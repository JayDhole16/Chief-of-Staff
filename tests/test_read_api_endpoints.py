"""
Integration Tests for Read APIs, Approvals, and Lifecycle Endpoints (T08.4, T09).

Tests:
- /api/activity feed
- /api/receipts/{id}
- /api/deals & /api/pipeline/deals
- /api/escalations
- /api/approvals/pending & hash-bound decisions (/api/approvals/{ref}/decision)
- 409 Conflict on stale / tampered hash
- /api/actions/{ref}/cancel
- /api/settings & /api/settings/kill-switch
- /api/auth/login & /api/session
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app, state
from backend.services.tasks import TaskRepositoryUnavailableError


@pytest.fixture(autouse=True)
def reset_app_state():
    state.reset()
    yield
    state.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_activity_feed(client: TestClient):
    res = client.get("/api/activity")
    assert res.status_code == 200
    data = res.json()
    assert "events" in data
    assert data["count"] >= 2
    assert any(e["type"] == "proposed" for e in data["events"])


def test_health_endpoints(client: TestClient):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/api/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_readiness_returns_service_unavailable_when_repository_is_down(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    def unavailable() -> bool:
        raise TaskRepositoryUnavailableError("database is offline")

    monkeypatch.setattr(state.task_repository, "health_check", unavailable)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["detail"] == "Task repository is not ready"


def test_get_receipt_success_and_404(client: TestClient):
    # Existing seeded receipt
    res = client.get("/api/receipts/rcpt_20261015_001")
    assert res.status_code == 200
    receipt = res.json()
    assert receipt["receipt_id"] == "rcpt_20261015_001"
    assert receipt["status"] == "executed"
    assert receipt["action_kind"] == "email"
    assert len(receipt["checks_passed"]) > 0

    # Non-existent receipt -> 404
    res_404 = client.get("/api/receipts/rcpt_non_existent")
    assert res_404.status_code == 404


def test_get_deals_pipeline(client: TestClient):
    res1 = client.get("/api/deals")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["count"] == 6
    assert data1["total_pipeline_paise"] == 1455000000

    # Test /api/pipeline/deals alias used by frontend
    res2 = client.get("/api/pipeline/deals")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["count"] == 6
    assert data2["deals"][0]["id"] == "D-1"


def test_get_escalations_empty_and_populated(client: TestClient):
    res = client.get("/api/escalations")
    assert res.status_code == 200
    assert res.json()["count"] == 0

    # Inject an inbound message that triggers escalation (INB-003)
    client.post(
        "/api/dev/inject-inbound",
        json={
            "message_id": "test_msg_esc_01",
            "from_email": "arjun@bluedart-franchise.in",
            "subject": "Penalty clause demand",
            "body": "We require a penalty clause and unlimited liability.",
        },
    )

    res_esc = client.get("/api/escalations")
    assert res_esc.status_code == 200
    assert res_esc.json()["count"] == 1
    assert res_esc.json()["escalations"][0]["guard_code"] == "G14"


def test_approvals_pending_and_decision(client: TestClient):
    # 1. Fetch pending approvals (should contain seeded Raju proposal)
    res = client.get("/api/approvals/pending")
    assert res.status_code == 200
    approvals = res.json()["approvals"]
    assert len(approvals) >= 1
    proposal = approvals[0]["proposal"]
    assert proposal["ref"] == "PA-2026-10-15-001"
    golden_hash = proposal["rendered_hash"]

    # 2. Tampered / stale hash attempt -> 409 Conflict
    res_conflict = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={
            "decision": "approve",
            "rendered_hash": "bad_stale_hash_1234567890abcdef",
        },
    )
    assert res_conflict.status_code == 409
    assert "Proposal version conflict" in res_conflict.json()["detail"]

    # 3. Valid approve with correct rendered_hash
    res_approve = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={
            "decision": "approve",
            "rendered_hash": golden_hash,
        },
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "approved"

    # Worker executed: check receipt created
    receipts_res = client.get(f"/api/receipts/{proposal['ref']}")
    assert receipts_res.status_code == 200
    assert receipts_res.json()["status"] == "executed"

    # Pending list should now be empty
    res_after = client.get("/api/approvals/pending")
    assert res_after.json()["count"] == 0


def test_action_cancellation_undo(client: TestClient):
    res = client.post("/api/actions/PA-2026-10-15-001/cancel")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cancelled"
    assert "rcpt_cancel_" in data["receipt_id"]


def test_settings_and_kill_switch(client: TestClient):
    # Get settings
    res = client.get("/api/settings")
    assert res.status_code == 200
    settings = res.json()
    assert settings["founder"]["name"] == "Meera Nair"
    assert settings["kill_switch"]["active"] is False

    # Toggle kill switch active
    res_toggle = client.post(
        "/api/settings/kill-switch",
        json={"active": True, "reason": "Emergency halt test"},
    )
    assert res_toggle.status_code == 200
    assert res_toggle.json()["kill_switch_active"] is True

    # Re-verify settings shows active
    res_after = client.get("/api/settings")
    assert res_after.json()["kill_switch"]["active"] is True
    assert res_after.json()["kill_switch"]["reason"] == "Emergency halt test"


def test_auth_login_and_session(client: TestClient):
    # Missing credentials
    res_bad = client.post("/api/auth/login", json={"email": "", "password": ""})
    assert res_bad.status_code == 422

    # Short password
    res_short = client.post("/api/auth/login", json={"email": "meera@agency.in", "password": "123"})
    assert res_short.status_code == 422

    # Valid login
    res_ok = client.post(
        "/api/auth/login",
        json={"email": "meera@agency.in", "password": "password123"},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert "session_id" in data
    session_id = data["session_id"]

    # Verify /api/session
    res_session = client.get("/api/session", headers={"X-Session-ID": session_id})
    assert res_session.status_code == 200
    assert res_session.json()["user"]["email"] == "meera@agency.in"

    # Invalid session header
    res_unauth = client.get("/api/session", headers={"X-Session-ID": "invalid_session"})
    assert res_unauth.status_code == 401

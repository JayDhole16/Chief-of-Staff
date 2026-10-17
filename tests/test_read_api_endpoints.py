"""
Integration Tests for Read APIs, Approvals, Chat, Profile, Lifecycle Endpoints, and Deep Domain/Service Fixes.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app, state
from backend.contracts.read_api import ActivityEventItem, ActivityType
from backend.domain.types import Discount, DiscountType, Money, TrustedFacts
from backend.facts.inr_formatter import format_inr, parse_inr
from backend.facts.trusted_render import PlaceholderError, apply_discount_to_facts, calculate_offer
from backend.policy.engine import PolicyInput
from backend.services.context import CapsuleIsolationError, ContextService, TaskContextInput
from backend.services.inbound import InboundEmailMessage, InboundProcessingPipeline
from backend.services.tasks import TaskRepositoryUnavailableError


@pytest.fixture(autouse=True)
def reset_app_state():
    state.reset()
    yield
    state.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_activity_feed_and_pagination(client: TestClient):
    res = client.get("/api/activity")
    assert res.status_code == 200
    data = res.json()
    assert "events" in data
    assert data["count"] >= 2
    assert any(e["type"] == "proposed" for e in data["events"])

    # Test pagination with limit=1 and cursor
    res_page1 = client.get("/api/activity?limit=1")
    assert res_page1.status_code == 200
    page1 = res_page1.json()
    assert len(page1["events"]) == 1
    assert page1["has_more"] is True
    assert page1["next_cursor"] == page1["events"][0]["id"]

    res_page2 = client.get(f"/api/activity?limit=1&cursor={page1['next_cursor']}")
    assert res_page2.status_code == 200
    page2 = res_page2.json()
    assert len(page2["events"]) == 1
    assert page2["events"][0]["id"] != page1["events"][0]["id"]


def test_health_endpoints(client: TestClient):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/api/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_operations_status_reports_placeholder_integrations(client: TestClient):
    response = client.get("/api/v1/ops/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["data_mode"] == "provisional"
    assert payload["components"]["task_repository"]["status"] == "ready"
    assert payload["components"]["worker"]["status"] == "degraded"
    assert payload["components"]["google"]["status"] == "not_configured"
    assert payload["components"]["agent_runtime"]["status"] == "not_configured"
    assert payload["components"]["benchmarks"]["status"] == "not_configured"
    assert payload["components"]["deployment"]["status"] == "not_configured"


def test_operations_status_exposes_repository_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    def unavailable() -> bool:
        raise TaskRepositoryUnavailableError("database is offline")

    monkeypatch.setattr(state.task_repository, "health_check", unavailable)
    response = client.get("/api/v1/ops/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["components"]["task_repository"]["status"] == "unavailable"
    assert payload["components"]["task_repository"]["detail"] == "database is offline"


def test_brief_items_only_include_resolvable_receipt_approval_or_escalation_links(
    client: TestClient,
):
    baseline = client.get("/api/v1/brief")
    assert baseline.status_code == 200
    baseline_payload = baseline.json()
    assert baseline_payload["omitted_unlinked_events"] == 0
    assert {item["link"]["kind"] for item in baseline_payload["items"]} == {
        "receipt",
        "approval",
    }

    inject_response = client.post(
        "/api/dev/inject-inbound",
        json={
            "message_id": "brief_escalation_001",
            "from_email": "arjun@bluedart-franchise.in",
            "subject": "Penalty clause demand",
            "body": "We require a penalty clause and unlimited liability.",
        },
    )
    assert inject_response.status_code == 200
    assert inject_response.json()["escalation_id"]

    updated = client.get("/api/v1/brief")
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["omitted_unlinked_events"] == 0
    escalation_items = [item for item in payload["items"] if item["link"]["kind"] == "escalation"]
    assert len(escalation_items) == 1
    assert escalation_items[0]["link"]["reference"] == inject_response.json()["escalation_id"]
    assert all(
        item["link"]["kind"] in {"receipt", "approval", "escalation"}
        and item["link"]["reference"]
        and item["link"]["href"]
        for item in payload["items"]
    )


def test_brief_reports_omitted_events_without_references(client: TestClient):
    state.activity_events.append(
        ActivityEventItem(
            id="unlinked_event",
            timestamp=datetime.now(timezone.utc),
            type=ActivityType.EXECUTION,
            title="Event without a reference",
            description="Must not appear in the brief without a link.",
            user_id="test",
        )
    )

    response = client.get("/api/v1/brief")
    assert response.status_code == 200
    payload = response.json()
    assert payload["omitted_unlinked_events"] >= 1
    assert all(
        item["link"]["kind"] in {"receipt", "approval", "escalation"}
        for item in payload["items"]
    )


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
    res = client.get("/api/receipts/rcpt_20261015_001")
    assert res.status_code == 200
    receipt = res.json()
    assert receipt["receipt_id"] == "rcpt_20261015_001"
    assert receipt["status"] == "executed"
    assert receipt["action_kind"] == "email"
    assert len(receipt["checks_passed"]) > 0

    res_404 = client.get("/api/receipts/rcpt_non_existent")
    assert res_404.status_code == 404


def test_get_deals_pipeline(client: TestClient):
    res1 = client.get("/api/deals")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["count"] == 6
    assert data1["total_pipeline_paise"] == 1455000000

    res2 = client.get("/api/pipeline/deals")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["count"] == 6
    assert data2["deals"][0]["id"] == "D-1"


def test_get_escalations_empty_and_populated(client: TestClient):
    res = client.get("/api/escalations")
    assert res.status_code == 200
    assert res.json()["count"] == 0

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
    res = client.get("/api/approvals/pending")
    assert res.status_code == 200
    approvals = res.json()["approvals"]
    assert len(approvals) >= 1
    proposal = approvals[0]["proposal"]
    assert proposal["ref"] == "PA-2026-10-15-001"
    golden_hash = proposal["rendered_hash"]

    res_conflict = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={
            "decision": "approve",
            "rendered_hash": "bad_stale_hash_1234567890abcdef",
        },
    )
    assert res_conflict.status_code == 409
    assert "Proposal version conflict" in res_conflict.json()["detail"]

    res_approve = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={
            "decision": "approve",
            "rendered_hash": golden_hash,
        },
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "approved"

    receipts_res = client.get(f"/api/receipts/{proposal['ref']}")
    assert receipts_res.status_code == 200
    assert receipts_res.json()["status"] == "executed"

    res_after = client.get("/api/approvals/pending")
    assert res_after.json()["count"] == 0


def test_action_cancellation_undo_and_conflict_on_executed(client: TestClient):
    res = client.post("/api/actions/PA-2026-10-15-001/cancel")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cancelled"
    assert "rcpt_cancel_" in data["receipt_id"]
    assert state.proposals["PA-2026-10-15-001"].status == "cancelled"

    # Attempting to cancel an already-executed action (act_d1_01) returns 409 Conflict
    res_exec_cancel = client.post("/api/actions/act_d1_01/cancel")
    assert res_exec_cancel.status_code == 409


def test_settings_and_kill_switch(client: TestClient):
    res = client.get("/api/settings")
    assert res.status_code == 200
    settings = res.json()
    assert settings["founder"]["name"] == "Meera Nair"
    assert settings["kill_switch"]["active"] is False

    res_toggle = client.post(
        "/api/settings/kill-switch",
        json={"active": True, "reason": "Emergency halt test"},
    )
    assert res_toggle.status_code == 200
    assert res_toggle.json()["kill_switch_active"] is True

    res_after = client.get("/api/settings")
    assert res_after.json()["kill_switch"]["active"] is True
    assert res_after.json()["kill_switch"]["reason"] == "Emergency halt test"


def test_auth_login_and_session(client: TestClient):
    res_bad = client.post("/api/auth/login", json={"email": "", "password": ""})
    assert res_bad.status_code == 422

    res_short = client.post("/api/auth/login", json={"email": "meera@agency.in", "password": "123"})
    assert res_short.status_code == 422

    res_ok = client.post(
        "/api/auth/login",
        json={"email": "meera@agency.in", "password": "password123"},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert "session_id" in data
    session_id = data["session_id"]

    res_session = client.get("/api/session", headers={"X-Session-ID": session_id})
    assert res_session.status_code == 200
    assert res_session.json()["user"]["email"] == "meera@agency.in"

    res_unauth = client.get("/api/session", headers={"X-Session-ID": "invalid_session"})
    assert res_unauth.status_code == 401


def test_profile_get_and_update(client: TestClient):
    res_get = client.get("/api/profile")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Meera Nair"

    res_put = client.put(
        "/api/profile",
        json={"name": "Ayush Sharma", "business_name": "Sharma AI Ventures"},
    )
    assert res_put.status_code == 200
    assert res_put.json()["name"] == "Ayush Sharma"
    assert res_put.json()["business_name"] == "Sharma AI Ventures"


def test_chat_endpoint_grounded_responses(client: TestClient):
    res_d1 = client.post("/api/chat", json={"message": "Review Raju Malhotra 20% discount on D-1", "session_id": "s-1"})
    assert res_d1.status_code == 200
    body_d1 = res_d1.json()
    assert body_d1["intent"] == "DEAL_D1_REVIEW"
    assert "₹4,56,000" in body_d1["reply"]
    assert "G08" in body_d1["guards_checked"]

    res_brief = client.post("/api/chat", json={"message": "Generate my morning standup brief", "session_id": "s-1"})
    assert res_brief.status_code == 200
    assert res_brief.json()["intent"] == "FOUNDER_BRIEF"


def test_backend_regression_fixes():
    """Verify deep backend audit fixes across domain, facts, policy, context, and inbound pipeline."""
    # 1. Boolean rejected where int is required
    with pytest.raises(TypeError):
        Money(True)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Money.from_rupees(True)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Discount(DiscountType.PERCENTAGE, True)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        PolicyInput(amount_paise=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        format_inr(True)  # type: ignore[arg-type]

    # 2. Money.from_rupees Decimal half-up rounding
    assert Money.from_rupees(Decimal("10.005")).amount_paise == 1001

    # 3. TrustedFacts defensive copy prevents external mutation
    source_dict = {"price": "₹4,56,000"}
    tf = TrustedFacts(source_dict)
    source_dict["price"] = "₹0"
    assert tf.get("price") == "₹4,56,000"

    # 4. Indian comma grouping strictly validated in parse_inr
    with pytest.raises(ValueError):
        parse_inr("₹100,00")
    with pytest.raises(ValueError):
        parse_inr("₹1,2,3")
    assert parse_inr("₹12,34,567") == 123456700

    # 5. Double rupee symbol fixed in floor breach message & PlaceholderError on missing key
    try:
        calculate_offer(100000, Discount(DiscountType.PERCENTAGE, 50), floor_price_paise=60000)
        assert False, "Expected floor breach exception"
    except Exception as exc:
        assert "₹₹" not in str(exc)
        assert "₹500" in str(exc) and "₹600" in str(exc)
    with pytest.raises(PlaceholderError):
        apply_discount_to_facts(TrustedFacts({}), "missing_key", Discount(DiscountType.PERCENTAGE, 5))

    # 6. Inbound whitespace guard bypass & persistent opt-out G12
    pipeline = InboundProcessingPipeline()
    padded_res = pipeline.process(
        InboundEmailMessage(
            to_email="meera@agency.in",
            message_id="msg_padded_arjun",
            from_email="  arjun@bluedart-franchise.in  ",
            subject="Schedule follow-up",
            body="Let us discuss the deployment timeline.",
        )
    )
    assert padded_res.status == "task_created"
    assert any(f.code == "G02" for f in padded_res.risk_flags)

    # Opt-out persists across subsequent messages from same contact
    pipeline.process(
        InboundEmailMessage(
            to_email="meera@agency.in",
            message_id="msg_optout_1",
            from_email="sunil@apexlogistics.in",
            subject="Unsubscribe",
            body="Please unsubscribe me from this list.",
        )
    )
    subsequent = pipeline.process(
        InboundEmailMessage(
            to_email="meera@agency.in",
            message_id="msg_optout_2",
            from_email="sunil@apexlogistics.in",
            subject="Quick question",
            body="Actually can we meet?",
        )
    )
    assert subsequent.status == "dropped"
    assert any(f.code == "G12" for f in subsequent.risk_flags)

    # Abbreviated month OOO return date parsing
    ooo = pipeline.process(
        InboundEmailMessage(
            to_email="meera@agency.in",
            message_id="msg_ooo_abbr",
            from_email="raju@patel-warehousing.in",
            subject="Out of office",
            body="I am away and back on 22 Oct 2026.",
        )
    )
    assert ooo.classification.return_date == "2026-10-22"

    # 7. CapsuleIsolationError on cross-tenant message leak
    with pytest.raises(CapsuleIsolationError):
        ContextService.build_capsule(
            TaskContextInput(
                tenant_id="tenant-a",
                task_id="t-1",
                task_ref="T-1",
                task_kind="inbound_reply",
                task_instructions=None,
                allowed_action_types=["propose_reply"],
                founder_name="Meera",
                founder_signature="Meera",
                founder_business="Agency",
                founder_tz="Asia/Kolkata",
                contact_id="c-1",
                contact_ref="C-1",
                contact_name="Raju",
                contact_first_name="Raju",
                contact_company="Patel Warehousing",
                contact_tz="Asia/Kolkata",
                contact_autonomy_mode="approval_required",
                deal_id="d-1",
                deal_ref="D-1",
                deal_title="Deal 1",
                deal_stage="Negotiation",
                deal_days_quiet=2,
                deal_record_age_days=1,
                deal_record_version=1,
                deal_founder_notes=None,
                proposal_ref=None,
                proposal_title=None,
                proposal_sent_on_display=None,
                proposal_terms_status=None,
                mandate_ref="M-1",
                mandate_clauses=["C-1"],
                mandate_discount_max_pct="5%",
                mandate_hard_ceiling_pct="10%",
                kill_switch_engaged=False,
                thread_ref="TH-1",
                thread_subject="Subj",
                messages=[
                    {
                        "ref": "M-1",
                        "tenant_id": "tenant-b",
                        "direction": "inbound",
                        "from_display": "other@tenant.com",
                        "sent_at_display": "2026-10-15T04:00:00Z",
                        "body_excerpt": "Cross-tenant leak",
                    }
                ],
                trusted_facts=TrustedFacts({"F_BASE": "₹4,80,000"}),
                conflicts=[],
                add_ons=[],
                now_dt=datetime(2026, 10, 15, 5, 0, tzinfo=timezone.utc),
                calendar_days=[],
            )
        )

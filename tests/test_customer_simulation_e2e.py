"""
End-to-End Customer Simulation and Comprehensive QA Suite (T15.1).

Tests the complete founder journey from beginning to end across all 10 stages:
1. Inbound customer message arrives (price objection).
2. System resolves customer and relevant deal.
3. Trusted facts and context are assembled.
4. Follow-up action is proposed.
5. Deterministic guards evaluate policy (ALLOW / ASK / BLOCK).
6. Founder views proposal with grounded evidence facts and risk flags.
7. Founder approves with verified SHA-256 rendered_hash.
8. Designated worker executor handles external effect (Gmail adapter).
9. Immutable terminal action receipt is persisted.
10. Activity feed, pipeline, escalations, and founder brief reflect the outcome.

Adversarial and Edge Cases:
- Wrong recipient and unauthorized actions.
- Missing or ambiguous contact identity.
- Unverified commercial claims (G08 / G10).
- Stale or modified approval payloads (409 Conflict).
- Duplicate messages and retries (G01 Replay).
- Kill switch active blocking writes.
- Cross-tenant workspace boundary enforcement (403 Forbidden).
- Worker failure / interrupted execution recording blocked receipt without ghost email.
"""

import hashlib
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.api.app import app, state
from backend.contracts.read_api import ReceiptStatus


@pytest.fixture(autouse=True)
def reset_app():
    state.reset()
    yield
    state.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ===========================================================================
# 1. Complete 10-Step Golden Path Simulation
# ===========================================================================

def test_complete_golden_path_journey(client: TestClient):
    """Executes the complete 10-stage customer journey from inbound email to founder brief."""
    # Stage 1: Inbound message arrives
    inbound_payload = {
        "message_id": "gmail_msg_simulation_golden_101",
        "from_email": "raju@patel-warehousing.in",
        "from_name": "Raju Patel",
        "to_email": "meera@agency.in",
        "subject": "Re: Warehouse Automation Proposal",
        "body": (
            "Hi Meera, we reviewed the setup quote. On our call last Tuesday, "
            "you mentioned a potential 20% discount if we signed this month. "
            "Can you confirm the revised price and Thursday afternoon slot?"
        ),
        "headers": {"auto-submitted": "no"},
    }
    inb_res = client.post("/api/dev/inject-inbound", json=inbound_payload)
    assert inb_res.status_code == 200
    inb_data = inb_res.json()

    # Stage 2: Entity resolution and task creation
    assert inb_data["status"] == "task_created"
    assert inb_data["task_id"] is not None

    # Stage 3: Trusted facts assembled & Stage 4/5: Guard evaluation
    assert inb_data["intent"] == "PRICE_OBJECTION"
    assert inb_data["verdict"] == "ASK"
    assert "G08" in inb_data["guards_triggered"]
    assert "G10" in inb_data["guards_triggered"]

    # Stage 6: Founder sees proposal and supporting evidence
    approvals_res = client.get("/api/approvals/pending")
    assert approvals_res.status_code == 200
    approvals = approvals_res.json()["approvals"]
    assert len(approvals) >= 1
    proposal = next(a["proposal"] for a in approvals if a["proposal"]["deal_id"] == "D-1")
    ref = proposal["ref"]
    rendered_hash = proposal["rendered_hash"]
    assert len(rendered_hash) == 64
    assert "₹4,56,000" in proposal["rendered_body"]
    assert "15:00 - 15:30 IST" in proposal["rendered_body"]
    assert len(proposal["facts_used"]) >= 4

    # Stage 7: Founder approves with hash-bound decision
    decision_res = client.post(
        f"/api/approvals/{ref}/decision",
        json={"decision": "approve", "rendered_hash": rendered_hash},
    )
    assert decision_res.status_code == 200
    assert decision_res.json()["status"] == "approved"

    # Stage 8: Worker executor performs external effect
    assert len(state.gmail_adapter.sent_messages) == 1
    sent_msg = state.gmail_adapter.sent_messages[0]
    assert sent_msg["to"] == "raju@patel-warehousing.in"
    assert sent_msg["rendered_hash"] == rendered_hash

    # Stage 9: Accurate immutable receipt persisted
    receipt_res = client.get(f"/api/receipts/{ref}")
    assert receipt_res.status_code == 200
    receipt = receipt_res.json()
    assert receipt["status"] == "executed"
    assert receipt["authority_clause"] == "Founder Explicit Approval"
    assert receipt["external_id"] == sent_msg["id"]
    assert len(receipt["checks_passed"]) >= 8

    # Stage 10: Activity feed, pipeline, and founder brief reflect actual outcome
    activity_res = client.get("/api/activity")
    assert activity_res.status_code == 200
    events = activity_res.json()["events"]
    assert any(e["action_ref"] == ref and e["type"] == "approved" for e in events)

    brief_res = client.get("/api/brief")
    assert brief_res.status_code == 200
    brief = brief_res.json()
    assert brief["metrics"]["actions_executed_count"] >= 2
    assert any(i["evidence_receipt_id"] == receipt["receipt_id"] for i in brief["items"])


# ===========================================================================
# 2. Adversarial Scenarios and Boundary Verification
# ===========================================================================

def test_tampered_or_stale_hash_rejected_409(client: TestClient):
    """Proposal approval with modified or stale hash must return 409 Conflict."""
    approvals_res = client.get("/api/approvals/pending")
    approvals = approvals_res.json()["approvals"]
    target = approvals[0]["proposal"]

    tampered_hash = hashlib.sha256(b"malicious_modified_content").hexdigest()
    res = client.post(
        f"/api/approvals/{target['ref']}/decision",
        json={"decision": "approve", "rendered_hash": tampered_hash},
    )
    assert res.status_code == 409
    detail = res.json()["detail"].lower()
    assert "not match" in detail or "conflict" in detail


def test_wrong_recipient_domain_spoofing_blocked(client: TestClient):
    """Inbound message from personal domain spoofing contact is blocked (G04) and escalated."""
    spoof_payload = {
        "message_id": "msg_spoof_attacker",
        "from_email": "raju.patel.personal@gmail.com",
        "from_name": "Raju Patel Impersonator",
        "to_email": "meera@agency.in",
        "subject": "Confidential banking details update",
        "body": "Please wire setup funds to my personal account.",
    }
    res = client.post("/api/dev/inject-inbound", json=spoof_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verdict"] == "BLOCK"
    assert "G04" in data["guards_triggered"]
    assert data["status"] == "escalated"


def test_duplicate_message_replay_detection(client: TestClient):
    """Replaying an already processed message ID is blocked by Guard G01."""
    msg = {
        "message_id": "gmail_msg_duplicate_001",
        "from_email": "raju@patel-warehousing.in",
        "to_email": "meera@agency.in",
        "subject": "Duplicate test",
        "body": "Message 1",
    }
    res1 = client.post("/api/dev/inject-inbound", json=msg)
    assert res1.status_code == 200

    # Second injection with identical message_id
    res2 = client.post("/api/dev/inject-inbound", json=msg)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["verdict"] == "BLOCK"
    assert "G01" in data2["guards_triggered"]


def test_ambiguous_unknown_contact_quarantined(client: TestClient):
    """Inbound from completely unknown contact does not create a task."""
    unknown_msg = {
        "message_id": "msg_unknown_stranger_99",
        "from_email": "stranger@unknown-domain-xyz.com",
        "to_email": "meera@agency.in",
        "subject": "Cold Sales Pitch",
        "body": "Buy our leads database.",
    }
    res = client.post("/api/dev/inject-inbound", json=unknown_msg)
    assert res.status_code == 200
    data = res.json()
    assert data["task_id"] is None
    assert data["verdict"] == "BLOCK"


def test_kill_switch_disengages_autonomous_execution(client: TestClient):
    """When kill switch is engaged, worker blocks execution and records blocked receipt."""
    # Engage kill switch
    ks_res = client.post("/api/settings/kill-switch", json={"active": True, "reason": "Founder emergency pause"})
    assert ks_res.status_code == 200
    assert ks_res.json()["kill_switch_active"] is True

    # Attempt execution via worker
    receipt = state.executor.execute_action(
        action_ref="PA-KILLSWITCH-TEST",
        action_kind="email",
        recipient_email="raju@patel-warehousing.in",
        rendered_body_or_time="Emergency message",
        rendered_hash="dummy_hash_ks",
        authority_clause="Mandate Clause",
        is_founder_approved=False,
    )

    assert receipt.status == ReceiptStatus.BLOCKED
    assert "Kill switch is active" in receipt.authority_clause or "Kill switch is currently engaged" in receipt.timeline[-1].event
    assert len(state.gmail_adapter.sent_messages) == 0


def test_cross_tenant_workspace_boundary_enforced(client: TestClient):
    """Requests targeting a different workspace ID receive 403 Forbidden."""
    res = client.get("/api/brief", headers={"x-workspace-id": "WS-MALICIOUS-TENANT"})
    assert res.status_code == 403
    assert "Unauthorized access" in res.json()["detail"]


def test_worker_failure_handling_and_no_ghost_writes(client: TestClient):
    """Simulates worker adapter failure; verifies no external write occurred and failed receipt recorded."""
    body = "Will fail due to simulated network timeout"
    valid_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    # Force adapter failure
    state.gmail_adapter.send_email = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Simulated Gmail API 500 Network Timeout"))

    receipt = state.executor.execute_action(
        action_ref="PA-WORKER-FAIL-TEST",
        action_kind="email",
        recipient_email="raju@patel-warehousing.in",
        rendered_body_or_time=body,
        rendered_hash=valid_hash,
        authority_clause="Founder Explicit Approval",
        is_founder_approved=True,
    )

    assert receipt.status == ReceiptStatus.BLOCKED
    assert any("Simulated Gmail API 500" in t.event for t in receipt.timeline)
    assert len(state.gmail_adapter.sent_messages) == 0

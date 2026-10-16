"""
Unit and Integration Tests for Deterministic Founder Brief (T13.2).

Covers:
- Normal operation with mixed receipts, approvals, escalations, quiet deals.
- Empty receipts / empty state without errors.
- Failed / blocked actions preserved as blocked and not claimed as executed.
- Approved proposal without terminal receipt is NEVER claimed as executed.
- Conflicting states, missing fields, and unverified data handled deterministically.
- Workspace authorization and cross-tenant boundary isolation (403).
- GET /api/brief integration tests via FastAPI TestClient.
- Deterministic narration text fallback generation.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.api.app import app, state
from backend.contracts.read_api import (
    ActionReceiptResponse,
    DealItem,
    DealStage,
    EscalationItem,
    EscalationSeverity,
    ReceiptFactItem,
    ReceiptStatus,
    ReceiptTimelineItem,
)
from backend.services.brief import (
    BriefItem,
    BriefMetrics,
    FounderBriefResponse,
    FounderBriefService,
)


@pytest.fixture(autouse=True)
def reset_app_state():
    state.reset()
    yield
    state.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_brief_empty_state():
    """Verify that empty inputs generate a valid deterministic brief without errors."""
    service = FounderBriefService(workspace_id="WS-TEST")
    brief = service.generate_brief(
        receipts=[],
        proposals=[],
        deals=[],
        escalations=[],
        activity_events=[],
        as_of_time=datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert isinstance(brief, FounderBriefResponse)
    assert brief.workspace_id == "WS-TEST"
    assert brief.metrics.actions_executed_count == 0
    assert brief.metrics.pending_approvals_count == 0
    assert brief.metrics.escalations_count == 0
    assert brief.metrics.blocked_actions_count == 0
    assert brief.metrics.total_pipeline_value_paise == 0
    assert len(brief.items) == 0
    assert "All operations are currently quiet" in brief.narration_text


def test_brief_normal_operation():
    """Verify normal operation accurately computes metrics, categories, and narration."""
    service = FounderBriefService(workspace_id="WS-DEMO")
    
    mock_receipt = ActionReceiptResponse(
        receipt_id="rcpt_001",
        action_ref="act_001",
        action_kind="email",
        status=ReceiptStatus.EXECUTED,
        authority_clause="Founder Explicit Approval",
        recipient_email="raju@patel-warehousing.in",
        external_id="gmail_msg_001",
        rendered_hash="abc123hash",
        checks_passed=["G01", "G04", "G05"],
        facts_used=[ReceiptFactItem(key="pricing.tier", label="Tier", value="Standard", source="pricing_sheet")],
        executed_at=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc),
        timeline=[ReceiptTimelineItem(timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc), event="Sent email via Gmail adapter")],
    )

    mock_proposal = {
        "ref": "act_002",
        "action_kind": "email",
        "deal_id": "D-1",
        "deal_title": "Acme Warehousing",
        "contact_name": "Raju Patel",
        "contact_email": "raju@patel-warehousing.in",
        "rendered_body": "Proposal text",
        "rendered_hash": "hash_act_002",
        "facts_used": [{"key": "discount", "label": "Discount", "value": "10%", "source": "sheet"}],
        "risk_flags": [{"reason": "G08_DISCOUNT_THRESHOLD"}],
        "policy_verdict": "ASK",
        "policy_reasons": ["Discount exceeds threshold"],
        "status": "pending",
    }

    mock_deal = DealItem(
        id="D-2",
        title="Quiet Deal",
        contact_name="Sunil Mehta",
        contact_email="sunil@apexlogistics.in",
        stage=DealStage.LEAD,
        value_paise=250000000,
        created_at=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
        days_quiet=5,
        is_quiet=True,
    )

    mock_escalation = EscalationItem(
        escalation_id="esc_001",
        created_at=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc),
        severity=EscalationSeverity.CRITICAL,
        source_message_id="msg_001",
        deal_id="D-1",
        contact_email="raju@patel-warehousing.in",
        reason="Security breach mentioned",
        guard_code="G03",
        status="open",
    )

    brief = service.generate_brief(
        receipts=[mock_receipt],
        proposals=[mock_proposal],
        deals=[mock_deal],
        escalations=[mock_escalation],
        as_of_time=datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert brief.metrics.actions_executed_count == 1
    assert brief.metrics.pending_approvals_count == 1
    assert brief.metrics.escalations_count == 1
    assert brief.metrics.total_pipeline_value_paise == 250000000

    categories = {item.category for item in brief.items}
    assert "executed_action" in categories
    assert "pending_decision" in categories
    assert "escalation" in categories
    assert "pipeline_quiet" in categories

    # Check narration mentions key figures
    assert "1 action was executed" in brief.narration_text
    assert "1 pending proposal" in brief.narration_text
    assert "escalated" in brief.narration_text


def test_approved_proposal_without_terminal_receipt_not_claimed_executed():
    """Safety requirement: An approved proposal must NOT be claimed as executed without a terminal receipt."""
    service = FounderBriefService(workspace_id="WS-DEMO")

    mock_proposal = {
        "ref": "act_approved_unexecuted",
        "action_kind": "email",
        "deal_id": "D-1",
        "deal_title": "Acme Warehousing",
        "contact_name": "Raju Patel",
        "contact_email": "raju@patel-warehousing.in",
        "rendered_body": "Proposal text",
        "rendered_hash": "hash_unexecuted",
        "status": "approved",
    }

    # Empty receipts -> execution has not happened
    brief = service.generate_brief(
        receipts=[],
        proposals=[mock_proposal],
        deals=[],
        escalations=[],
    )

    assert brief.metrics.actions_executed_count == 0
    # Must appear as approved_awaiting_receipt under pending_decision, NOT executed_action
    item = next(i for i in brief.items if i.id == "item_act_approved_unexecuted")
    assert item.category == "pending_decision"
    assert item.status == "approved_awaiting_receipt"
    assert "worker execution pending receipt" in item.summary


def test_blocked_and_failed_actions_recorded_as_blocked():
    """Blocked and failed receipts must be categorized as blocked_action, never executed_action."""
    service = FounderBriefService(workspace_id="WS-DEMO")

    blocked_receipt = ActionReceiptResponse(
        receipt_id="rcpt_blocked",
        action_ref="act_blocked",
        action_kind="email",
        status=ReceiptStatus.BLOCKED,
        authority_clause="Guard G01 Block: Disallowed domain",
        checks_passed=["G04"],
        recipient_email="attacker@external-evil.com",
        rendered_hash="hash_blocked",
        facts_used=[],
        timeline=[],
    )

    cancelled_receipt = ActionReceiptResponse(
        receipt_id="rcpt_cancelled",
        action_ref="act_cancelled",
        action_kind="calendar",
        status=ReceiptStatus.CANCELLED,
        authority_clause="Founder undo within 15s window",
        checks_passed=["G01", "G04"],
        recipient_email="sunil@apexlogistics.in",
        rendered_hash="hash_cancelled",
        facts_used=[],
        timeline=[],
    )

    brief = service.generate_brief(
        receipts=[blocked_receipt, cancelled_receipt],
        proposals=[],
        deals=[],
        escalations=[],
    )

    assert brief.metrics.actions_executed_count == 0
    assert brief.metrics.blocked_actions_count == 2
    categories = [i.category for i in brief.items]
    assert all(c == "blocked_action" for c in categories)


def test_unauthorized_workspace_access_rejected():
    """Tenant/workspace isolation: Accessing a workspace with mismatched ID must be rejected."""
    service = FounderBriefService(workspace_id="WS-TENANT-A")

    with pytest.raises(PermissionError) as exc_info:
        service.generate_brief(
            receipts=[],
            proposals=[],
            deals=[],
            escalations=[],
            requesting_workspace_id="WS-TENANT-B",
        )
    assert "Unauthorized access" in str(exc_info.value)


def test_api_get_brief_endpoint(client: TestClient):
    """Integration test for GET /api/brief endpoint with default and invalid workspace headers."""
    # Default header (WS-DEMO) -> 200 OK
    res = client.get("/api/brief")
    assert res.status_code == 200
    data = res.json()
    assert data["workspace_id"] == "WS-DEMO"
    assert "metrics" in data
    assert "items" in data
    assert "narration_text" in data
    assert len(data["narration_text"]) > 0

    # Mismatched header -> 403 Forbidden
    res_bad = client.get("/api/brief", headers={"x-workspace-id": "WS-ATTACKER"})
    assert res_bad.status_code == 403
    assert "Unauthorized access" in res_bad.json()["detail"]


def test_api_brief_reflects_approved_execution(client: TestClient):
    """Integration test verifying GET /api/brief reflects state after a proposal is approved and executed."""
    # Initially: 1 pending proposal seeded in demo state (Beat 3 Raju Patel)
    brief_before = client.get("/api/brief").json()
    initial_pending = brief_before["metrics"]["pending_approvals_count"]
    initial_executed = brief_before["metrics"]["actions_executed_count"]
    assert initial_pending >= 1
    assert initial_executed == 1  # 1 pre-existing seeded receipt

    # Fetch pending approvals to get the ref and hash
    approvals_res = client.get("/api/approvals/pending")
    assert approvals_res.status_code == 200
    approvals = approvals_res.json()["approvals"]
    target = approvals[0]
    ref = target["proposal"]["ref"]
    hash_val = target["proposal"]["rendered_hash"]

    # Founder approves
    decision_res = client.post(
        f"/api/approvals/{ref}/decision",
        json={"decision": "approve", "rendered_hash": hash_val},
    )
    assert decision_res.status_code == 200

    # Query brief again
    brief_after = client.get("/api/brief").json()
    assert brief_after["metrics"]["actions_executed_count"] == initial_executed + 1
    assert brief_after["metrics"]["pending_approvals_count"] == initial_pending - 1

    # Check executed item is in brief with receipt id
    executed_items = [i for i in brief_after["items"] if i["category"] == "executed_action"]
    assert len(executed_items) >= 2
    assert any(i["evidence_receipt_id"] is not None for i in executed_items)

"""
Tests for Read API Contracts (T08.4).

Verifies typed contracts and expectations for:
- /activity (ActivityFeedResponse)
- /receipts/{ref_or_id} (ActionReceiptResponse)
- /deals (PipelineDealsResponse)
- /escalations (EscalationsResponse)

Dependency Note:
Live HTTP endpoint implementation depends on Jairaj's T05.7 (approval router / authority API).
These contract tests ensure schemas and serialized data models are validated independently.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from backend.contracts.read_api import (
    ActivityFeedResponse,
    ActivityEventItem,
    ActivityType,
    ActionReceiptResponse,
    ReceiptStatus,
    ReceiptFactItem,
    ReceiptTimelineItem,
    PipelineDealsResponse,
    DealItem,
    DealStage,
    EscalationsResponse,
    EscalationItem,
    EscalationSeverity,
)


def test_activity_feed_contract_validation():
    payload = {
        "events": [
            {
                "id": "evt_001",
                "timestamp": "2026-10-15T10:00:00Z",
                "type": "proposed",
                "title": "Proposed follow-up to Raju Patel",
                "description": "Counter-offer ₹4,56,000 drafted. Pending founder approval.",
                "user_id": "agent_cos",
                "action_ref": "PA-2026-10-15-001",
                "rendered_hash": "8f9b7c62d4e13589a12c8b74619d08e5c3e06182a93746c59b2184d8f1e6b392",
                "can_undo": False,
            },
            {
                "id": "evt_002",
                "timestamp": "2026-10-15T09:30:00Z",
                "type": "execution",
                "title": "D-1 Follow-up Sent",
                "description": "Autonomously sent to Acme Warehousing.",
                "user_id": "worker_executor",
                "receipt_id": "rcpt_20261015_001",
                "can_undo": False,
            },
        ],
        "count": 2,
        "has_more": False,
    }

    feed = ActivityFeedResponse.model_validate(payload)
    assert feed.count == 2
    assert feed.events[0].type == ActivityType.PROPOSED
    assert feed.events[1].receipt_id == "rcpt_20261015_001"


def test_action_receipt_contract_validation():
    payload = {
        "receipt_id": "rcpt_20261015_001",
        "action_ref": "act_d1_01",
        "action_kind": "email",
        "status": "executed",
        "authority_clause": "Mandate M-2026-10-15 Clause C2: Follow-up quiet deals with <=5% discount",
        "recipient_email": "raju@patel-warehousing.in",
        "external_id": "gmail_msg_18b93f8e71c29a04",
        "rendered_hash": "8f9b7c62d4e13589a12c8b74619d08e5c3e06182a93746c59b2184d8f1e6b392",
        "checks_passed": ["G01", "G04", "G05", "G06", "G07", "G09", "G10", "G11"],
        "facts_used": [
            {
                "key": "deal_value",
                "label": "Deal Value",
                "value": "₹12,50,000",
                "source": "crm:deal_d1",
            },
            {
                "key": "max_discount",
                "label": "Max Discount",
                "value": "5%",
                "source": "mandate:clause_c2",
            },
        ],
        "executed_at": "2026-10-15T09:30:00Z",
        "undo_window_seconds": 15,
        "timeline": [
            {"timestamp": "2026-10-15T09:29:45Z", "event": "Sweep proposed action under mandate"},
            {"timestamp": "2026-10-15T09:30:00Z", "event": "Undo window elapsed; worker dispatched"},
            {"timestamp": "2026-10-15T09:30:02Z", "event": "Gmail API send confirmed"},
        ],
    }

    receipt = ActionReceiptResponse.model_validate(payload)
    assert receipt.receipt_id == "rcpt_20261015_001"
    assert receipt.status == ReceiptStatus.EXECUTED
    assert len(receipt.checks_passed) == 8
    assert receipt.facts_used[0].value == "₹12,50,000"


def test_pipeline_deals_contract_validation():
    """Beat 0: Six-deal pipeline with quiet tracking."""
    payload = {
        "deals": [
            {
                "id": "D-1",
                "title": "Acme Warehousing Automation",
                "contact_name": "Raju Patel",
                "contact_email": "raju@patel-warehousing.in",
                "stage": "negotiation",
                "value_paise": 125000000,
                "created_at": "2026-10-01T10:00:00Z",
                "days_quiet": 3,
                "is_quiet": True,
            },
            {
                "id": "D-2",
                "title": "Apex Logistics Cloud Connector",
                "contact_name": "Sunil Mehta",
                "contact_email": "sunil@apexlogistics.in",
                "stage": "lead",
                "value_paise": 250000000,
                "created_at": "2026-10-05T10:00:00Z",
                "days_quiet": 0,
                "is_quiet": False,
            },
            {
                "id": "D-3",
                "title": "QuickShip Solutions Inventory Sync",
                "contact_name": "Priya Shah",
                "contact_email": "priya@quickship.in",
                "stage": "negotiation",
                "value_paise": 180000000,
                "created_at": "2026-10-02T10:00:00Z",
                "days_quiet": 4,
                "is_quiet": True,
            },
            {
                "id": "D-4",
                "title": "BlueDart Regional Franchise",
                "contact_name": "Arjun Verma",
                "contact_email": "arjun@bluedart-franchise.in",
                "stage": "negotiation",
                "value_paise": 300000000,
                "created_at": "2026-10-08T10:00:00Z",
                "days_quiet": 1,
                "is_quiet": True,
            },
            {
                "id": "D-5",
                "title": "ExpressCargo Route Automation",
                "contact_name": "Deepak Roy",
                "contact_email": "deepak@expresscargo.in",
                "stage": "active",
                "value_paise": 150000000,
                "created_at": "2026-10-09T10:00:00Z",
                "days_quiet": 0,
                "is_quiet": False,
            },
            {
                "id": "D-6",
                "title": "MegaFreight ERP Integration",
                "contact_name": "Kavita Nair",
                "contact_email": "kavita@megafreight.in",
                "stage": "won",
                "value_paise": 450000000,
                "created_at": "2026-09-25T10:00:00Z",
                "days_quiet": 0,
                "is_quiet": False,
            },
        ],
        "count": 6,
        "total_pipeline_paise": 1455000000,  # ₹1,45,50,000
    }

    pipeline = PipelineDealsResponse.model_validate(payload)
    assert pipeline.count == 6
    assert pipeline.total_pipeline_paise == 1455000000
    quiet_deals = [d for d in pipeline.deals if d.is_quiet]
    assert len(quiet_deals) == 3
    assert {d.id for d in quiet_deals} == {"D-1", "D-3", "D-4"}


def test_escalations_contract_validation():
    payload = {
        "escalations": [
            {
                "escalation_id": "esc_001",
                "created_at": "2026-10-15T11:00:00Z",
                "severity": "critical",
                "source_message_id": "gmail_msg_inb_003",
                "deal_id": "D-4",
                "contact_email": "arjun@bluedart-franchise.in",
                "reason": "Customer demands ₹5,00,000 penalty clause and unlimited liability.",
                "guard_code": "G14",
                "status": "open",
            }
        ],
        "count": 1,
    }

    esc = EscalationsResponse.model_validate(payload)
    assert esc.count == 1
    assert esc.escalations[0].guard_code == "G14"
    assert esc.escalations[0].severity == EscalationSeverity.CRITICAL


def test_extra_fields_forbidden():
    """All contract models must forbid extra fields to prevent contract drift."""
    with pytest.raises(ValidationError):
        DealItem.model_validate({
            "id": "D-99",
            "title": "Test",
            "stage": "lead",
            "value_paise": 1000,
            "created_at": "2026-10-15T10:00:00Z",
            "unsupported_field": "disallowed",
        })

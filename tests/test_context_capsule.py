"""
Unit and integration tests for Task-Scoped Context Capsules (T05.4).
Tests:
  - Happy path capsule assembly for D-1 demo task
  - Tenant and contact isolation: assert no other deal or contact data leaks
  - Untrusted text separation: customer text only appears in untrusted_text fields
  - Conflict terms handling (e.g. 6 weeks vs 8 weeks)
  - Hash stability: deterministic hash and stable capsule id across identical builds
  - Freshness check: rejection of stale record version
  - Fallback timezone handling
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from backend.contracts.capsule import ContextCapsule
from backend.domain.types import FactReference, FactValue, Money, TrustedFacts
from backend.services.context import (
    CapsuleIsolationError,
    CapsuleStaleError,
    ContextService,
    TaskContextInput,
    compute_capsule_content_hash,
)


@pytest.fixture
def base_d1_context_input() -> TaskContextInput:
    """Fixture representing D-1 Raju Malhotra task context."""
    facts = TrustedFacts(
        facts={
            "deal.price": FactValue(Money(48000000), FactReference("f1", "proposal")),  # ₹4,80,000
            "deal.monthly_support": FactValue(Money(1500000), FactReference("f2", "proposal")),  # ₹15,000/mo
            "catalog.SUP-ANNUAL.price": FactValue(Money(6000000), FactReference("f3", "catalog")),  # ₹60,000
        }
    )

    now_dt = datetime(2026, 10, 15, 10, 0, 0, tzinfo=timezone.utc)
    calendar_days = [
        {"date": "2026-10-15", "weekday": "Thu", "label": "Thu 15 Oct", "is_working_day": True},
        {"date": "2026-10-16", "weekday": "Fri", "label": "Fri 16 Oct", "is_working_day": True},
    ]

    return TaskContextInput(
        tenant_id="tenant-acme-1",
        task_id="task-d1-123",
        task_ref="T-101",
        task_kind="followup",
        task_instructions="Follow up on quiet proposal",
        allowed_action_types=["send_email", "book_meeting"],
        founder_name="Meera Nair",
        founder_signature="Meera",
        founder_business="Nair Automation Studio",
        founder_tz="Asia/Kolkata",
        contact_id="contact-raju-1",
        contact_ref="C-1",
        contact_name="Raju Malhotra",
        contact_first_name="Raju",
        contact_company="Malhotra Logistics",
        contact_tz="Asia/Kolkata",
        contact_autonomy_mode="mandate_governed",
        deal_id="deal-d1-uuid",
        deal_ref="D-1",
        deal_title="Warehouse WhatsApp-to-ERP order automation",
        deal_stage="proposal_sent",
        deal_days_quiet=4,
        deal_record_age_days=10,
        deal_record_version=1,
        deal_founder_notes="Price-sensitive. Flex only together with annual support (SUP-ANNUAL). Never more than 5% without me.",
        proposal_ref="PR-1",
        proposal_title="Warehouse automation proposal",
        proposal_sent_on_display="11 Oct 2026",
        proposal_terms_status="verified",
        mandate_ref="M7",
        mandate_clauses=["C1: followup", "C4: max discount 5%"],
        mandate_discount_max_pct="5.0",
        mandate_hard_ceiling_pct="10.0",
        kill_switch_engaged=False,
        thread_ref="TH-1",
        thread_subject="Proposal: Warehouse Automation",
        messages=[
            {
                "ref": "msg-1",
                "direction": "outbound",
                "sender": "meera@nairautomation.com",
                "recipient": "raju@malhotralogistics.in",
                "at_display": "11 Oct, 10:30 IST",
                "text": "Hi Raju, here is the proposal for your review.",
            },
            {
                "ref": "msg-2",
                "direction": "inbound",
                "sender": "raju@malhotralogistics.in",
                "recipient": "meera@nairautomation.com",
                "at_display": "15 Oct, 09:30 IST",
                "text": "The price is high. You promised 20% on our last call.",
                "risk_flags": ["claims_prior_commitment"],
            },
        ],
        trusted_facts=facts,
        conflicts=[("timeline", "6 weeks (p.2) vs 8 weeks (p.4) conflict in proposal document")],
        add_ons=[("SUP-ANNUAL", "Annual support & monitoring", "catalog.SUP-ANNUAL.price")],
        now_dt=now_dt,
        calendar_days=calendar_days,
    )


class TestContextCapsuleBuilder:
    """Test suite for ContextService capsule builder."""

    def test_d1_capsule_happy_path(self, base_d1_context_input: TaskContextInput):
        """Build D-1 capsule and verify fields and structure."""
        capsule, content_hash = ContextService.build_capsule(base_d1_context_input)

        assert isinstance(capsule, ContextCapsule)
        assert capsule.capsule_version == "1"
        assert capsule.tenant_id == "tenant-acme-1"
        assert capsule.contact.name == "Raju Malhotra"
        assert capsule.deal.ref == "D-1"
        assert capsule.authority.mandate_ref == "M7"
        assert len(capsule.facts) == 3
        assert len(capsule.conflicts) == 1
        assert "6 weeks (p.2) vs 8 weeks (p.4)" in capsule.conflicts[0].note

        # Verify fact formatting
        price_fact = next(f for f in capsule.facts if f.key == "deal.price")
        assert price_fact.display == "₹4,80,000"

    def test_untrusted_text_separation(self, base_d1_context_input: TaskContextInput):
        """Inbound customer text MUST only be in untrusted_text, never in trusted text."""
        capsule, _ = ContextService.build_capsule(base_d1_context_input)

        assert capsule.latest_inbound is not None
        assert capsule.latest_inbound.direction == "inbound"
        assert "promised 20%" in (capsule.latest_inbound.untrusted_text or "")
        assert capsule.latest_inbound.text is None  # Must NOT be in text field

        # Check outbound message
        outbound = next(m for m in capsule.thread.messages if m.direction == "outbound")
        assert outbound.text is not None
        assert outbound.untrusted_text is None

    def test_hash_stability_and_deterministic_id(self, base_d1_context_input: TaskContextInput):
        """Identical inputs produce identical content hash and capsule ID."""
        capsule1, hash1 = ContextService.build_capsule(base_d1_context_input)
        capsule2, hash2 = ContextService.build_capsule(base_d1_context_input)

        assert hash1 == hash2
        assert capsule1.capsule_id == capsule2.capsule_id

    def test_freshness_check_rejects_stale_record(self, base_d1_context_input: TaskContextInput):
        """Rejects capsule build when expected deal version does not match."""
        # Expected version 2, but ctx has version 1
        with pytest.raises(CapsuleStaleError, match="stale"):
            ContextService.build_capsule(base_d1_context_input, expected_record_version=2)

    def test_contact_and_deal_isolation(self, base_d1_context_input: TaskContextInput):
        """
        Isolation test: verify that unrelated deal/contact data (e.g. D-3 Priya Shah, Brightleaf)
        does NOT appear anywhere in the assembled D-1 capsule JSON.
        """
        capsule, _ = ContextService.build_capsule(base_d1_context_input)
        capsule_json = capsule.model_dump_json()

        # Unrelated entities
        assert "Priya Shah" not in capsule_json
        assert "Brightleaf Clinics" not in capsule_json
        assert "Arjun Mehta" not in capsule_json
        assert "kestrelfoods.in" not in capsule_json
        assert "Farhan" not in capsule_json

    def test_contact_without_timezone_defaults_to_founder_tz(self, base_d1_context_input: TaskContextInput):
        """When contact has no timezone, default to founder's timezone."""
        from dataclasses import replace
        ctx_no_tz = replace(base_d1_context_input, contact_tz=None)

        capsule, _ = ContextService.build_capsule(ctx_no_tz)
        assert capsule.contact.timezone == "Asia/Kolkata"
        assert capsule.now.contact_tz == "Asia/Kolkata"

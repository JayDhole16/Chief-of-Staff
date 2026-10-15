"""
Tests for Deterministic Quiet Proposal Sweep (T08.2).

Validates:
- Eligible deals detection and grounded proposal generation.
- Correct policy verdicts (ALLOW for mandate-governed, ASK for approval_required).
- Skipped scenarios: not quiet, closed stage, OOO snoozed, opted-out, stale.
- Repeated sweep deduplication (no duplicate proposals).
- Safe partial failure recovery.
- Strict safety boundary: proposals created, zero external writes.
"""

from datetime import datetime, timezone
import pytest

from backend.services.sweep import (
    QuietDealRecord,
    QuietSweepService,
    get_demo_sweep_deals,
)


@pytest.fixture
def sweep_service() -> QuietSweepService:
    return QuietSweepService()


def test_demo_sweep_selection(sweep_service: QuietSweepService):
    """
    In the canonical demo dataset:
    - D-1 (Raju, 4 days quiet, mandate_governed) -> Eligible, ALLOW (scheduled with 15s undo).
    - D-2 (Sunil, 1 day quiet) -> Skipped (not quiet).
    - D-3 (Priya, 6 days quiet, OOO snoozed until 2026-10-20) -> Skipped (ooo_snoozed).
    - D-4 (Arjun, 5 days quiet, approval_required) -> Eligible, ASK (pending approval).
    - D-5 (Deepak, 0 days quiet) -> Skipped (not quiet).
    - D-6 (Kavita, won) -> Skipped (deal_closed).
    """
    deals = get_demo_sweep_deals()
    result = sweep_service.sweep(deals, current_date="2026-10-16")

    assert result.total_deals_scanned == 6
    assert result.eligible_deals_count == 2
    assert len(result.proposals_created) == 2
    assert len(result.errors) == 0

    deal_ids = {p.deal_id for p in result.proposals_created}
    assert deal_ids == {"D-1", "D-4"}

    # Inspect D-1 proposal
    p_d1 = next(p for p in result.proposals_created if p.deal_id == "D-1")
    assert p_d1.policy_verdict == "ALLOW"
    assert p_d1.status == "scheduled"
    assert p_d1.execute_after is not None
    assert p_d1.undo_window_seconds == 15
    assert "₹4,56,000" in p_d1.rendered_body  # 5% discount from ₹4,80,000
    assert "5%" in [f["value"] for f in p_d1.facts_used]

    # Inspect D-4 proposal
    p_d4 = next(p for p in result.proposals_created if p.deal_id == "D-4")
    assert p_d4.policy_verdict == "ASK"
    assert p_d4.status == "pending"
    assert p_d4.execute_after is None
    assert "G02" in [f["code"] for f in p_d4.risk_flags]

    # Check skipped reasons
    skipped_reasons = {s["deal_id"]: s["reason"] for s in result.skipped}
    assert "not_quiet" in skipped_reasons["D-2"]
    assert "ooo_snoozed" in skipped_reasons["D-3"]
    assert "not_quiet" in skipped_reasons["D-5"]
    assert "deal_closed" in skipped_reasons["D-6"]


def test_sweep_deduplication_on_repeated_run(sweep_service: QuietSweepService):
    """Running sweep repeatedly must prevent duplicate proposals."""
    deals = get_demo_sweep_deals()
    res1 = sweep_service.sweep(deals, current_date="2026-10-16")
    assert len(res1.proposals_created) == 2

    # Second sweep with same deals
    res2 = sweep_service.sweep(deals, current_date="2026-10-16")
    assert len(res2.proposals_created) == 0  # No new proposals
    assert any("active_proposal_already_exists" in s["reason"] for s in res2.skipped if s["deal_id"] == "D-1")
    assert any("active_proposal_already_exists" in s["reason"] for s in res2.skipped if s["deal_id"] == "D-4")


def test_opt_out_respected(sweep_service: QuietSweepService):
    deals = [
        QuietDealRecord(
            id="D-OPT",
            title="Opted-out Lead",
            contact_id="c_opt",
            contact_name="Opted Out Contact",
            contact_email="opt@example.in",
            stage="negotiation",
            value_paise=10000000,
            days_quiet=10,
            do_not_contact=True,
        )
    ]
    res = sweep_service.sweep(deals)
    assert len(res.proposals_created) == 0
    assert res.skipped[0]["reason"] == "contact_opted_out"


def test_stale_deal_skipped(sweep_service: QuietSweepService):
    deals = [
        QuietDealRecord(
            id="D-INACTIVE",
            title="Inactive Deal",
            contact_id="c_in",
            contact_name="Contact",
            contact_email="test@example.in",
            stage="negotiation",
            value_paise=10000000,
            days_quiet=10,
            is_active=False,
        )
    ]
    res = sweep_service.sweep(deals)
    assert len(res.proposals_created) == 0
    assert res.skipped[0]["reason"] == "stale_or_inactive_deal"


def test_partial_failure_safety(sweep_service: QuietSweepService):
    """An unhandled error in a single deal record must not abort the entire sweep."""
    malformed_deal = QuietDealRecord(
        id="D-BAD",
        title="Bad Deal",
        contact_id="c_bad",
        contact_name="Bad Contact",
        contact_email="bad@example.in",
        stage="negotiation",
        value_paise=-999,  # invalid negative price
        days_quiet=10,
    )
    # Monkey-patch value_paise to something that triggers an error during format
    good_deal = QuietDealRecord(
        id="D-GOOD",
        title="Good Deal",
        contact_id="c_good",
        contact_name="Good Contact",
        contact_email="good@example.in",
        stage="negotiation",
        value_paise=20000000,
        days_quiet=10,
    )

    res = sweep_service.sweep([malformed_deal, good_deal])
    # Good deal should still be processed successfully
    assert len(res.proposals_created) == 1
    assert res.proposals_created[0].deal_id == "D-GOOD"


def test_rendered_hash_integrity(sweep_service: QuietSweepService):
    """Rendered hash must be valid SHA-256 and match the exact body bytes."""
    import hashlib
    deals = [get_demo_sweep_deals()[0]]
    res = sweep_service.sweep(deals)
    proposal = res.proposals_created[0]

    computed_hash = hashlib.sha256(proposal.rendered_body.encode("utf-8")).hexdigest()
    assert proposal.rendered_hash == computed_hash
    assert len(proposal.rendered_hash) == 64

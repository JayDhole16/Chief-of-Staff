import hashlib
from dataclasses import replace

import pytest

from backend.policy.engine import PolicyInput, evaluate_policy
from backend.services.actions import ServerRenderedAction, propose_action


@pytest.fixture
def safe_input() -> PolicyInput:
    return PolicyInput(
        session_valid=True,
        permission_granted=True,
        amount_paise=100_000,
        daily_limit_paise=500_000,
        contact_verified=True,
        task_scope_matches=True,
        required_facts_present=True,
        draft_grounded=True,
        unverified_commitment=False,
        currency="INR",
        discount_pct=5,
        mandate_max_discount_pct=5,
        price_paise=95_000,
        floor_price_paise=80_000,
        opted_out=False,
        within_business_window=True,
        contains_sensitive_data=False,
        grammar_ok=True,
    )


def test_policy_allows_valid_proposal(safe_input: PolicyInput):
    decision = evaluate_policy(safe_input)
    assert decision.verdict == "ALLOW"
    assert decision.guards_triggered == ()


@pytest.mark.parametrize(
    ("change", "guard", "verdict"),
    [
        ({"session_valid": False}, "G01", "BLOCK"),
        ({"permission_granted": False}, "G02", "BLOCK"),
        ({"amount_paise": 500_001}, "G03", "BLOCK"),
        ({"contact_verified": False}, "G04", "BLOCK"),
        ({"task_scope_matches": False}, "G05", "BLOCK"),
        ({"required_facts_present": False}, "G06", "BLOCK"),
        ({"draft_grounded": False}, "G07", "ASK"),
        ({"unverified_commitment": True}, "G08", "ASK"),
        ({"currency": "USD"}, "G09", "BLOCK"),
        ({"discount_pct": 6}, "G10", "ASK"),
        ({"price_paise": 79_999}, "G11", "BLOCK"),
        ({"opted_out": True}, "G12", "BLOCK"),
        ({"within_business_window": False}, "G13", "ASK"),
        ({"contains_sensitive_data": True}, "G14", "BLOCK"),
        ({"grammar_ok": False}, "G15", "ASK"),
    ],
)
def test_policy_emits_expected_reason_and_verdict(
    safe_input: PolicyInput, change: dict, guard: str, verdict: str
):
    decision = evaluate_policy(replace(safe_input, **change))
    assert decision.verdict == verdict
    assert guard in decision.guards_triggered
    assert len(decision.reasons) == len(decision.guards_triggered)


def test_founder_approval_resolves_ask_but_never_overrides_block(safe_input: PolicyInput):
    warning = evaluate_policy(
        replace(safe_input, discount_pct=6, explicit_founder_approval=True)
    )
    blocked = evaluate_policy(
        replace(
            safe_input,
            opted_out=True,
            explicit_founder_approval=True,
        )
    )
    assert warning.verdict == "ALLOW"
    assert warning.guards_triggered == ("G10",)
    assert blocked.verdict == "BLOCK"


def test_propose_action_hashes_content_and_never_executes(
    safe_input: PolicyInput,
):
    content = "Your verified proposal is ready."
    proposal = propose_action(
        ServerRenderedAction(
            action_ref="action-1",
            recipient_email="customer@example.invalid",
            subject="Proposal follow-up",
            rendered_body=content,
            policy_input=replace(safe_input, unverified_commitment=True),
        )
    )
    assert proposal.status == "pending_approval"
    assert proposal.rendered_hash == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert proposal.policy_decision.verdict == "ASK"


def test_propose_action_rejects_missing_recipient(safe_input: PolicyInput):
    with pytest.raises(ValueError, match="recipient_email"):
        propose_action(
            ServerRenderedAction(
                action_ref="action-1",
                recipient_email="not-an-email",
                subject="Proposal follow-up",
                rendered_body="Body",
                policy_input=safe_input,
            )
        )

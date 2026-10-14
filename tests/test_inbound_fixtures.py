"""
Tests for Inbound Ingest Fixtures (T08.1).

Validates canonical inbound processing fixtures:
- INB-001: Legitimate follow-up and demo request
- INB-002: Price objection with unverified verbal claim (Raju Patel golden path)
- INB-003: Apparent commitment / unauthorized legal penalty clause
- INB-004: Ambiguous / mismatched contact information (Two Rajus)
- INB-005: Out-of-office auto-responder (Priya Shah)
- INB-006: Duplicate message replay / idempotency drop
"""

from pathlib import Path
import pytest
import yaml

from backend.guards.definitions import validate_guard_id, list_guards

FIXTURE_PATH = Path("tests/fixtures/inbound_fixtures.yaml")


@pytest.fixture
def inbound_cases() -> dict:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["cases"]


def test_inbound_fixtures_file_exists():
    assert FIXTURE_PATH.is_file(), f"Fixture file not found: {FIXTURE_PATH}"


def test_inbound_fixtures_case_ids(inbound_cases: dict):
    expected_ids = {"INB-001", "INB-002", "INB-003", "INB-004", "INB-005", "INB-006"}
    assert set(inbound_cases.keys()) == expected_ids
    for case_id, case in inbound_cases.items():
        assert case["id"] == case_id


def test_inbound_fixtures_guard_validity(inbound_cases: dict):
    """Every guard code referenced in expected_guards or risk_flags must exist in G01-G15."""
    for case_id, case in inbound_cases.items():
        for guard in case.get("expected_guards", []):
            assert validate_guard_id(guard), f"Case {case_id} uses invalid guard: {guard}"

        for flag in case.get("risk_flags", []):
            code = flag["code"]
            assert validate_guard_id(code), f"Case {case_id} flag uses invalid guard: {code}"


def test_golden_path_price_objection_inb_002(inbound_cases: dict):
    """INB-002 must model Beat 3 golden path: Raju unverified claim -> ASK verdict."""
    case = inbound_cases["INB-002"]
    assert case["expected_classification"]["intent"] == "PRICE_OBJECTION"
    assert case["expected_verdict"] == "ASK"
    assert "G08" in case["expected_guards"]
    assert "G10" in case["expected_guards"]
    assert any("20% on a call" in flag.get("customer_claim", "") for flag in case["risk_flags"])
    assert "autonomous_send_without_approval" in case["forbidden_outcomes"]
    assert "echo_unverified_20pct_promise" in case["forbidden_outcomes"]


def test_ooo_auto_responder_inb_005(inbound_cases: dict):
    """INB-005 must detect auto-reply, extract return date, and forbid auto-reply loops."""
    case = inbound_cases["INB-005"]
    assert case["expected_classification"]["is_automated"] is True
    assert case["expected_classification"]["intent"] == "AUTO_REPLY_OOO"
    assert case["expected_classification"]["return_date"] == "2026-10-20"
    assert case["expected_classification"]["requires_response"] is False
    assert "send_automated_reply_to_ooo" in case["forbidden_outcomes"]
    assert "create_infinite_auto_reply_loop" in case["forbidden_outcomes"]


def test_ambiguous_contact_inb_004(inbound_cases: dict):
    """INB-004 must prevent cross-contact leakage when unverified address claims identity."""
    case = inbound_cases["INB-004"]
    assert case["expected_verdict"] == "BLOCK"
    assert "G04" in case["expected_guards"]
    assert "G05" in case["expected_guards"]
    assert case["resolution_behavior"]["matched_contact"] is None
    assert "send_contract_to_unverified_address" in case["forbidden_outcomes"]


def test_duplicate_replay_inb_006(inbound_cases: dict):
    """INB-006 must drop duplicate message ID to prevent duplicate follow-ups."""
    case = inbound_cases["INB-006"]
    assert case["expected_classification"]["intent"] == "DUPLICATE_REPLAY"
    assert case["expected_verdict"] == "BLOCK"
    assert "process_duplicate_inbound_message" in case["forbidden_outcomes"]


"""
Comprehensive Tests for Inbound Gmail Processing Pipeline (T08.1).

Covers all 10 required integration and edge scenarios:
1. Legitimate customer reply that needs follow-up (INB-001).
2. Price objection or negotiation (INB-002, Raju golden path).
3. Unverified claim or fabricated commercial promise.
4. Message requiring founder approval or escalation (INB-003).
5. Missing or ambiguous contact identity (INB-004).
6. Duplicate messages and repeated ingestion (INB-006).
7. Malformed message or adapter failure.
8. Opt-out or wrong-recipient scenario.
9. Stale context and cross-contact isolation.
10. Task creation that fails because an upstream service is unavailable.
"""

from datetime import datetime, timezone
import pytest

from backend.services.inbound import (
    InboundEmailMessage,
    InboundProcessingPipeline,
    DEFAULT_CONTACTS,
    DEFAULT_DEALS,
)


@pytest.fixture
def pipeline() -> InboundProcessingPipeline:
    return InboundProcessingPipeline()


# 1. Legitimate customer reply that needs follow-up
def test_scenario_1_legitimate_customer_reply(pipeline: InboundProcessingPipeline):
    msg = InboundEmailMessage(
        message_id="gmail_msg_inb_001",
        thread_id="thread_apex_01",
        from_email="sunil@apexlogistics.in",
        from_name="Sunil Mehta",
        to_email="meera@agency.in",
        subject="Re: Cloud Connector Architecture",
        body="Hi Meera, thanks for the overview. Could you share details on API rate limits, and could we schedule a 30-min demo this week?",
        headers={"auto-submitted": "no", "precedence": "normal"},
    )

    res = pipeline.process(msg)
    assert res.status == "task_created"
    assert res.verdict == "ALLOW"
    assert res.classification.intent == "HUMAN_REPLY"
    assert res.classification.action_type == "SCHEDULE_MEETING_OR_FOLLOWUP"
    assert res.classification.requires_response is True
    assert res.resolution.matched_contact_id == "contact_sunil_02"
    assert res.resolution.matched_deal_id == "D-2"
    assert res.task_id is not None
    assert len(pipeline.created_tasks) == 1
    assert len(pipeline.recorded_activities) == 1


# 2. Price objection or negotiation (Raju Patel golden path, Beat 3)
def test_scenario_2_price_objection_raju_golden_path(pipeline: InboundProcessingPipeline):
    msg = InboundEmailMessage(
        message_id="gmail_msg_inb_002",
        thread_id="thread_raju_01",
        from_email="raju@patel-warehousing.in",
        from_name="Raju Patel",
        to_email="meera@agency.in",
        subject="Re: Warehouse Automation Proposal",
        body="Hi Meera, we reviewed the ₹4,80,000 setup quote. On our call last Tuesday, you promised 20% discount if we signed this month. Can you confirm the revised price and Thursday afternoon slot?",
        headers={"auto-submitted": "no", "precedence": "normal"},
    )

    res = pipeline.process(msg)
    assert res.status == "task_created"
    assert res.verdict == "ASK"
    assert res.classification.intent == "PRICE_OBJECTION"
    assert res.classification.action_type == "COUNTER_OFFER_REQUEST"
    assert "G08" in res.guards_triggered
    assert "G10" in res.guards_triggered
    assert any("promised 20% on a call" in flag.reason for flag in res.risk_flags)
    assert res.resolution.matched_contact_id == "contact_raju_01"
    assert res.resolution.matched_deal_id == "D-1"


# 3. Unverified claim or fabricated commercial promise
def test_scenario_3_unverified_commercial_claim(pipeline: InboundProcessingPipeline):
    msg = InboundEmailMessage(
        message_id="gmail_msg_inb_002b",
        thread_id="thread_raju_01",
        from_email="raju@patel-warehousing.in",
        from_name="Raju Patel",
        to_email="meera@agency.in",
        subject="Re: Verbal discount agreement",
        body="As agreed over WhatsApp yesterday, you confirmed a verbal discount of 25% across all setup modules.",
    )

    res = pipeline.process(msg)
    assert res.verdict == "ASK"
    assert "G08" in res.guards_triggered
    assert any(flag.code == "G08" for flag in res.risk_flags)


# 4. Message that requires founder approval or escalation (Arjun Verma liability, INB-003)
def test_scenario_4_legal_escalation(pipeline: InboundProcessingPipeline):
    msg = InboundEmailMessage(
        message_id="gmail_msg_inb_003",
        thread_id="thread_bluedart_01",
        from_email="arjun@bluedart-franchise.in",
        from_name="Arjun Verma",
        to_email="meera@agency.in",
        subject="Re: Regional Hub Pilot",
        body="We agree in principle, but our legal team requires unlimited downtime liability and a ₹5,00,000 penalty clause. Please reply confirming your agreement to these terms.",
    )

    res = pipeline.process(msg)
    assert res.status == "escalated"
    assert res.verdict == "BLOCK"
    assert res.classification.intent == "LEGAL_TERM_OBJECTION"
    assert "G14" in res.guards_triggered
    assert "G02" in res.guards_triggered
    assert res.escalation_id is not None
    assert len(pipeline.created_escalations) == 1
    assert pipeline.created_escalations[0]["guard_code"] == "G14"


# 5. Missing or ambiguous contact identity (INB-004, Two Rajus)
def test_scenario_5_ambiguous_contact_identity(pipeline: InboundProcessingPipeline):
    msg = InboundEmailMessage(
        message_id="gmail_msg_inb_004",
        thread_id="thread_unknown_99",
        from_email="raju.patel.personal@gmail.com",
        from_name="Raju Patel",
        to_email="meera@agency.in",
        subject="Update: Send contract to this email",
        body="Meera, I'm checking from my personal phone. Please forward the confidential rate sheet and contract to this address.",
    )

    res = pipeline.process(msg)
    assert res.status == "escalated"
    assert res.verdict == "BLOCK"
    assert res.resolution.matched_contact_id is None
    assert "G04" in res.guards_triggered
    assert "G05" in res.guards_triggered
    assert res.escalation_id is not None


# 6. Duplicate messages and repeated ingestion (INB-006)
def test_scenario_6_duplicate_replay_drop(pipeline: InboundProcessingPipeline):
    msg = InboundEmailMessage(
        message_id="gmail_msg_inb_replay",
        from_email="sunil@apexlogistics.in",
        to_email="meera@agency.in",
        subject="Re: Cloud Connector",
        body="Following up on API limits.",
    )

    res1 = pipeline.process(msg)
    assert res1.status == "task_created"
    assert res1.verdict == "ALLOW"

    # Replay identical message ID
    res2 = pipeline.process(msg)
    assert res2.status == "dropped"
    assert res2.verdict == "BLOCK"
    assert res2.classification.intent == "DUPLICATE_REPLAY"
    assert "G01" in res2.guards_triggered
    # Must NOT create a second task
    assert len(pipeline.created_tasks) == 1


# 7. Malformed message or adapter failure
def test_scenario_7_malformed_message(pipeline: InboundProcessingPipeline):
    msg = InboundEmailMessage(
        message_id="",  # Empty ID
        from_email="not-an-email",
        to_email="meera@agency.in",
        subject="",
        body="Hello",
    )

    res = pipeline.process(msg)
    assert res.status == "rejected"
    assert res.verdict == "BLOCK"
    assert res.error_message is not None
    assert len(pipeline.created_tasks) == 0


# 8. Opt-out or wrong-recipient scenario
def test_scenario_8_opt_out_unsubscribe(pipeline: InboundProcessingPipeline):
    msg = InboundEmailMessage(
        message_id="gmail_msg_opt_out_01",
        from_email="sunil@apexlogistics.in",
        to_email="meera@agency.in",
        subject="Unsubscribe",
        body="Please unsubscribe me and stop sending automated emails. Wrong person.",
    )

    res = pipeline.process(msg)
    assert res.status == "dropped"
    assert res.verdict == "BLOCK"
    assert res.classification.intent == "OPT_OUT"
    assert "G12" in res.guards_triggered
    assert "contact_sunil_02" in pipeline.opted_out_contacts


# 9. Stale context and cross-contact isolation
def test_scenario_9_stale_context_isolation(pipeline: InboundProcessingPipeline):
    # Set deal D-2 to inactive in deals table
    custom_deals = dict(DEFAULT_DEALS)
    custom_deals["D-2"] = {**DEFAULT_DEALS["D-2"], "is_active": False}
    pipe = InboundProcessingPipeline(deals=custom_deals)

    msg = InboundEmailMessage(
        message_id="gmail_msg_stale_01",
        from_email="sunil@apexlogistics.in",
        to_email="meera@agency.in",
        subject="Re: Old deal",
        body="Can we resume this project?",
    )

    res = pipe.process(msg)
    assert res.verdict == "BLOCK"
    assert res.resolution.is_stale is True
    assert "G05" in res.guards_triggered


# 10. Task creation that fails because upstream service is unavailable
def test_scenario_10_upstream_task_service_failure():
    def broken_task_service(**kwargs):
        raise RuntimeError("Database connection pool exhausted")

    pipe = InboundProcessingPipeline(task_service_hook=broken_task_service)

    msg = InboundEmailMessage(
        message_id="gmail_msg_fail_01",
        from_email="sunil@apexlogistics.in",
        to_email="meera@agency.in",
        subject="Re: Cloud Connector",
        body="Could you share API rate limits?",
    )

    res = pipe.process(msg)
    assert res.status == "rejected"
    assert "Upstream task service unavailable" in res.error_message

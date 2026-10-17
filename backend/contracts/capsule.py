"""
Context Capsule contracts per BACKEND_SCHEMA §7.3 and TRD §9.2 / §9.3.
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from backend.contracts import CompatBaseModel


class CapsuleTask(CompatBaseModel):
    """Task metadata visible to the agent."""

    ref: str
    kind: Literal["followup", "inbound_reply", "scheduling", "founder_request"]
    instructions: str | None = None
    allowed_action_types: list[str] = Field(default_factory=list)


class CapsuleNow(CompatBaseModel):
    """Timestamp perspective for founder and contact."""

    utc: str
    founder_tz: str
    founder_local_display: str
    contact_tz: str
    contact_local_display: str


class CapsuleCalendarDay(CompatBaseModel):
    """One day in the founder's 14-day horizon."""

    date: str  # YYYY-MM-DD
    weekday: str  # e.g. "Thu"
    label: str  # e.g. "Thu 15 Oct"
    is_working_day: bool


class CapsuleFounder(CompatBaseModel):
    """Founder profile details."""

    name: str
    signature_name: str
    business_name: str


class CapsuleContact(CompatBaseModel):
    """Contact metadata with trust/autonomy mode."""

    ref: str
    name: str
    first_name: str
    company: str
    timezone: str
    autonomy_mode: Literal["mandate_governed", "approval_required"]


class CapsuleDeal(CompatBaseModel):
    """Deal metadata."""

    ref: str
    title: str
    stage: str
    days_quiet: int
    record_age_days: int
    founder_notes: str | None = None


class CapsuleProposal(CompatBaseModel):
    """Proposal metadata if attached."""

    ref: str
    title: str
    sent_on_display: str
    terms_status: str


class CapsuleFact(CompatBaseModel):
    """Verified fact available for template interpolation."""

    key: str
    display: str
    source: str


class CapsuleConflict(CompatBaseModel):
    """Conflicting terms: do not state this."""

    key: str
    note: str


class CapsuleAddOn(CompatBaseModel):
    """Allowed catalog add-on."""

    sku: str
    name: str
    fact_key: str


class CapsuleOfferOptions(CompatBaseModel):
    """Offer limits and allowed add-ons."""

    allowed_add_ons: list[CapsuleAddOn] = Field(default_factory=list)
    autonomous_discount_max_pct: str
    hard_ceiling_pct: str


class CapsuleMessage(CompatBaseModel):
    """A message in the thread conversation."""

    ref: str
    direction: Literal["inbound", "outbound"]
    sender: str
    recipient: str
    at_display: str
    untrusted_text: str | None = None  # Inbound only (customer-controlled)
    text: str | None = None  # Outbound only
    risk_flags: list[str] = Field(default_factory=list)


class CapsuleThread(CompatBaseModel):
    """Conversation thread up to 6 messages."""

    ref: str
    subject: str
    new_thread_required: bool = False
    messages: list[CapsuleMessage] = Field(default_factory=list)


class CapsuleAuthority(CompatBaseModel):
    """Mandate and kill switch authority summary."""

    mandate_ref: str | None = None
    clause_lines: list[str] = Field(default_factory=list)
    contact_requires_approval: bool
    kill_switch_engaged: bool
    summary: str


class CapsuleLimits(CompatBaseModel):
    """Safety limits for action drafting."""

    max_body_chars: int = 2000
    max_actions: int = 1


class ContextCapsule(CompatBaseModel):
    """
    Context Capsule: the only view of business data an agent gets.
    Implements BACKEND_SCHEMA §7.3 and TRD §9.2 / §9.3.
    """

    capsule_id: UUID
    capsule_version: Literal["1"] = "1"
    tenant_id: str
    task: CapsuleTask
    now: CapsuleNow
    calendar_days: list[CapsuleCalendarDay]
    founder: CapsuleFounder
    contact: CapsuleContact
    deal: CapsuleDeal
    proposal: CapsuleProposal | None = None
    facts: list[CapsuleFact] = Field(default_factory=list)
    conflicts: list[CapsuleConflict] = Field(default_factory=list)
    offer_options: CapsuleOfferOptions
    thread: CapsuleThread | None = None
    latest_inbound: CapsuleMessage | None = None
    authority: CapsuleAuthority
    rules: list[str] = Field(default_factory=list)
    limits: CapsuleLimits = CapsuleLimits()

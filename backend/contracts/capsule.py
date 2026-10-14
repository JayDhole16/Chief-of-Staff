"""
Context Capsule contracts per BACKEND_SCHEMA §7.3 and TRD §9.2 / §9.3.
"""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CapsuleTask(BaseModel):
    """Task metadata visible to the agent."""
    model_config = ConfigDict(extra="forbid")

    ref: str
    kind: Literal["followup", "inbound_reply", "scheduling", "founder_request"]
    instructions: str | None = None
    allowed_action_types: list[str] = Field(default_factory=list)


class CapsuleNow(BaseModel):
    """Timestamp perspective for founder and contact."""
    model_config = ConfigDict(extra="forbid")

    utc: str
    founder_tz: str
    founder_local_display: str
    contact_tz: str
    contact_local_display: str


class CapsuleCalendarDay(BaseModel):
    """One day in the founder's 14-day horizon."""
    model_config = ConfigDict(extra="forbid")

    date: str  # YYYY-MM-DD
    weekday: str  # e.g. "Thu"
    label: str  # e.g. "Thu 15 Oct"
    is_working_day: bool


class CapsuleFounder(BaseModel):
    """Founder profile details."""
    model_config = ConfigDict(extra="forbid")

    name: str
    signature_name: str
    business_name: str


class CapsuleContact(BaseModel):
    """Contact metadata with trust/autonomy mode."""
    model_config = ConfigDict(extra="forbid")

    ref: str
    name: str
    first_name: str
    company: str
    timezone: str
    autonomy_mode: Literal["mandate_governed", "approval_required"]


class CapsuleDeal(BaseModel):
    """Deal metadata."""
    model_config = ConfigDict(extra="forbid")

    ref: str
    title: str
    stage: str
    days_quiet: int
    record_age_days: int
    founder_notes: str | None = None


class CapsuleProposal(BaseModel):
    """Proposal metadata if attached."""
    model_config = ConfigDict(extra="forbid")

    ref: str
    title: str
    sent_on_display: str
    terms_status: str


class CapsuleFact(BaseModel):
    """Verified fact available for template interpolation."""
    model_config = ConfigDict(extra="forbid")

    key: str
    display: str
    source: str


class CapsuleConflict(BaseModel):
    """Conflicting terms: do not state this."""
    model_config = ConfigDict(extra="forbid")

    key: str
    note: str


class CapsuleAddOn(BaseModel):
    """Allowed catalog add-on."""
    model_config = ConfigDict(extra="forbid")

    sku: str
    name: str
    fact_key: str


class CapsuleOfferOptions(BaseModel):
    """Offer limits and allowed add-ons."""
    model_config = ConfigDict(extra="forbid")

    allowed_add_ons: list[CapsuleAddOn] = Field(default_factory=list)
    autonomous_discount_max_pct: str
    hard_ceiling_pct: str


class CapsuleMessage(BaseModel):
    """A message in the thread conversation."""
    model_config = ConfigDict(extra="forbid")

    ref: str
    direction: Literal["inbound", "outbound"]
    sender: str
    recipient: str
    at_display: str
    untrusted_text: str | None = None  # Inbound only (customer-controlled)
    text: str | None = None  # Outbound only
    risk_flags: list[str] = Field(default_factory=list)


class CapsuleThread(BaseModel):
    """Conversation thread up to 6 messages."""
    model_config = ConfigDict(extra="forbid")

    ref: str
    subject: str
    new_thread_required: bool = False
    messages: list[CapsuleMessage] = Field(default_factory=list)


class CapsuleAuthority(BaseModel):
    """Mandate and kill switch authority summary."""
    model_config = ConfigDict(extra="forbid")

    mandate_ref: str | None = None
    clause_lines: list[str] = Field(default_factory=list)
    contact_requires_approval: bool
    kill_switch_engaged: bool
    summary: str


class CapsuleLimits(BaseModel):
    """Safety limits for action drafting."""
    model_config = ConfigDict(extra="forbid")

    max_body_chars: int = 2000
    max_actions: int = 1


class ContextCapsule(BaseModel):
    """
    Context Capsule: the only view of business data an agent gets.
    Implements BACKEND_SCHEMA §7.3 and TRD §9.2 / §9.3.
    """
    model_config = ConfigDict(extra="forbid")

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


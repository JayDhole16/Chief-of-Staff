"""
Read API Contract Models (T08.4).

Pure contracts defining response schemas and query parameters for:
- /activity: Action lifecycle feed and audit events
- /receipts/{ref_or_id}: Terminal action receipts
- /deals: Sales pipeline and deal quietness status
- /escalations: Out-of-bounds or flagged items requiring founder review
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field

from backend.contracts import CompatBaseModel


class ActivityType(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    EXECUTION = "execution"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ActivityEventItem(CompatBaseModel):
    id: str
    timestamp: datetime
    type: ActivityType
    title: str
    description: str
    user_id: str
    action_ref: str | None = None
    receipt_id: str | None = None
    escalation_id: str | None = None
    rendered_hash: str | None = None
    execute_after: datetime | None = None
    can_undo: bool = False


class ActivityFeedResponse(CompatBaseModel):
    events: list[ActivityEventItem]
    count: int
    has_more: bool = False
    next_cursor: str | None = None


class ReceiptStatus(str, Enum):
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ReceiptFactItem(CompatBaseModel):
    key: str
    label: str
    value: str
    source: str


class ReceiptTimelineItem(CompatBaseModel):
    timestamp: datetime
    event: str


class ActionReceiptResponse(CompatBaseModel):
    receipt_id: str
    action_ref: str
    action_kind: Literal["email", "calendar"]
    status: ReceiptStatus
    authority_clause: str
    recipient_email: str | None = None
    meeting_time: str | None = None
    external_id: str | None = None  # Google Gmail/Calendar ID
    rendered_hash: str
    checks_passed: list[str] = Field(default_factory=list)
    facts_used: list[ReceiptFactItem] = Field(default_factory=list)
    executed_at: datetime | None = None
    cancelled_at: datetime | None = None
    undo_window_seconds: int | None = None
    timeline: list[ReceiptTimelineItem] = Field(default_factory=list)


class DealStage(str, Enum):
    LEAD = "lead"
    NEGOTIATION = "negotiation"
    APPROVED = "approved"
    ACTIVE = "active"
    MEETING_SCHEDULED = "meeting_scheduled"
    WON = "won"


class DealItem(CompatBaseModel):
    id: str
    title: str
    contact_name: str | None = None
    contact_email: str | None = None
    stage: DealStage
    value_paise: int = Field(ge=0)
    created_at: datetime
    days_quiet: int = Field(default=0, ge=0)
    is_quiet: bool = False
    last_interaction: datetime | None = None


class PipelineDealsResponse(CompatBaseModel):
    deals: list[DealItem]
    count: int
    total_pipeline_paise: int = Field(ge=0)


class EscalationSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


class EscalationItem(CompatBaseModel):
    escalation_id: str
    created_at: datetime
    severity: EscalationSeverity
    source_message_id: str | None = None
    deal_id: str | None = None
    contact_email: str | None = None
    reason: str
    guard_code: str | None = None
    status: Literal["open", "resolved", "dismissed"] = "open"


class EscalationsResponse(CompatBaseModel):
    escalations: list[EscalationItem]
    count: int

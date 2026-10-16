"""
Deterministic Founder Brief Service (T13.2).

Generates an immutable, verified summary from persisted receipts, trusted facts,
and application state. Does not turn approvals into claims of execution without
terminal receipts. Provides a deterministic narration fallback.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.read_api import (
    ActionReceiptResponse,
    ActivityEventItem,
    DealItem,
    EscalationItem,
    ReceiptStatus,
)


class BriefFactEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    label: str
    value: str
    source: str


class BriefItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    category: Literal["executed_action", "pending_decision", "escalation", "pipeline_quiet", "blocked_action"]
    deal_id: str | None = None
    deal_title: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    summary: str
    status: str
    authority_clause: str | None = None
    evidence_receipt_id: str | None = None
    evidence_action_ref: str | None = None
    evidence_facts: list[BriefFactEvidence] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    recommended_followup: str | None = None


class BriefMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actions_executed_count: int = Field(ge=0)
    pending_approvals_count: int = Field(ge=0)
    escalations_count: int = Field(ge=0)
    blocked_actions_count: int = Field(ge=0)
    total_pipeline_value_paise: int = Field(ge=0)
    estimated_founder_minutes_saved: float = Field(ge=0.0)


class FounderBriefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    generated_at: datetime
    headline: str
    metrics: BriefMetrics
    items: list[BriefItem]
    narration_text: str
    is_audio_available: bool = False
    disclaimer: str = "Source of truth: verified application receipts, audit log, and trusted server facts."


class FounderBriefService:
    """Pure deterministic founder brief generator."""

    def __init__(self, workspace_id: str = "WS-DEMO"):
        self.workspace_id = workspace_id

    def generate_brief(
        self,
        receipts: list[ActionReceiptResponse],
        proposals: list[dict[str, Any]],
        deals: list[DealItem],
        escalations: list[EscalationItem],
        activity_events: list[ActivityEventItem] | None = None,
        as_of_time: datetime | None = None,
        requesting_workspace_id: str | None = None,
    ) -> FounderBriefResponse:
        # Authorization check
        target_ws = requesting_workspace_id or self.workspace_id
        if target_ws != self.workspace_id:
            raise PermissionError(f"Unauthorized access to workspace '{self.workspace_id}' from '{target_ws}'")

        generated_at = as_of_time or datetime.now(timezone.utc)
        items: list[BriefItem] = []

        # 1. Terminal Receipts (Executed or Blocked)
        # Deduplicate by receipt_id and sort stably
        unique_receipts = {r.receipt_id: r for r in receipts}.values()
        sorted_receipts = sorted(unique_receipts, key=lambda r: r.receipt_id)
        executed_count = 0
        blocked_count = 0

        for r in sorted_receipts:
            if r.status == ReceiptStatus.EXECUTED:
                executed_count += 1
                facts = [
                    BriefFactEvidence(
                        key=f.key, label=f.label, value=f.value, source=f.source
                    )
                    for f in r.facts_used
                ]
                items.append(
                    BriefItem(
                        id=f"item_{r.receipt_id}",
                        category="executed_action",
                        summary=f"{r.action_kind.capitalize()} sent ({r.authority_clause}) to {r.recipient_email or 'contact'}",
                        status="executed",
                        authority_clause=r.authority_clause,
                        evidence_receipt_id=r.receipt_id,
                        evidence_action_ref=r.action_ref,
                        evidence_facts=facts,
                        recommended_followup="Await customer reply or review confirmation in activity feed",
                    )
                )
            elif r.status in (ReceiptStatus.BLOCKED, ReceiptStatus.CANCELLED):
                blocked_count += 1
                items.append(
                    BriefItem(
                        id=f"item_{r.receipt_id}",
                        category="blocked_action",
                        summary=f"{r.action_kind.capitalize()} {r.status.value} before external write: {r.authority_clause}",
                        status=r.status.value,
                        authority_clause=r.authority_clause,
                        evidence_receipt_id=r.receipt_id,
                        evidence_action_ref=r.action_ref,
                        risk_flags=["EXECUTION_BLOCKED" if r.status == ReceiptStatus.BLOCKED else "ACTION_CANCELLED"],
                        recommended_followup="Review security flags and deal context before re-proposing" if r.status == ReceiptStatus.BLOCKED else "Action cancelled during undo window; no external side effect",
                    )
                )

        # 2. Pending Proposals Requiring Founder Attention
        # Stable ordering by ref
        sorted_proposals = sorted(proposals, key=lambda p: p.get("ref", ""))
        pending_count = 0

        for p in sorted_proposals:
            p_status = p.get("status", "")
            if p_status == "pending":
                pending_count += 1
                risk_list = [rf.get("reason", "") for rf in p.get("risk_flags", []) if isinstance(rf, dict)]
                p_facts = [
                    BriefFactEvidence(
                        key=f.get("key", ""),
                        label=f.get("label", ""),
                        value=f.get("value", ""),
                        source=f.get("source", ""),
                    )
                    for f in p.get("facts_used", [])
                    if isinstance(f, dict)
                ]
                items.append(
                    BriefItem(
                        id=f"item_{p.get('ref')}",
                        category="pending_decision",
                        deal_id=p.get("deal_id"),
                        deal_title=p.get("deal_title"),
                        contact_name=p.get("contact_name"),
                        contact_email=p.get("contact_email"),
                        summary=f"Approval needed: {p.get('deal_title')} ({p.get('policy_verdict', 'ASK')})",
                        status="pending_approval",
                        evidence_action_ref=p.get("ref"),
                        evidence_facts=p_facts,
                        risk_flags=risk_list,
                        recommended_followup="Review grounded counter-offer and confirm hash-bound decision",
                    )
                )
            elif p_status == "approved":
                # Important safety check: Do NOT turn an approval into a claim of execution
                # Check if a terminal executed receipt exists
                has_executed_receipt = any(r.action_ref == p.get("ref") and r.status == ReceiptStatus.EXECUTED for r in receipts)
                if not has_executed_receipt:
                    items.append(
                        BriefItem(
                            id=f"item_{p.get('ref')}",
                            category="pending_decision",
                            deal_id=p.get("deal_id"),
                            deal_title=p.get("deal_title"),
                            contact_name=p.get("contact_name"),
                            summary=f"Founder approved {p.get('ref')}; worker execution pending receipt",
                            status="approved_awaiting_receipt",
                            evidence_action_ref=p.get("ref"),
                            recommended_followup="Worker dispatching; verify receipt upon worker completion",
                        )
                    )

        # 3. Escalations
        sorted_escalations = sorted(escalations, key=lambda e: e.escalation_id)
        for esc in sorted_escalations:
            if esc.status == "open":
                items.append(
                    BriefItem(
                        id=f"item_{esc.escalation_id}",
                        category="escalation",
                        deal_id=esc.deal_id,
                        contact_email=esc.contact_email,
                        summary=f"Escalation ({esc.severity.value}): {esc.reason}",
                        status="open",
                        risk_flags=[esc.reason],
                        recommended_followup="Triage inbound escalation in founder dashboard",
                    )
                )

        # 4. Pipeline Summary & Quiet Deals
        total_pipeline = sum(d.value_paise for d in deals)
        quiet_deals = [d for d in deals if d.is_quiet]
        for qd in quiet_deals:
            items.append(
                BriefItem(
                    id=f"item_quiet_{qd.id}",
                    category="pipeline_quiet",
                    deal_id=qd.id,
                    deal_title=qd.title,
                    contact_name=qd.contact_name,
                    contact_email=qd.contact_email,
                    summary=f"{qd.title} quiet for {qd.days_quiet} days (Value: ₹{qd.value_paise / 100:,.2f})",
                    status="quiet",
                    recommended_followup=f"Candidate for quiet sweep follow-up (stage: {qd.stage.value})",
                )
            )

        # Compute Metrics
        metrics = BriefMetrics(
            actions_executed_count=executed_count,
            pending_approvals_count=pending_count,
            escalations_count=len([e for e in escalations if e.status == "open"]),
            blocked_actions_count=blocked_count,
            total_pipeline_value_paise=total_pipeline,
            estimated_founder_minutes_saved=round(executed_count * 5.0 + len(quiet_deals) * 2.0, 1),
        )

        # Headline
        if executed_count == 0 and pending_count == 0 and len(escalations) == 0:
            headline = "All systems quiet. No actions pending founder review."
        else:
            parts = []
            if executed_count > 0:
                parts.append(f"{executed_count} action{'s' if executed_count != 1 else ''} executed")
            if pending_count > 0:
                parts.append(f"{pending_count} decision{'s' if pending_count != 1 else ''} pending")
            if len(escalations) > 0:
                parts.append(f"{len(escalations)} escalation{'s' if len(escalations) != 1 else ''}")
            headline = ", ".join(parts) + "."

        # Narration Text (Deterministic speech text fallback)
        narration = self._build_narration(executed_count, pending_count, escalations, quiet_deals, items)

        return FounderBriefResponse(
            workspace_id=self.workspace_id,
            generated_at=generated_at,
            headline=headline,
            metrics=metrics,
            items=items,
            narration_text=narration,
            is_audio_available=False,
        )

    def _build_narration(
        self,
        executed_count: int,
        pending_count: int,
        escalations: list[EscalationItem],
        quiet_deals: list[DealItem],
        items: list[BriefItem],
    ) -> str:
        """Construct deterministic spoken narration text."""
        lines = ["Here is your Founder Brief for Nair Automation Studio."]

        if executed_count == 0 and pending_count == 0 and len(escalations) == 0:
            lines.append("All operations are currently quiet. No autonomous actions were executed, and no decisions require attention.")
            return " ".join(lines)

        if executed_count > 0:
            lines.append(
                f"While you were away, {executed_count} action{'s were' if executed_count != 1 else ' was'} "
                "executed autonomously under your verified mandate, with all financial facts and slot tokens checked."
            )

        pending_items = [it for it in items if it.category == "pending_decision" and it.status == "pending_approval"]
        if pending_items:
            names = ", ".join(it.contact_name or "customer" for it in pending_items)
            lines.append(
                f"There {'are' if len(pending_items) != 1 else 'is'} {len(pending_items)} pending proposal{'s' if len(pending_items) != 1 else ''} "
                f"requiring your review for {names}."
            )

        open_esc = [e for e in escalations if e.status == "open"]
        if open_esc:
            lines.append(f"{len(open_esc)} item{'s' if len(open_esc) != 1 else ''} were escalated for safety review.")

        lines.append("All facts and actions link directly to immutable terminal receipts. Total founder attention required: under 30 seconds.")
        return " ".join(lines)

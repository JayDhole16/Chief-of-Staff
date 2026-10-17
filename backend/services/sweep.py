"""
Deterministic Quiet Proposal Sweep Service (T08.2).

Identifies quiet deals under active mandates, checks eligibility criteria,
respects opt-outs, OOO snoozes, and stale context, and produces deterministic,
grounded proposed actions (never performs external writes).

Implements BACKEND_SCHEMA §7.4, TRD §9.3, and Phase 8 specifications.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import hashlib
from typing import Any, Literal
from uuid import uuid4

from backend.domain.types import Discount, DiscountType
from backend.facts.inr_formatter import format_inr
from backend.facts.trusted_render import calculate_offer


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class QuietDealRecord:
    """Deal record for sweep evaluation."""
    id: str  # e.g. "D-1"
    title: str
    contact_id: str
    contact_name: str
    contact_email: str
    stage: str  # lead, negotiation, proposal_sent, active, won, lost
    value_paise: int
    days_quiet: int
    max_discount_pct: int = 5
    do_not_contact: bool = False
    is_active: bool = True
    autonomy_mode: Literal["mandate_governed", "approval_required"] = "mandate_governed"
    snooze_until: str | None = None  # YYYY-MM-DD
    last_interaction: datetime | None = None


@dataclass
class SweepProposal:
    """Generated proposal from quiet sweep."""
    ref: str
    kind: Literal["email", "calendar"]
    deal_id: str
    deal_title: str
    contact_name: str
    contact_email: str
    subject: str
    rendered_body: str
    rendered_hash: str
    facts_used: list[dict[str, str]]
    risk_flags: list[dict[str, Any]]
    policy_verdict: Literal["ALLOW", "ASK", "BLOCK"]
    policy_reasons: list[str]
    created_at: str
    expires_at: str
    status: Literal["pending", "scheduled", "approved", "rejected"]
    execute_after: str | None = None
    undo_window_seconds: int = 15


@dataclass
class SweepResult:
    """Result of a quiet sweep execution."""
    timestamp: datetime
    total_deals_scanned: int
    eligible_deals_count: int
    proposals_created: list[SweepProposal]
    skipped: list[dict[str, str]]  # list of {deal_id, reason}
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default Demo Deals for Sweep
# ---------------------------------------------------------------------------

def get_demo_sweep_deals() -> list[QuietDealRecord]:
    """Returns canonical demo deals matching t00.6-portable and Beat 0/Beat 3."""
    return [
        QuietDealRecord(
            id="D-1",
            title="Warehouse WhatsApp-to-ERP order automation",
            contact_id="contact_raju_01",
            contact_name="Raju Patel",
            contact_email="raju@patel-warehousing.in",
            stage="proposal_sent",
            value_paise=48000000,  # ₹4,80,000
            days_quiet=4,
            max_discount_pct=5,
            autonomy_mode="mandate_governed",
        ),
        QuietDealRecord(
            id="D-2",
            title="Cloud Connector Architecture",
            contact_id="contact_sunil_02",
            contact_name="Sunil Mehta",
            contact_email="sunil@apexlogistics.in",
            stage="lead",
            value_paise=250000000,  # ₹25,00,000
            days_quiet=1,  # Not quiet (< 3 days)
            max_discount_pct=0,
            autonomy_mode="mandate_governed",
        ),
        QuietDealRecord(
            id="D-3",
            title="Inventory Sync",
            contact_id="contact_priya_03",
            contact_name="Priya Shah",
            contact_email="priya@quickship.in",
            stage="proposal_sent",
            value_paise=180000000,  # ₹18,00,000
            days_quiet=6,
            max_discount_pct=5,
            autonomy_mode="mandate_governed",
            snooze_until="2026-10-20",  # OOO auto-responder from INB-005
        ),
        QuietDealRecord(
            id="D-4",
            title="Regional Hub Pilot",
            contact_id="contact_arjun_04",
            contact_name="Arjun Verma",
            contact_email="arjun@bluedart-franchise.in",
            stage="proposal_sent",
            value_paise=300000000,  # ₹30,00,000
            days_quiet=5,
            max_discount_pct=0,
            autonomy_mode="approval_required",  # Requires founder approval
        ),
        QuietDealRecord(
            id="D-5",
            title="ExpressCargo Route Automation",
            contact_id="contact_deepak_05",
            contact_name="Deepak Roy",
            contact_email="deepak@expresscargo.in",
            stage="active",
            value_paise=150000000,
            days_quiet=0,  # Not quiet
            max_discount_pct=0,
            autonomy_mode="mandate_governed",
        ),
        QuietDealRecord(
            id="D-6",
            title="MegaFreight ERP Integration",
            contact_id="contact_kavita_06",
            contact_name="Kavita Nair",
            contact_email="kavita@megafreight.in",
            stage="won",  # Closed / won
            value_paise=450000000,
            days_quiet=10,
            max_discount_pct=0,
            autonomy_mode="mandate_governed",
        ),
    ]


# ---------------------------------------------------------------------------
# Sweep Service Implementation
# ---------------------------------------------------------------------------

class QuietSweepService:
    """
    Deterministic Quiet Sweep Engine.
    Evaluates quiet deals and produces ProposedActions.
    Never sends external writes.
    """

    def __init__(
        self,
        quiet_threshold_days: int = 3,
        mandate_max_discount_pct: int = 5,
        mandate_ref: str = "Mandate M-2026-10-15 Clause C2",
        proposal_store: dict[str, SweepProposal] | None = None,
        activity_store: list[dict[str, Any]] | None = None,
    ):
        self.quiet_threshold_days = quiet_threshold_days
        self.mandate_max_discount_pct = mandate_max_discount_pct
        self.mandate_ref = mandate_ref
        self.proposal_store = proposal_store if proposal_store is not None else {}
        self.activity_store = activity_store if activity_store is not None else []

    def sweep(
        self,
        deals: list[QuietDealRecord],
        current_date: str = "2026-10-16",
        founder_name: str = "Meera Nair",
    ) -> SweepResult:
        """
        Execute deterministic sweep over deals.
        """
        now = datetime.now(timezone.utc)
        scanned_count = len(deals)
        eligible_count = 0
        proposals_created: list[SweepProposal] = []
        skipped: list[dict[str, str]] = []
        errors: list[str] = []

        for deal in deals:
            try:
                # 1. Opt-out check
                if deal.do_not_contact:
                    skipped.append({"deal_id": deal.id, "reason": "contact_opted_out"})
                    continue

                # 2. Inactive / Stale context check
                if not deal.is_active:
                    skipped.append({"deal_id": deal.id, "reason": "stale_or_inactive_deal"})
                    continue

                # 3. Closed deal check
                if deal.stage in ("won", "lost", "archived"):
                    skipped.append({"deal_id": deal.id, "reason": f"deal_closed_stage_{deal.stage}"})
                    continue

                # 4. Quiet threshold check
                if deal.days_quiet < self.quiet_threshold_days:
                    skipped.append({"deal_id": deal.id, "reason": f"not_quiet_days_{deal.days_quiet}_under_{self.quiet_threshold_days}"})
                    continue

                # 5. OOO Snooze check
                if deal.snooze_until and deal.snooze_until > current_date:
                    skipped.append({"deal_id": deal.id, "reason": f"ooo_snoozed_until_{deal.snooze_until}"})
                    continue

                # 6. Deduplication: check if active proposal already exists for deal
                existing = [
                    p for p in self.proposal_store.values()
                    if p.deal_id == deal.id and p.status in ("pending", "scheduled")
                ]
                if existing:
                    skipped.append({"deal_id": deal.id, "reason": f"active_proposal_already_exists_{existing[0].ref}"})
                    continue

                # Validate price before counting as eligible
                formatted_base_price = format_inr(deal.value_paise)

                # Calculate proposal numbers with exact integer/Decimal math via calculate_offer
                discount_pct = max(0, min(deal.max_discount_pct, self.mandate_max_discount_pct))
                final_price_paise = calculate_offer(
                    base_price_paise=deal.value_paise,
                    discount=Discount(DiscountType.PERCENTAGE, discount_pct),
                    mandate_max_discount_pct=self.mandate_max_discount_pct,
                )
                formatted_final_price = format_inr(final_price_paise)

                eligible_count += 1

                # Render email body using verified facts
                rendered_body = (
                    f"Dear {deal.contact_name},\n\n"
                    f"Following up on our discussions regarding {deal.title}.\n\n"
                    f"We are pleased to offer a {discount_pct}% concession on the implementation fee, "
                    f"bringing the revised setup cost to {formatted_final_price} (standard {formatted_base_price}).\n\n"
                    f"Would you be available for a brief 30-minute sync this week to review the next steps?\n\n"
                    f"Best regards,\n"
                    f"{founder_name}\n"
                    f"Chief of Staff"
                )

                rendered_hash = hashlib.sha256(rendered_body.encode("utf-8")).hexdigest()
                proposal_ref = f"PA-SWEEP-{deal.id}-{now.strftime('%Y%m%d%H%M%S')}"

                facts_used = [
                    {"key": "base_price", "label": "Standard Setup Cost", "value": formatted_base_price, "source": f"crm:{deal.id}"},
                    {"key": "discount_pct", "label": "Discount Concession", "value": f"{discount_pct}%", "source": "mandate:clause_c2"},
                    {"key": "revised_price", "label": "Revised Setup Cost", "value": formatted_final_price, "source": "calculated:offer"},
                ]

                # Policy Verdict
                risk_flags = []
                policy_reasons = []
                if deal.autonomy_mode == "approval_required":
                    verdict: Literal["ALLOW", "ASK", "BLOCK"] = "ASK"
                    status: Literal["pending", "scheduled"] = "pending"
                    policy_reasons.append("Contact autonomy requires explicit founder approval before sending external actions.")
                    risk_flags.append({
                        "code": "G02",
                        "severity": "warning",
                        "reason": "Contact autonomy mode is set to approval_required.",
                    })
                    execute_after = None
                else:
                    verdict = "ALLOW"
                    status = "scheduled"
                    policy_reasons.append(f"Complies with {self.mandate_ref} (<= {self.mandate_max_discount_pct}% concession).")
                    execute_after = (now + timedelta(seconds=15)).isoformat()

                proposal = SweepProposal(
                    ref=proposal_ref,
                    kind="email",
                    deal_id=deal.id,
                    deal_title=deal.title,
                    contact_name=deal.contact_name,
                    contact_email=deal.contact_email,
                    subject=f"Re: {deal.title} Follow-up",
                    rendered_body=rendered_body,
                    rendered_hash=rendered_hash,
                    facts_used=facts_used,
                    risk_flags=risk_flags,
                    policy_verdict=verdict,
                    policy_reasons=policy_reasons,
                    created_at=now.isoformat(),
                    expires_at=(now + timedelta(days=2)).isoformat(),
                    status=status,
                    execute_after=execute_after,
                    undo_window_seconds=15,
                )

                # Store proposal
                self.proposal_store[proposal_ref] = proposal
                proposals_created.append(proposal)

                # Record activity event
                event_type = "scheduled" if verdict == "ALLOW" else "proposed"
                self.activity_store.append({
                    "id": f"evt_sweep_{uuid4().hex[:8]}",
                    "timestamp": now,
                    "type": event_type,
                    "title": f"Quiet sweep: {proposal.deal_title}",
                    "description": f"Drafted follow-up to {proposal.contact_name} ({proposal.policy_verdict}).",
                    "user_id": "sweep_engine",
                    "action_ref": proposal_ref,
                    "rendered_hash": rendered_hash,
                    "execute_after": execute_after,
                    "can_undo": (verdict == "ALLOW"),
                })

            except Exception as e:
                errors.append(f"Error processing deal {deal.id}: {str(e)}")

        return SweepResult(
            timestamp=now,
            total_deals_scanned=scanned_count,
            eligible_deals_count=eligible_count,
            proposals_created=proposals_created,
            skipped=skipped,
            errors=errors,
        )

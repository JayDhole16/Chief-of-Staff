"""
FastAPI Application and Read/Approval/Operations/Chat Endpoints (T08.4, T09, T10.1, T15).

Connects:
- Pure read APIs (/api/activity, /api/receipts, /api/deals, /api/escalations)
- Founder authority endpoints (/api/approvals/pending, /api/approvals/{ref}/decision)
- Action lifecycle & undo (/api/actions/{ref}/cancel)
- Session auth & profile (/api/auth/login, /api/session, /api/profile)
- Settings & Kill Switch (/api/settings, /api/settings/kill-switch)
- Grounded AI Chief of Staff Chat (/api/chat)
- Inbound pipeline injection & quiet sweep dev endpoints (/api/dev/...)
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field

from backend.contracts import CompatBaseModel
from backend.contracts.read_api import (
    ActionReceiptResponse,
    ActivityEventItem,
    ActivityFeedResponse,
    ActivityType,
    DealItem,
    DealStage,
    EscalationItem,
    EscalationSeverity,
    EscalationsResponse,
    PipelineDealsResponse,
    ReceiptFactItem,
    ReceiptStatus,
    ReceiptTimelineItem,
)
from backend.facts.inr_formatter import format_inr
from backend.guards.definitions import list_guards
from backend.services.brief import (
    FounderBriefResponse,
    FounderBriefService,
)
from backend.services.executor import (
    FakeCalendarAdapter,
    FakeGmailAdapter,
    WorkerExecutor,
)
from backend.services.inbound import (
    InboundEmailMessage,
    InboundProcessingPipeline,
)
from backend.services.sweep import (
    QuietSweepService,
    get_demo_sweep_deals,
)
from backend.services.tasks import (
    PostgresTaskRepository,
    SQLiteTaskRepository,
    TaskRepositoryUnavailableError,
    TaskService,
)

# ---------------------------------------------------------------------------
# Request/Response Schemas for Authority, Profile, Chat & Ops
# ---------------------------------------------------------------------------

class LoginRequest(CompatBaseModel):
    email: str
    password: str


class LoginUser(CompatBaseModel):
    id: str
    email: str
    name: str
    role: str = "Founder & CEO"
    business_name: str = "Nair Automation Studio"
    timezone: str = "Asia/Kolkata"


class LoginResponse(CompatBaseModel):
    session_id: str
    user: LoginUser


class SessionResponse(CompatBaseModel):
    session_id: str
    user: LoginUser


class ProfileUpdateRequest(CompatBaseModel):
    name: str | None = None
    role: str | None = None
    business_name: str | None = None
    timezone: str | None = None
    signature: str | None = None
    working_hours: str | None = None
    concise_mode: bool | None = None


class FounderProfileResponse(CompatBaseModel):
    id: str
    name: str
    email: str
    role: str
    business_name: str
    timezone: str
    signature: str
    working_hours: str
    concise_mode: bool
    google_connected: bool
    kill_switch_active: bool


class FactEvidence(CompatBaseModel):
    key: str
    label: str
    value: str
    source: str


class RiskFlagSchema(CompatBaseModel):
    code: str
    severity: Literal["warning", "critical"]
    reason: str
    customer_claim: str | None = None


class ProposedActionSchema(CompatBaseModel):
    ref: str
    kind: Literal["email", "calendar"]
    deal_id: str
    deal_title: str
    contact_name: str
    contact_email: str
    subject: str
    rendered_body: str
    rendered_hash: str
    facts_used: list[FactEvidence] = Field(default_factory=list)
    risk_flags: list[RiskFlagSchema] = Field(default_factory=list)
    policy_verdict: Literal["ALLOW", "ASK", "BLOCK"]
    policy_reasons: list[str] = Field(default_factory=list)
    created_at: str
    expires_at: str
    status: Literal["pending", "approved", "rejected", "expired", "scheduled", "executing", "cancelled"]
    execute_after: str | None = None


class ApprovalItem(CompatBaseModel):
    id: str
    title: str
    description: str
    state: Literal["pending", "approved", "rejected"]
    created_at: str
    expires_at: str
    proposal: ProposedActionSchema


class ApprovalsResponse(CompatBaseModel):
    approvals: list[ApprovalItem]
    count: int


class ApprovalDecisionRequest(CompatBaseModel):
    decision: Literal["approve", "reject"]
    rendered_hash: str
    rejection_reason: str | None = None


class ApprovalDecisionResponse(CompatBaseModel):
    ref: str
    status: Literal["approved", "rejected", "scheduled"]
    rendered_hash: str
    execute_after: str | None = None
    message: str


class CancelActionResponse(CompatBaseModel):
    ref: str
    status: str
    cancelled_at: str
    receipt_id: str
    message: str


class SystemSettingsSchema(CompatBaseModel):
    founder: dict[str, Any]
    google_account: dict[str, Any]
    kill_switch: dict[str, Any]


class KillSwitchRequest(CompatBaseModel):
    active: bool
    reason: str | None = None


class InjectInboundRequest(CompatBaseModel):
    message_id: str
    from_email: str
    to_email: str = "meera@agency.in"
    subject: str
    body: str
    from_name: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class OperationsComponent(CompatBaseModel):
    status: Literal["ready", "degraded", "unavailable", "not_configured"]
    detail: str


class OperationsStatusResponse(CompatBaseModel):
    status: Literal["ready", "degraded"]
    checked_at: datetime
    data_mode: Literal["provisional"]
    kill_switch_active: bool
    components: dict[str, OperationsComponent]


class BriefLink(CompatBaseModel):
    kind: Literal["receipt", "approval", "escalation"]
    reference: str
    href: str


class BriefItem(CompatBaseModel):
    event_id: str
    timestamp: datetime
    title: str
    summary: str
    link: BriefLink


class BriefResponse(CompatBaseModel):
    generated_at: datetime
    items: list[BriefItem]
    omitted_unlinked_events: int
    limitation: str


class ChatMessageRequest(CompatBaseModel):
    message: str
    session_id: str = "s-1"


class ChatMessageResponse(CompatBaseModel):
    id: str
    session_id: str
    role: Literal["assistant"] = "assistant"
    reply: str
    timestamp: str
    intent: str
    facts_cited: list[dict[str, str]] = Field(default_factory=list)
    guards_checked: list[str] = Field(default_factory=list)
    suggested_prompts: list[str] = Field(default_factory=list)
    action_card: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# State Container (In-Memory Database & Services)
# ---------------------------------------------------------------------------

class ApplicationState:
    """Singleton-like in-memory application store for stateful demo & tests."""

    def __init__(self):
        self.reset()

    def reset(self):
        if hasattr(self, "task_repository"):
            try:
                self.task_repository.close()
            except Exception:
                pass
        self.sessions: dict[str, dict[str, Any]] = {
            "test_session_123": {
                "id": "user_meera_01",
                "user_id": "user_meera_01",
                "email": "meera@agency.in",
                "name": "Meera Nair",
                "role": "Founder & CEO",
                "business_name": "Nair Growth Agency",
                "timezone": "Asia/Kolkata",
            }
        }
        self.founder_profile: dict[str, Any] = {
            "id": "user_meera_01",
            "name": "Meera Nair",
            "email": "meera@agency.in",
            "role": "Founder & CEO",
            "business_name": "Nair Growth Agency",
            "timezone": "Asia/Kolkata",
            "signature": "Meera Nair · Chief of Staff",
            "working_hours": "09:30 - 18:30 IST (Mon–Fri)",
            "concise_mode": True,
        }
        self.kill_switch_active: bool = False
        self.kill_switch_reason: str | None = None
        self.google_connected: bool = True
        self.google_email: str = "meera@agency.in"
        self.google_token_status: str = "valid"

        # Initialize pipelines & services
        self.gmail_adapter = FakeGmailAdapter()
        self.calendar_adapter = FakeCalendarAdapter()
        self.receipts: dict[str, ActionReceiptResponse] = {}
        self.activity_events: list[ActivityEventItem] = []
        self.proposals: dict[str, ProposedActionSchema] = {}
        self.escalations: list[EscalationItem] = []

        self.executor = WorkerExecutor(
            gmail_adapter=self.gmail_adapter,
            calendar_adapter=self.calendar_adapter,
            receipt_store=self.receipts,
            activity_store=[],
        )

        database_url = os.getenv("DATABASE_URL")
        self.task_repository = (
            PostgresTaskRepository(database_url)
            if database_url
            else SQLiteTaskRepository()
        )
        self.task_service = TaskService(self.task_repository)
        self.inbound_pipeline = InboundProcessingPipeline(
            task_service_hook=self._create_inbound_task
        )
        self.sweep_service = QuietSweepService()

        # Seed initial Beat 3 proposal (Raju Patel golden path pending approval)
        self._seed_initial_state()

    def _seed_initial_state(self):
        now = datetime.now(timezone.utc)
        body_text = (
            "Dear Raju,\n\n"
            "Thank you for your response regarding our proposal.\n\n"
            "Regarding your query on pricing: we are pleased to confirm a 5% discount on the one-time implementation fee, "
            "bringing the setup cost to ₹4,56,000 (standard ₹4,80,000). For annual ongoing maintenance, our SUP-ANNUAL tier is "
            "₹60,000/year, and our standard cloud connector remains ₹15,000/month.\n\n"
            "I would be delighted to walk you through the architecture this Thursday at 15:00 - 15:30 IST.\n\n"
            "Best regards,\n"
            "Meera Nair\n"
            "Chief of Staff"
        )
        golden_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()

        p = ProposedActionSchema(
            ref="PA-2026-10-15-001",
            kind="email",
            deal_id="D-1",
            deal_title="Acme Warehouse Automation",
            contact_name="Raju Patel",
            contact_email="raju@patel-warehousing.in",
            subject="Re: Automation Project Proposal & Scope",
            rendered_body=body_text,
            rendered_hash=golden_hash,
            facts_used=[
                FactEvidence(key="setup_cost", label="Setup (5% discount applied)", value="₹4,56,000", source="mandate_c2:rate_card"),
                FactEvidence(key="discount_pct", label="Discount", value="5%", source="mandate_c2:max_discount"),
                FactEvidence(key="support_annual", label="Annual Support", value="₹60,000", source="catalog:SUP-ANNUAL"),
                FactEvidence(key="monthly_maintenance", label="Monthly Maintenance", value="₹15,000", source="catalog:CONN-MONTHLY"),
                FactEvidence(key="meeting_slot", label="Proposed Slot", value="15:00 - 15:30 IST", source="calendar:slot_token"),
            ],
            risk_flags=[
                RiskFlagSchema(
                    code="G08",
                    severity="warning",
                    reason="Customer referenced verbal 20% discount on call. Exceeds mandate limit (5%). Requires founder review.",
                    customer_claim="promised 20% on a call",
                ),
            ],
            policy_verdict="ASK",
            policy_reasons=[
                'Customer claim "promised 20% on a call" is unverified',
                "Founder review required before sending counter-offer",
            ],
            created_at=(now - timedelta(minutes=10)).isoformat(),
            expires_at=(now + timedelta(hours=48)).isoformat(),
            status="pending",
        )
        self.proposals[p.ref] = p

        # Seed initial activity feed events
        self.activity_events.append(
            ActivityEventItem(
                id="evt_001",
                timestamp=now - timedelta(minutes=10),
                type=ActivityType.PROPOSED,
                title="Proposed follow-up to Raju Patel",
                description="Counter-offer ₹4,56,000 drafted. Pending founder approval.",
                user_id="agent_cos",
                action_ref="PA-2026-10-15-001",
                rendered_hash=golden_hash,
                can_undo=False,
            )
        )
        self.activity_events.append(
            ActivityEventItem(
                id="evt_002",
                timestamp=now - timedelta(minutes=45),
                type=ActivityType.EXECUTION,
                title="D-1 Follow-up Sent",
                description="Autonomously sent to Acme Warehousing.",
                user_id="worker_executor",
                receipt_id="rcpt_20261015_001",
                can_undo=False,
            )
        )

        # Seed a pre-existing receipt
        rcpt = ActionReceiptResponse(
            receipt_id="rcpt_20261015_001",
            action_ref="act_d1_01",
            action_kind="email",
            status=ReceiptStatus.EXECUTED,
            authority_clause="Mandate M-2026-10-15 Clause C2: Follow-up quiet deals with <=5% discount",
            recipient_email="raju@patel-warehousing.in",
            external_id="gmail_msg_18b93f8e71c29a04",
            rendered_hash=golden_hash,
            checks_passed=["G01", "G04", "G05", "G06", "G07", "G09", "G10", "G11"],
            facts_used=[
                ReceiptFactItem(key="deal_value", label="Deal Value", value="₹12,50,000", source="crm:deal_d1"),
                ReceiptFactItem(key="max_discount", label="Max Discount", value="5%", source="mandate:clause_c2"),
            ],
            executed_at=now - timedelta(minutes=45),
            undo_window_seconds=15,
            timeline=[
                ReceiptTimelineItem(timestamp=now - timedelta(minutes=45, seconds=15), event="Sweep proposed action under mandate"),
                ReceiptTimelineItem(timestamp=now - timedelta(minutes=45), event="Undo window elapsed; worker dispatched"),
                ReceiptTimelineItem(timestamp=now - timedelta(minutes=44, seconds=58), event="Gmail API send confirmed"),
            ],
        )
        self.receipts["rcpt_20261015_001"] = rcpt
        self.receipts["act_d1_01"] = rcpt

    def _create_inbound_task(
        self,
        *,
        contact_id: str | None,
        deal_id: str | None,
        deal_version: int,
        message_id: str,
        classification: Any,
        risk_flags: list[Any],
        verdict: str,
    ) -> str:
        if contact_id is None or deal_id is None:
            raise ValueError("A verified contact and deal are required to create a task")
        task = self.task_service.create_task(
            workspace_id="demo",
            contact_id=contact_id,
            deal_id=deal_id,
            deal_version=deal_version,
            source_message_id=message_id,
            kind=classification.intent.lower(),
            payload={
                "verdict": verdict,
                "risk_flags": [flag.code for flag in risk_flags],
            },
        )
        return task.task_id


# Global in-memory instance
state = ApplicationState()


def _parse_iso_utc(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# FastAPI App Construction
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Chief of Staff - Backend API",
        version="0.1.0",
        description="Founder OS API for sales operations, approvals, receipts, chat, and pipeline.",
    )

    # Enable CORS for Vite frontend (http://localhost:5173)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    @app.get("/api/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        try:
            healthy = state.task_repository.health_check()
        except TaskRepositoryUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Task repository is not ready",
            ) from exc
        if not healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Task repository is not ready",
            )
        return {"status": "ready"}

    # -----------------------------------------------------------------------
    # Helper: Verify Session
    # -----------------------------------------------------------------------
    def get_current_user(x_session_id: str | None = Header(None)) -> dict[str, Any]:
        if not x_session_id or x_session_id not in state.sessions:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Missing or invalid session ID.",
            )
        return state.sessions[x_session_id]

    # -----------------------------------------------------------------------
    # Auth, Session & Profile Endpoints
    # -----------------------------------------------------------------------
    @app.post("/api/auth/login", response_model=LoginResponse)
    def login(req: LoginRequest):
        email = (req.email or "").strip()
        password = req.password or ""
        if not email or not password or "@" not in email:
            raise HTTPException(status_code=422, detail="Valid email and password required")
        if len(password) < 6:
            raise HTTPException(status_code=422, detail="Invalid credentials")

        session_id = f"session_{uuid4().hex[:12]}"
        user_info = {
            "id": f"user_{uuid4().hex[:6]}",
            "email": email,
            "name": email.split("@")[0].title(),
            "role": state.founder_profile.get("role", "Founder & CEO"),
            "business_name": state.founder_profile.get("business_name", "Nair Growth Agency"),
            "timezone": state.founder_profile.get("timezone", "Asia/Kolkata"),
        }
        state.sessions[session_id] = user_info
        return LoginResponse(session_id=session_id, user=LoginUser(**user_info))

    @app.get("/api/session", response_model=SessionResponse)
    def get_session(x_session_id: str | None = Header(None)):
        user = get_current_user(x_session_id)
        user_payload = {
            "id": user.get("id") or user.get("user_id", "user_01"),
            "email": user["email"],
            "name": user["name"],
            "role": user.get("role", "Founder & CEO"),
            "business_name": user.get("business_name", "Nair Growth Agency"),
            "timezone": user.get("timezone", "Asia/Kolkata"),
        }
        return SessionResponse(session_id=x_session_id or "", user=LoginUser(**user_payload))

    @app.get("/api/profile", response_model=FounderProfileResponse)
    def get_profile():
        return FounderProfileResponse(
            **state.founder_profile,
            google_connected=state.google_connected,
            kill_switch_active=state.kill_switch_active,
        )

    @app.put("/api/profile", response_model=FounderProfileResponse)
    def update_profile(req: ProfileUpdateRequest):
        updates = req.model_dump(exclude_none=True)
        for k, v in updates.items():
            if k in state.founder_profile:
                state.founder_profile[k] = v
        for sess in state.sessions.values():
            if "name" in updates:
                sess["name"] = updates["name"]
            if "role" in updates:
                sess["role"] = updates["role"]
            if "business_name" in updates:
                sess["business_name"] = updates["business_name"]
            if "timezone" in updates:
                sess["timezone"] = updates["timezone"]
        return FounderProfileResponse(
            **state.founder_profile,
            google_connected=state.google_connected,
            kill_switch_active=state.kill_switch_active,
        )

    # -----------------------------------------------------------------------
    # Approvals Endpoints (T09.4)
    # -----------------------------------------------------------------------
    @app.get("/api/approvals/pending", response_model=ApprovalsResponse)
    def get_pending_approvals():
        pending_list = [
            ApprovalItem(
                id=p.ref,
                title=f"Review follow-up for {p.contact_name}",
                description=f"{p.deal_title} ({p.policy_verdict})",
                state="pending" if p.status == "pending" else "approved",
                created_at=p.created_at,
                expires_at=p.expires_at,
                proposal=p,
            )
            for p in state.proposals.values()
            if p.status == "pending"
        ]
        return ApprovalsResponse(approvals=pending_list, count=len(pending_list))

    @app.post("/api/approvals/{ref}/decision", response_model=ApprovalDecisionResponse)
    def handle_approval_decision(ref: str, req: ApprovalDecisionRequest):
        proposal = state.proposals.get(ref)
        if not proposal:
            raise HTTPException(status_code=404, detail=f"Proposal {ref} not found")

        if proposal.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Proposal {ref} is no longer pending approval.",
            )

        actual_hash = hashlib.sha256(proposal.rendered_body.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(proposal.rendered_hash, actual_hash):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stored proposal content no longer matches its rendered_hash.",
            )

        # Non-negotiable safety invariant: rendered_hash binding
        if not hmac.compare_digest(proposal.rendered_hash, req.rendered_hash):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Proposal version conflict: the supplied hash does not match the current proposal.",
            )

        if _parse_iso_utc(proposal.expires_at) <= datetime.now(timezone.utc):
            proposal.status = "expired"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Proposal {ref} has expired and cannot be approved."
                ),
            )

        if req.decision == "approve":
            proposal.status = "approved"
            if ref in state.sweep_service.proposal_store:
                state.sweep_service.proposal_store[ref].status = "approved"
            now = datetime.now(timezone.utc)

            # Worker executes approved action and generates terminal receipt
            receipt = state.executor.execute_action(
                action_ref=proposal.ref,
                action_kind=proposal.kind,
                recipient_email=proposal.contact_email,
                rendered_body_or_time=proposal.rendered_body,
                rendered_hash=proposal.rendered_hash,
                authority_clause="Founder Explicit Approval",
                checks_passed=["G01", "G04", "G05", "G06", "G07", "G09", "G10", "G11"],
                facts_used=[f.model_dump() for f in proposal.facts_used],
                is_founder_approved=True,
                email_subject=proposal.subject,
            )
            if receipt.status == ReceiptStatus.BLOCKED:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Approval was recorded but execution failed. Receipt: {receipt.receipt_id}",
                )

            # Record activity event
            state.activity_events.insert(0, ActivityEventItem(
                id=f"evt_{uuid4().hex[:8]}",
                timestamp=now,
                type=ActivityType.APPROVED,
                title=f"Approved action for {proposal.contact_name}",
                description=f"Founder confirmed {proposal.deal_title}. Terminal receipt: {receipt.receipt_id}.",
                user_id="founder",
                action_ref=proposal.ref,
                receipt_id=receipt.receipt_id,
                rendered_hash=proposal.rendered_hash,
                can_undo=False,
            ))

            return ApprovalDecisionResponse(
                ref=proposal.ref,
                status="approved",
                rendered_hash=proposal.rendered_hash,
                message="Action approved and executed by worker",
            )

        elif req.decision == "reject":
            proposal.status = "rejected"
            if ref in state.sweep_service.proposal_store:
                state.sweep_service.proposal_store[ref].status = "rejected"
            now = datetime.now(timezone.utc)
            state.activity_events.insert(0, ActivityEventItem(
                id=f"evt_{uuid4().hex[:8]}",
                timestamp=now,
                type=ActivityType.REJECTED,
                title=f"Rejected action for {proposal.contact_name}",
                description=f"Reason: {req.rejection_reason or 'Rejected by founder'}",
                user_id="founder",
                action_ref=proposal.ref,
                rendered_hash=proposal.rendered_hash,
                can_undo=False,
            ))
            return ApprovalDecisionResponse(
                ref=proposal.ref,
                status="rejected",
                rendered_hash=proposal.rendered_hash,
                message="Action rejected",
            )

    # -----------------------------------------------------------------------
    # Action Lifecycle & Undo
    # -----------------------------------------------------------------------
    @app.post("/api/actions/{ref}/cancel", response_model=CancelActionResponse)
    def cancel_action(ref: str):
        existing_receipt = state.receipts.get(ref)
        if existing_receipt is not None and existing_receipt.status == ReceiptStatus.EXECUTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Action {ref} has already been executed by the worker. Undo window closed.",
            )

        now = datetime.now(timezone.utc)
        receipt_id = f"rcpt_cancel_{uuid4().hex[:6]}"

        cancelled_receipt = ActionReceiptResponse(
            receipt_id=receipt_id,
            action_ref=ref,
            action_kind="email",
            status=ReceiptStatus.CANCELLED,
            authority_clause="Founder Undo Action During Countdown Window",
            rendered_hash="cancelled_hash",
            cancelled_at=now,
            timeline=[
                ReceiptTimelineItem(timestamp=now, event="Action cancelled by user before dispatch"),
            ],
        )

        # Store under both receipt_id and action_ref so WorkerExecutor refuses late execution
        state.receipts[receipt_id] = cancelled_receipt
        state.receipts[ref] = cancelled_receipt

        if ref in state.proposals:
            state.proposals[ref].status = "cancelled"
        if ref in state.sweep_service.proposal_store:
            state.sweep_service.proposal_store[ref].status = "rejected"

        state.activity_events.insert(0, ActivityEventItem(
            id=f"evt_{uuid4().hex[:8]}",
            timestamp=now,
            type=ActivityType.CANCELLED,
            title=f"Action Cancelled: {ref}",
            description="User cancelled action during in-flight undo window.",
            user_id="founder",
            action_ref=ref,
            receipt_id=receipt_id,
        ))

        return CancelActionResponse(
            ref=ref,
            status="cancelled",
            cancelled_at=now.isoformat(),
            receipt_id=receipt_id,
            message="Action successfully cancelled",
        )

    # -----------------------------------------------------------------------
    # Read APIs (T08.4)
    # -----------------------------------------------------------------------
    @app.get("/api/activity", response_model=ActivityFeedResponse)
    def get_activity_feed(cursor: str | None = None, limit: int = Query(default=50, ge=1, le=500)):
        if not isinstance(limit, int):
            limit = 50
        if not isinstance(cursor, str):
            cursor = None
        # Sync activities from inbound & sweep services if any new ones arrived
        valid_types = {m.value for m in ActivityType}
        existing_ids = {e.id for e in state.activity_events}

        for act in state.inbound_pipeline.recorded_activities:
            evt_id = act["id"]
            if evt_id not in existing_ids:
                state.activity_events.insert(0, ActivityEventItem(
                    id=evt_id,
                    timestamp=act["timestamp"],
                    type=ActivityType(act["type"]) if act["type"] in valid_types else ActivityType.EXECUTION,
                    title=act["title"],
                    description=act["description"],
                    user_id=act.get("user_id", "system"),
                    action_ref=act.get("action_ref"),
                    receipt_id=act.get("receipt_id"),
                    escalation_id=act.get("escalation_id"),
                ))
                existing_ids.add(evt_id)

        for act in state.sweep_service.activity_store:
            evt_id = act["id"]
            if evt_id not in existing_ids:
                state.activity_events.insert(0, ActivityEventItem(
                    id=evt_id,
                    timestamp=act["timestamp"],
                    type=ActivityType(act["type"]) if act["type"] in valid_types else ActivityType.SCHEDULED,
                    title=act["title"],
                    description=act["description"],
                    user_id=act.get("user_id", "sweep_engine"),
                    action_ref=act.get("action_ref"),
                    rendered_hash=act.get("rendered_hash"),
                    execute_after=act.get("execute_after"),
                    can_undo=act.get("can_undo", False),
                ))
                existing_ids.add(evt_id)

        for act in state.executor.activities:
            evt_id = act["id"]
            if evt_id not in existing_ids:
                state.activity_events.insert(0, ActivityEventItem(
                    id=evt_id,
                    timestamp=act["timestamp"],
                    type=ActivityType(act["type"]) if act["type"] in valid_types else ActivityType.EXECUTION,
                    title=act["title"],
                    description=act["description"],
                    user_id=act.get("user_id", "worker_executor"),
                    action_ref=act.get("action_ref"),
                    receipt_id=act.get("receipt_id"),
                    rendered_hash=act.get("rendered_hash"),
                    can_undo=act.get("can_undo", False),
                ))
                existing_ids.add(evt_id)

        start_idx = 0
        if cursor:
            for idx, evt in enumerate(state.activity_events):
                if evt.id == cursor:
                    start_idx = idx + 1
                    break

        sliced = state.activity_events[start_idx : start_idx + limit]
        has_more = (start_idx + limit) < len(state.activity_events)
        next_cursor = sliced[-1].id if (has_more and sliced) else None

        return ActivityFeedResponse(
            events=sliced,
            count=len(state.activity_events),
            has_more=has_more,
            next_cursor=next_cursor,
        )

    @app.get("/api/receipts/{ref_or_id}", response_model=ActionReceiptResponse)
    def get_receipt(ref_or_id: str):
        receipt = state.receipts.get(ref_or_id)
        if not receipt:
            raise HTTPException(status_code=404, detail=f"Receipt {ref_or_id} not found")
        return receipt

    @app.get("/api/deals", response_model=PipelineDealsResponse)
    @app.get("/api/pipeline/deals", response_model=PipelineDealsResponse)
    def get_deals():
        deals_list = [
            DealItem(
                id="D-1",
                title="Acme Warehousing Automation",
                contact_name="Raju Patel",
                contact_email="raju@patel-warehousing.in",
                stage=DealStage.NEGOTIATION,
                value_paise=125000000,
                created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
                days_quiet=3,
                is_quiet=True,
            ),
            DealItem(
                id="D-2",
                title="Cloud Connector Architecture",
                contact_name="Sunil Mehta",
                contact_email="sunil@apexlogistics.in",
                stage=DealStage.LEAD,
                value_paise=250000000,
                created_at=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
                days_quiet=1,
                is_quiet=False,
            ),
            DealItem(
                id="D-3",
                title="Inventory Sync",
                contact_name="Priya Shah",
                contact_email="priya@quickship.in",
                stage=DealStage.NEGOTIATION,
                value_paise=180000000,
                created_at=datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc),
                days_quiet=6,
                is_quiet=True,
            ),
            DealItem(
                id="D-4",
                title="Regional Hub Pilot",
                contact_name="Arjun Verma",
                contact_email="arjun@bluedart-franchise.in",
                stage=DealStage.NEGOTIATION,
                value_paise=300000000,
                created_at=datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc),
                days_quiet=5,
                is_quiet=True,
            ),
            DealItem(
                id="D-5",
                title="ExpressCargo Route Automation",
                contact_name="Deepak Roy",
                contact_email="deepak@expresscargo.in",
                stage=DealStage.ACTIVE,
                value_paise=150000000,
                created_at=datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc),
                days_quiet=0,
                is_quiet=False,
            ),
            DealItem(
                id="D-6",
                title="MegaFreight ERP Integration",
                contact_name="Kavita Nair",
                contact_email="kavita@megafreight.in",
                stage=DealStage.WON,
                value_paise=450000000,
                created_at=datetime(2026, 9, 25, 10, 0, tzinfo=timezone.utc),
                days_quiet=0,
                is_quiet=False,
            ),
        ]
        total_paise = sum(d.value_paise for d in deals_list)
        return PipelineDealsResponse(deals=deals_list, count=len(deals_list), total_pipeline_paise=total_paise)

    @app.get("/api/escalations", response_model=EscalationsResponse)
    def get_escalations():
        for esc in state.inbound_pipeline.created_escalations:
            if not any(e.escalation_id == esc["escalation_id"] for e in state.escalations):
                state.escalations.append(EscalationItem(
                    escalation_id=esc["escalation_id"],
                    created_at=esc["created_at"],
                    severity=EscalationSeverity(esc["severity"]),
                    source_message_id=esc["source_message_id"],
                    deal_id=esc["deal_id"],
                    contact_email=esc["contact_email"],
                    reason=esc["reason"],
                    guard_code=esc.get("guard_code"),
                    status="open",
                ))

        return EscalationsResponse(escalations=state.escalations, count=len(state.escalations))

    @app.get("/api/v1/ops/status", response_model=OperationsStatusResponse)
    def get_operations_status():
        try:
            repository_ready = state.task_repository.health_check()
        except TaskRepositoryUnavailableError as exc:
            repository_ready = False
            repository_detail = str(exc)
        else:
            repository_detail = (
                f"{type(state.task_repository).__name__} health check passed"
                if repository_ready
                else f"{type(state.task_repository).__name__} health check failed"
            )

        components = {
            "api": OperationsComponent(status="ready", detail="API process is serving requests"),
            "task_repository": OperationsComponent(
                status="ready" if repository_ready else "unavailable",
                detail=repository_detail,
            ),
            "worker": OperationsComponent(
                status="degraded",
                detail="Health-only placeholder; no background jobs are executed",
            ),
            "google": OperationsComponent(
                status="not_configured",
                detail="Fake Gmail and Calendar adapters are active; no live Google connection",
            ),
            "agent_runtime": OperationsComponent(
                status="not_configured",
                detail="No live agent or DirectRunner is configured",
            ),
            "benchmarks": OperationsComponent(
                status="not_configured",
                detail="No benchmark run is recorded",
            ),
            "deployment": OperationsComponent(
                status="not_configured",
                detail="No approved demo deployment target is configured",
            ),
        }
        overall_status = (
            "ready"
            if repository_ready
            and all(component.status == "ready" for component in components.values())
            else "degraded"
        )
        return OperationsStatusResponse(
            status=overall_status,
            checked_at=datetime.now(timezone.utc),
            data_mode="provisional",
            kill_switch_active=state.kill_switch_active,
            components=components,
        )

    @app.get("/api/v1/brief", response_model=BriefResponse)
    def get_brief():
        events = get_activity_feed().events
        escalations = get_escalations().escalations
        escalation_ids = {item.escalation_id for item in escalations}
        brief_items: list[BriefItem] = []
        omitted_unlinked = 0

        for event in events:
            link: BriefLink | None = None
            if event.receipt_id and event.receipt_id in state.receipts:
                link = BriefLink(
                    kind="receipt",
                    reference=event.receipt_id,
                    href=f"/api/receipts/{event.receipt_id}",
                )
            elif event.action_ref and event.action_ref in state.proposals:
                link = BriefLink(
                    kind="approval",
                    reference=event.action_ref,
                    href="/api/approvals/pending",
                )
            elif event.escalation_id and event.escalation_id in escalation_ids:
                link = BriefLink(
                    kind="escalation",
                    reference=event.escalation_id,
                    href="/api/escalations",
                )

            if link is None:
                omitted_unlinked += 1
                continue

            brief_items.append(
                BriefItem(
                    event_id=event.id,
                    timestamp=event.timestamp,
                    title=event.title,
                    summary=event.description,
                    link=link,
                )
            )

        return BriefResponse(
            generated_at=datetime.now(timezone.utc),
            items=brief_items,
            omitted_unlinked_events=omitted_unlinked,
            limitation=(
                "Provisional local state; activity may be incomplete and is not a live "
                "operational record."
            ),
        )

    @app.get("/api/brief", response_model=FounderBriefResponse)
    def get_founder_brief(x_workspace_id: str = Header(default="WS-DEMO")):
        get_escalations()
        get_activity_feed()

        if x_workspace_id != "WS-DEMO":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized access to workspace 'WS-DEMO' from '{x_workspace_id}'",
            )

        deals_response = get_deals()
        brief_service = FounderBriefService(workspace_id="WS-DEMO")
        proposals_list = [p.model_dump() for p in state.proposals.values()]
        receipts_list = list(state.receipts.values())

        try:
            brief = brief_service.generate_brief(
                receipts=receipts_list,
                proposals=proposals_list,
                deals=deals_response.deals,
                escalations=state.escalations,
                activity_events=state.activity_events,
                requesting_workspace_id=x_workspace_id,
            )
            return brief
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # -----------------------------------------------------------------------
    # Grounded AI Chief of Staff Chat Endpoint
    # -----------------------------------------------------------------------
    @app.post("/api/chat", response_model=ChatMessageResponse)
    def handle_chat(req: ChatMessageRequest):
        text = (req.message or "").strip()
        if not text:
            raise HTTPException(status_code=422, detail="Message cannot be empty")

        now_iso = datetime.now(timezone.utc).isoformat()
        p = text.lower()
        deals_resp = get_deals()
        pending_props = [pr for pr in state.proposals.values() if pr.status == "pending"]
        unique_receipts = list({r.receipt_id: r for r in state.receipts.values()}.values())
        executed_receipts = [r for r in unique_receipts if r.status == ReceiptStatus.EXECUTED]
        guards_map = list_guards()

        if any(k in p for k in ("brief", "standup", "morning", "summary")):
            brief = get_founder_brief(x_workspace_id="WS-DEMO")
            return ChatMessageResponse(
                id=f"chat_{uuid4().hex[:8]}",
                session_id=req.session_id,
                reply=(
                    f"**Founder Standup Summary ({brief.workspace_id})**\n"
                    f"• **Headline:** {brief.headline}\n"
                    f"• **Executed Actions:** {brief.metrics.actions_executed_count} (verified terminal receipts)\n"
                    f"• **Pending Approvals:** {brief.metrics.pending_approvals_count}\n"
                    f"• **Pipeline Total:** {format_inr(brief.metrics.total_pipeline_value_paise)}\n"
                    f"• **Time Saved:** ~{brief.metrics.estimated_founder_minutes_saved} mins\n\n"
                    f"_{brief.narration_text}_"
                ),
                timestamp=now_iso,
                intent="FOUNDER_BRIEF",
                facts_cited=[
                    {"label": "Pipeline Total", "value": format_inr(brief.metrics.total_pipeline_value_paise), "source": "crm:pipeline"},
                    {"label": "Executed Receipts", "value": str(brief.metrics.actions_executed_count), "source": "audit:receipts"},
                ],
                guards_checked=["G01", "G06", "G07", "G09"],
                suggested_prompts=[
                    "Show pending approvals",
                    "Run quiet pipeline sweep",
                    "Inspect latest execution receipt",
                ],
            )

        if any(k in p for k in ("sweep", "quiet", "follow-up", "followup")):
            quiet_deals = [d for d in deals_resp.deals if d.is_quiet]
            quiet_summary = "\n".join(
                f"• **{d.id} ({d.title})** — {d.contact_name} · Quiet {d.days_quiet}d · {format_inr(d.value_paise)}"
                for d in quiet_deals
            )
            return ChatMessageResponse(
                id=f"chat_{uuid4().hex[:8]}",
                session_id=req.session_id,
                reply=(
                    f"I scanned all **{deals_resp.count} deals** against Mandate M-2026-10-15 Clause C2 (quiet threshold ≥ 3 days, max 5% discount):\n\n"
                    f"{quiet_summary}\n\n"
                    "Note: Priya Shah (D-3) has an active OOO auto-reply until 20 Oct 2026 and is automatically snoozed."
                ),
                timestamp=now_iso,
                intent="QUIET_SWEEP_ANALYSIS",
                facts_cited=[
                    {"label": "Quiet Deals", "value": str(len(quiet_deals)), "source": "sweep:detector"},
                    {"label": "Mandate Cap", "value": "5%", "source": "mandate:clause_c2"},
                ],
                guards_checked=["G01", "G04", "G05", "G10", "G12"],
                suggested_prompts=[
                    "Review Raju Malhotra's 20% discount request",
                    "Check Deal D-4 Arjun Verma status",
                    "Generate Founder Morning Brief",
                ],
            )

        if any(k in p for k in ("raju", "d-1", "discount", "20%", "counter")):
            raju_prop = state.proposals.get("PA-2026-10-15-001")
            status_label = raju_prop.status if raju_prop else "pending"
            return ChatMessageResponse(
                id=f"chat_{uuid4().hex[:8]}",
                session_id=req.session_id,
                reply=(
                    "**Deal D-1 (Raju Malhotra / Warehouse Automation) Guardrail Analysis:**\n"
                    "1. **Guard G08 (Unverified Claim):** Customer claimed a verbal `20% discount` on a call — not present in `TrustedFacts`.\n"
                    "2. **Guard G10 (Mandate Ceiling):** 20% exceeds the autonomous mandate cap of `5%`.\n"
                    "3. **Grounded Counter-Offer (`PA-2026-10-15-001`):** Server-rendered at **₹4,56,000** (5% off ₹4,80,000 base) + **₹60,000/yr** annual support (`SUP-ANNUAL`), proposing slot **Thu 15:00–15:30 IST**.\n"
                    f"4. **Current Status:** `{status_label.upper()}` (SHA-256 hash-bound)."
                ),
                timestamp=now_iso,
                intent="DEAL_D1_REVIEW",
                facts_cited=[
                    {"label": "Counter-Offer", "value": "₹4,56,000", "source": "mandate_c2:rate_card"},
                    {"label": "Annual Support", "value": "₹60,000/yr", "source": "catalog:SUP-ANNUAL"},
                    {"label": "Slot", "value": "15:00 - 15:30 IST", "source": "calendar:slot_token"},
                ],
                guards_checked=["G01", "G04", "G06", "G07", "G08", "G09", "G10", "G11"],
                suggested_prompts=[
                    "Show all 6 pipeline deals",
                    "Inspect terminal receipts",
                    "Explain deterministic guards G01-G15",
                ],
            )

        if any(k in p for k in ("guard", "g0", "g1", "policy", "safety", "security")):
            guard_lines = "\n".join(f"• **{gid}:** {desc}" for gid, desc in list(guards_map.items())[:8])
            return ChatMessageResponse(
                id=f"chat_{uuid4().hex[:8]}",
                session_id=req.session_id,
                reply=(
                    "**Deterministic Guard Registry (G01–G15):**\n"
                    "Every outbound proposal is evaluated by pure functions (`ALLOW` / `ASK` / `BLOCK`). Blocking guards can never be overridden:\n\n"
                    f"{guard_lines}\n"
                    "• **G09–G15:** INR currency lock, mandate discount ceiling (5%), floor price check, opt-out enforcement, business hours, PII filter, and grammar check."
                ),
                timestamp=now_iso,
                intent="GUARD_EXPLANATION",
                facts_cited=[
                    {"label": "Total Guards", "value": "15 (G01-G15)", "source": "policy:engine"},
                    {"label": "Kill Switch", "value": "ACTIVE" if state.kill_switch_active else "STANDBY", "source": "ops:kill_switch"},
                ],
                guards_checked=list(guards_map.keys()),
                suggested_prompts=[
                    "Check operations status",
                    "Show pending approvals",
                    "Summarize Q4 revenue target",
                ],
            )

        if any(k in p for k in ("deal", "pipeline", "revenue", "target", "q4")):
            deal_lines = "\n".join(
                f"• **{d.id} · {d.title}** ({d.contact_name}) — `{d.stage.value.upper()}` · **{format_inr(d.value_paise)}**"
                for d in deals_resp.deals
            )
            return ChatMessageResponse(
                id=f"chat_{uuid4().hex[:8]}",
                session_id=req.session_id,
                reply=(
                    f"**Executive Pipeline Overview ({deals_resp.count} Deals · Total {format_inr(deals_resp.total_pipeline_paise)}):**\n"
                    f"• **Q4 Revenue Progress:** ₹18,80,000 / ₹35,00,000 (**53.7%**)\n\n"
                    f"{deal_lines}"
                ),
                timestamp=now_iso,
                intent="PIPELINE_OVERVIEW",
                facts_cited=[
                    {"label": "Total Pipeline", "value": format_inr(deals_resp.total_pipeline_paise), "source": "crm:deals"},
                    {"label": "Active Deals", "value": str(deals_resp.count), "source": "crm:deals"},
                ],
                guards_checked=["G01", "G05", "G09"],
                suggested_prompts=[
                    "Run quiet pipeline sweep",
                    "Review Raju Malhotra's 20% discount request",
                    "Generate Founder Morning Brief",
                ],
            )

        return ChatMessageResponse(
            id=f"chat_{uuid4().hex[:8]}",
            session_id=req.session_id,
            reply=(
                f"I've evaluated **\"{text}\"** against your live workspace (`WS-DEMO`).\n\n"
                f"• **Pipeline:** {deals_resp.count} deals totaling **{format_inr(deals_resp.total_pipeline_paise)}**\n"
                f"• **Pending Founder Decisions:** {len(pending_props)} proposal(s)\n"
                f"• **Verified Receipts:** {len(executed_receipts)} executed action(s)\n"
                f"• **Autonomy Mode:** {'PAUSED (Kill Switch Engaged)' if state.kill_switch_active else 'Auto-pilot Active (Mandate M-2026-10-15)'}"
            ),
            timestamp=now_iso,
            intent="GENERAL_ASSISTANCE",
            facts_cited=[
                {"label": "Pending Approvals", "value": str(len(pending_props)), "source": "authority:approvals"},
                {"label": "Executed Actions", "value": str(len(executed_receipts)), "source": "audit:receipts"},
            ],
            guards_checked=["G01", "G04", "G05", "G06", "G07"],
            suggested_prompts=[
                "Summarize Q4 revenue target & deals",
                "Review Raju Malhotra's 20% discount request",
                "Generate Founder Morning Brief",
            ],
        )

    # -----------------------------------------------------------------------
    # Settings & Kill Switch (T09.5)
    # -----------------------------------------------------------------------
    @app.get("/api/settings", response_model=SystemSettingsSchema)
    def get_settings():
        return SystemSettingsSchema(
            founder={
                "name": state.founder_profile.get("name", "Meera Nair"),
                "email": state.founder_profile.get("email", "meera@agency.in"),
                "business_name": state.founder_profile.get("business_name", "Nair Growth Agency"),
                "timezone": state.founder_profile.get("timezone", "Asia/Kolkata"),
            },
            google_account={
                "connected": state.google_connected,
                "email": state.google_email,
                "token_status": state.google_token_status,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "scopes": ["gmail.modify", "calendar"],
            },
            kill_switch={
                "active": state.kill_switch_active,
                "triggered_at": datetime.now(timezone.utc).isoformat() if state.kill_switch_active else None,
                "reason": state.kill_switch_reason,
            },
        )

    @app.post("/api/settings/kill-switch")
    def toggle_kill_switch(req: KillSwitchRequest):
        state.kill_switch_active = req.active
        state.kill_switch_reason = req.reason or ("Manually toggled" if req.active else None)
        state.executor.kill_switch_active = req.active
        return {
            "status": "ok",
            "active": state.kill_switch_active,
            "kill_switch_active": state.kill_switch_active,
            "message": (
                "Emergency kill switch active. All mandate sweeps halted."
                if state.kill_switch_active
                else "Kill switch released. Autonomous sweeps normal."
            ),
        }

    # -----------------------------------------------------------------------
    # Dev / Test Integration Endpoints
    # -----------------------------------------------------------------------
    @app.post("/api/dev/inject-inbound")
    def inject_inbound(req: InjectInboundRequest):
        msg = InboundEmailMessage(
            message_id=req.message_id,
            from_email=req.from_email,
            to_email=req.to_email,
            subject=req.subject,
            body=req.body,
            from_name=req.from_name,
            headers=req.headers,
        )
        result = state.inbound_pipeline.process(msg)
        return {
            "status": result.status,
            "verdict": result.verdict,
            "intent": result.classification.intent,
            "action_type": result.classification.action_type,
            "guards_triggered": result.guards_triggered,
            "task_id": result.task_id,
            "escalation_id": result.escalation_id,
        }

    @app.post("/api/dev/run-sweep")
    def run_sweep():
        deals = get_demo_sweep_deals()
        for d in deals:
            if d.contact_id in state.inbound_pipeline.opted_out_contacts:
                d.do_not_contact = True
            if d.contact_id in state.inbound_pipeline.snoozed_contacts:
                d.snooze_until = state.inbound_pipeline.snoozed_contacts[d.contact_id]

        res = state.sweep_service.sweep(deals)
        for p in res.proposals_created:
            schema = ProposedActionSchema(
                ref=p.ref,
                kind=p.kind,
                deal_id=p.deal_id,
                deal_title=p.deal_title,
                contact_name=p.contact_name,
                contact_email=p.contact_email,
                subject=p.subject,
                rendered_body=p.rendered_body,
                rendered_hash=p.rendered_hash,
                facts_used=[FactEvidence(**f) for f in p.facts_used],
                risk_flags=[RiskFlagSchema(**f) for f in p.risk_flags],
                policy_verdict=p.policy_verdict,
                policy_reasons=p.policy_reasons,
                created_at=p.created_at,
                expires_at=p.expires_at,
                status=p.status,
                execute_after=p.execute_after,
            )
            state.proposals[p.ref] = schema
        return {
            "scanned": res.total_deals_scanned,
            "eligible": res.eligible_deals_count,
            "proposals_created": len(res.proposals_created),
            "skipped": res.skipped,
        }

    @app.post("/api/dev/reset-demo")
    def reset_demo():
        state.reset()
        return {"status": "reset_complete"}

    return app


app = create_app()

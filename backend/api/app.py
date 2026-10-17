"""
FastAPI Application and Read/Approval/Operations Endpoints (T08.4, T09, T10.1).

Connects:
- Pure read APIs (/api/activity, /api/receipts, /api/deals, /api/escalations)
- Founder authority endpoints (/api/approvals/pending, /api/approvals/{ref}/decision)
- Action lifecycle & undo (/api/actions/{ref}/cancel)
- Session auth (/api/auth/login, /api/session)
- Settings & Kill Switch (/api/settings, /api/settings/kill-switch)
- Inbound pipeline injection & quiet sweep dev endpoints (/api/dev/...)
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
# Request/Response Schemas for Authority & Ops
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginUser(BaseModel):
    id: str
    email: str
    name: str


class LoginResponse(BaseModel):
    session_id: str
    user: LoginUser


class SessionResponse(BaseModel):
    session_id: str
    user: LoginUser


class FactEvidence(BaseModel):
    key: str
    label: str
    value: str
    source: str


class RiskFlagSchema(BaseModel):
    code: str
    severity: Literal["warning", "critical"]
    reason: str
    customer_claim: str | None = None


class ProposedActionSchema(BaseModel):
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
    status: Literal["pending", "approved", "rejected", "expired", "scheduled", "executing"]
    execute_after: str | None = None


class ApprovalItem(BaseModel):
    id: str
    title: str
    description: str
    state: Literal["pending", "approved", "rejected"]
    created_at: str
    expires_at: str
    proposal: ProposedActionSchema


class ApprovalsResponse(BaseModel):
    approvals: list[ApprovalItem]
    count: int


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    rendered_hash: str
    rejection_reason: str | None = None


class ApprovalDecisionResponse(BaseModel):
    ref: str
    status: Literal["approved", "rejected", "scheduled"]
    rendered_hash: str
    execute_after: str | None = None
    message: str


class CancelActionResponse(BaseModel):
    ref: str
    status: str
    cancelled_at: str
    receipt_id: str
    message: str


class SystemSettingsSchema(BaseModel):
    founder: dict[str, str]
    google_account: dict[str, Any]
    kill_switch: dict[str, Any]


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str | None = None


class InjectInboundRequest(BaseModel):
    message_id: str
    from_email: str
    to_email: str = "meera@agency.in"
    subject: str
    body: str
    from_name: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class OperationsComponent(BaseModel):
    status: Literal["ready", "degraded", "unavailable", "not_configured"]
    detail: str


class OperationsStatusResponse(BaseModel):
    status: Literal["ready", "degraded"]
    checked_at: datetime
    data_mode: Literal["provisional"]
    kill_switch_active: bool
    components: dict[str, OperationsComponent]


class BriefLink(BaseModel):
    kind: Literal["receipt", "approval", "escalation"]
    reference: str
    href: str


class BriefItem(BaseModel):
    event_id: str
    timestamp: datetime
    title: str
    summary: str
    link: BriefLink


class BriefResponse(BaseModel):
    generated_at: datetime
    items: list[BriefItem]
    omitted_unlinked_events: int
    limitation: str


# ---------------------------------------------------------------------------
# State Container (In-Memory Database & Services)
# ---------------------------------------------------------------------------

class ApplicationState:
    """Singleton-like in-memory application store for stateful demo & tests."""

    def __init__(self):
        self.reset()

    def reset(self):
        if hasattr(self, "task_repository"):
            self.task_repository.close()
        self.sessions: dict[str, dict[str, Any]] = {
            "test_session_123": {
                "user_id": "user_meera_01",
                "email": "meera@agency.in",
                "name": "Meera Nair",
            }
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


# ---------------------------------------------------------------------------
# FastAPI App Construction
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Chief of Staff - Backend API",
        version="0.1.0",
        description="Founder OS API for sales operations, approvals, receipts, and pipeline.",
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
    # Auth & Session Endpoints
    # -----------------------------------------------------------------------
    @app.post("/api/auth/login", response_model=LoginResponse)
    def login(req: LoginRequest):
        if not req.email or not req.password:
            raise HTTPException(status_code=422, detail="Email and password required")
        if len(req.password) < 6:
            raise HTTPException(status_code=422, detail="Invalid credentials")

        session_id = f"session_{uuid4().hex[:12]}"
        user_info = {
            "id": f"user_{uuid4().hex[:6]}",
            "email": req.email,
            "name": req.email.split("@")[0].title(),
        }
        state.sessions[session_id] = user_info
        return LoginResponse(session_id=session_id, user=LoginUser(**user_info))

    @app.get("/api/session", response_model=SessionResponse)
    def get_session(x_session_id: str | None = Header(None)):
        user = get_current_user(x_session_id)
        return SessionResponse(session_id=x_session_id, user=LoginUser(**user))

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

        if datetime.fromisoformat(proposal.expires_at) <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Proposal {ref} has expired and cannot be approved."
                ),
            )

        if req.decision == "approve":
            proposal.status = "approved"
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
        now = datetime.now(timezone.utc)
        receipt_id = f"rcpt_cancel_{uuid4().hex[:6]}"

        # Record cancelled receipt
        state.receipts[receipt_id] = ActionReceiptResponse(
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
    def get_activity_feed(cursor: str | None = None, limit: int = 50):
        # Sync activities from inbound & sweep services if any new ones arrived
        for act in state.inbound_pipeline.recorded_activities:
            evt_id = act["id"]
            if not any(e.id == evt_id for e in state.activity_events):
                state.activity_events.insert(0, ActivityEventItem(
                    id=evt_id,
                    timestamp=act["timestamp"],
                    type=ActivityType(act["type"]) if act["type"] in ActivityType.__members__.values() else ActivityType.EXECUTION,
                    title=act["title"],
                    description=act["description"],
                    user_id=act.get("user_id", "system"),
                    action_ref=act.get("action_ref"),
                    receipt_id=act.get("receipt_id"),
                    escalation_id=act.get("escalation_id"),
                ))

        for act in state.sweep_service.activity_store:
            evt_id = act["id"]
            if not any(e.id == evt_id for e in state.activity_events):
                state.activity_events.insert(0, ActivityEventItem(
                    id=evt_id,
                    timestamp=act["timestamp"],
                    type=ActivityType(act["type"]) if act["type"] in ActivityType.__members__.values() else ActivityType.SCHEDULED,
                    title=act["title"],
                    description=act["description"],
                    user_id=act.get("user_id", "sweep_engine"),
                    action_ref=act.get("action_ref"),
                    rendered_hash=act.get("rendered_hash"),
                    execute_after=act.get("execute_after"),
                    can_undo=act.get("can_undo", False),
                ))

        for act in state.executor.activities:
            evt_id = act["id"]
            if not any(e.id == evt_id for e in state.activity_events):
                state.activity_events.insert(0, ActivityEventItem(
                    id=evt_id,
                    timestamp=act["timestamp"],
                    type=ActivityType(act["type"]) if act["type"] in ActivityType.__members__.values() else ActivityType.EXECUTION,
                    title=act["title"],
                    description=act["description"],
                    user_id=act.get("user_id", "worker_executor"),
                    action_ref=act.get("action_ref"),
                    receipt_id=act.get("receipt_id"),
                    rendered_hash=act.get("rendered_hash"),
                    can_undo=act.get("can_undo", False),
                ))

        return ActivityFeedResponse(
            events=state.activity_events[:limit],
            count=len(state.activity_events),
            has_more=len(state.activity_events) > limit,
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
        # Sync escalations from inbound pipeline
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
        # Sync escalations from inbound pipeline
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
    # Settings & Kill Switch (T09.5)
    # -----------------------------------------------------------------------
    @app.get("/api/settings", response_model=SystemSettingsSchema)
    def get_settings():
        return SystemSettingsSchema(
            founder={
                "name": "Meera Nair",
                "email": "meera@agency.in",
                "business_name": "Nair Growth Agency",
                "timezone": "Asia/Kolkata",
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
        return {"status": "ok", "kill_switch_active": state.kill_switch_active}

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
        res = state.sweep_service.sweep(deals)
        # Register new proposals in state.proposals
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

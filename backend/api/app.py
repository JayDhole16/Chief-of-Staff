"""
Chief-of-Staff HTTP API.

Every route except auth and health requires a session (``X-Session-ID`` header or
``Authorization: Bearer``) and only ever reads or writes the caller's own data.

- Auth:        /api/auth/register, /api/auth/login, /api/auth/logout, /api/session
- Profile:     /api/profile
- Deals:       /api/deals (CRUD), /api/deals/{id}/draft-followup, /api/sweep
- Approvals:   /api/approvals, /api/approvals/{ref} (edit), /api/approvals/{ref}/decision
- Records:     /api/receipts, /api/activity, /api/brief
- Chat:        /api/chat, /api/chat/sessions
- Settings:    /api/settings/api-keys, /api/settings/email, /api/settings/usage,
               /api/settings/kill-switch
- Operations:  /healthz, /readyz, /api/v1/ops/status
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.facts.inr_formatter import format_inr
from backend.guards.definitions import list_guards
from backend.policy.engine import PolicyInput, evaluate_policy
from backend.services import llm, mailer
from backend.services.app_store import (
    AppStore,
    EmailAlreadyRegisteredError,
    iso,
    parse_iso,
    utcnow,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DealStage = Literal["lead", "qualified", "proposal_sent", "negotiating", "won", "lost"]
OPEN_STAGES = {"lead", "qualified", "proposal_sent", "negotiating"}


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=256)
    business_name: str = Field(default="", max_length=160)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    business_name: str | None = Field(default=None, max_length=160)
    timezone: str | None = Field(default=None, max_length=64)
    signature: str | None = Field(default=None, max_length=500)
    working_hours: str | None = Field(default=None, max_length=120)
    max_discount_pct: int | None = Field(default=None, ge=0, le=100)
    quiet_days_threshold: int | None = Field(default=None, ge=1, le=90)


class DealCreate(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    contact_name: str = Field(min_length=1, max_length=120)
    contact_email: str = Field(default="", max_length=254)
    stage: DealStage = "lead"
    value_inr: int = Field(default=0, ge=0)
    notes: str = Field(default="", max_length=4000)
    do_not_contact: bool = False
    last_contact_at: str | None = None


class DealUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=160)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, min_length=1, max_length=120)
    contact_email: str | None = Field(default=None, max_length=254)
    stage: DealStage | None = None
    value_inr: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=4000)
    do_not_contact: bool | None = None
    last_contact_at: str | None = None


class DraftRequest(BaseModel):
    instructions: str = Field(default="", max_length=2000)


class ProposalEdit(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    rendered_hash: str
    rejection_reason: str | None = Field(default=None, max_length=500)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None


class RenameChatRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class ApiKeyUpdate(BaseModel):
    api_key: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    base_url: str | None = Field(default=None, max_length=500)
    make_active: bool = True


class ActiveProviderRequest(BaseModel):
    provider: str | None


class EmailSettingsUpdate(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    username: str = Field(min_length=1, max_length=255)
    password: str | None = Field(default=None, max_length=500)
    from_email: str = Field(max_length=254)
    use_ssl: bool = False


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def default_database() -> str:
    """``DATABASE_URL`` (PostgreSQL) when set, otherwise a SQLite file at ``APP_DB_PATH``."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url
    env_path = os.getenv("APP_DB_PATH", "").strip()
    if env_path:
        return env_path
    return str(Path(__file__).resolve().parents[2] / "data" / "app.db")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sanitize_deal_payload(data: dict[str, Any]) -> dict[str, Any]:
    if "contact_email" in data and data["contact_email"]:
        email = data["contact_email"].strip().lower()
        if not EMAIL_RE.match(email):
            raise HTTPException(status_code=422, detail="Contact email is not a valid address")
        data["contact_email"] = email
    if data.get("last_contact_at"):
        try:
            data["last_contact_at"] = iso(parse_iso(data["last_contact_at"]))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="last_contact_at must be an ISO date") from exc
    for key in ("company", "title", "contact_name", "notes"):
        if isinstance(data.get(key), str):
            data[key] = data[key].strip()
    return data


_MONEY_RE = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)
_DISCOUNT_RE = re.compile(r"(\d{1,3})\s*%\s*(?:off|discount)", re.IGNORECASE)
_FOREIGN_CURRENCY_RE = re.compile(r"(\$|€|£|\busd\b|\beur\b|\bgbp\b)", re.IGNORECASE)
_SENSITIVE_RE = re.compile(
    r"\b(?:\d[ -]?){13,16}\b"  # card-like numbers
    r"|\b\d{4}\s?\d{4}\s?\d{4}\b"  # Aadhaar-like
    r"|\b[A-Z]{5}\d{4}[A-Z]\b"  # PAN
    r"|password\s*[:=]",
    re.IGNORECASE,
)


def run_guards(*, user: dict[str, Any], deal: dict[str, Any], subject: str, body: str) -> dict[str, Any]:
    """Run the deterministic G01–G15 policy over a drafted email."""
    text = f"{subject}\n{body}"
    amounts = []
    for raw in _MONEY_RE.findall(text):
        try:
            amounts.append(int(float(raw.replace(",", ""))))
        except ValueError:
            continue
    known_amounts = {int(deal.get("value_inr") or 0)}
    draft_grounded = all(a in known_amounts for a in amounts)
    discounts = [int(d) for d in _DISCOUNT_RE.findall(text)]
    discount_pct = min(max(discounts, default=0), 100)
    decision = evaluate_policy(
        PolicyInput(
            session_valid=True,
            permission_granted=True,
            amount_paise=0,
            daily_limit_paise=0,
            contact_verified=bool(EMAIL_RE.match(deal.get("contact_email") or "")),
            task_scope_matches=True,
            required_facts_present=bool(deal.get("contact_name") and deal.get("contact_email")),
            draft_grounded=draft_grounded,
            unverified_commitment=False,
            currency="USD" if _FOREIGN_CURRENCY_RE.search(text) else "INR",
            discount_pct=discount_pct,
            mandate_max_discount_pct=int(user.get("max_discount_pct") or 0),
            price_paise=0,
            floor_price_paise=0,
            opted_out=bool(deal.get("do_not_contact")),
            within_business_window=True,
            contains_sensitive_data=bool(_SENSITIVE_RE.search(text)),
            grammar_ok=len(body.strip()) >= 20,
        )
    )
    reasons = list(decision.reasons)
    if amounts and not draft_grounded:
        reasons.append(
            "Amounts in the draft do not match the deal value on record: "
            + ", ".join(format_inr(a * 100) for a in amounts)
        )
    return {
        "verdict": decision.verdict,
        "reasons": reasons,
        "guards_triggered": list(decision.guards_triggered),
        "guards_checked": sorted(list_guards().keys()),
    }


def parse_draft(text: str, fallback_subject: str) -> tuple[str, str]:
    """Split an LLM draft of the form ``SUBJECT: ...`` + body."""
    cleaned = text.strip().strip("`").strip()
    subject = fallback_subject
    lines = cleaned.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip() or fallback_subject
        lines = lines[1:]
    body = "\n".join(lines).strip()
    if body.lower().startswith("body:"):
        body = body[5:].strip()
    return subject[:300], body


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app(database: str | None = None) -> FastAPI:
    store = AppStore(database or default_database())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        store.close()

    app = FastAPI(
        lifespan=lifespan,
        title="Chief of Staff API",
        version="1.0.0",
        description="Founder operating system: deals, approvals, receipts, grounded chat, BYOK LLM keys.",
    )
    app.state.store = store

    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------- auth deps
    def session_token(
        x_session_id: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> str:
        token = x_session_id
        if not token and authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        if not token:
            raise HTTPException(status_code=401, detail="Not signed in")
        return token

    def current_user(token: str = Depends(session_token)) -> dict[str, Any]:
        user = store.user_for_session(token)
        if user is None:
            raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
        return user

    def llm_config_for(user: dict[str, Any]) -> llm.LLMConfig:
        provider = user.get("active_llm_provider")
        if not provider:
            raise HTTPException(
                status_code=409,
                detail="No AI provider configured. Add your API key in Settings → API Keys.",
            )
        try:
            return llm.resolve_config(provider, store.get_api_key(user["id"], provider))
        except llm.LLMNotConfiguredError as exc:
            raise HTTPException(status_code=409, detail=f"{exc}. Update it in Settings → API Keys.") from exc

    def call_llm(
        user: dict[str, Any],
        *,
        purpose: str,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4000,
    ) -> llm.LLMResult:
        config = llm_config_for(user)
        try:
            result = llm.complete(config, system=system, messages=messages, max_tokens=max_tokens)
        except llm.LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        store.record_usage(
            user["id"],
            provider=result.provider,
            model=result.model,
            purpose=purpose,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        return result

    def auth_response(user: dict[str, Any]) -> dict[str, Any]:
        return {"session_id": store.create_session(user["id"]), "user": user}

    # ---------------------------------------------------------------- health
    @app.get("/healthz")
    @app.get("/api/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        if not store.health_check():
            raise HTTPException(status_code=503, detail="Database is not ready")
        return {"status": "ready"}

    # ---------------------------------------------------------------- auth
    @app.post("/api/auth/register", status_code=201)
    def register(req: RegisterRequest) -> dict[str, Any]:
        email = req.email.strip().lower()
        if not EMAIL_RE.match(email):
            raise HTTPException(status_code=422, detail="Enter a valid email address")
        if not req.name.strip():
            raise HTTPException(status_code=422, detail="Enter your name")
        try:
            user = store.create_user(
                name=req.name, email=email, password=req.password, business_name=req.business_name
            )
        except EmailAlreadyRegisteredError as exc:
            raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
        store.add_activity(user["id"], type="account", title="Account created", description=f"Welcome, {user['name']}.")
        return auth_response(user)

    @app.post("/api/auth/login")
    def login(req: LoginRequest) -> dict[str, Any]:
        user = store.authenticate(req.email, req.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return auth_response(user)

    @app.post("/api/auth/logout")
    def logout(token: str = Depends(session_token)) -> dict[str, str]:
        store.delete_session(token)
        return {"status": "signed_out"}

    @app.get("/api/session")
    def get_session(token: str = Depends(session_token), user: dict = Depends(current_user)) -> dict[str, Any]:
        return {"session_id": token, "user": user}

    # ---------------------------------------------------------------- profile
    @app.get("/api/profile")
    def get_profile(user: dict = Depends(current_user)) -> dict[str, Any]:
        return user

    @app.put("/api/profile")
    def update_profile(req: ProfileUpdate, user: dict = Depends(current_user)) -> dict[str, Any]:
        updates = {k: (v.strip() if isinstance(v, str) else v) for k, v in req.model_dump(exclude_none=True).items()}
        return store.update_user(user["id"], updates)

    # ---------------------------------------------------------------- deals
    @app.get("/api/deals")
    def list_deals(user: dict = Depends(current_user)) -> dict[str, Any]:
        deals = store.list_deals(user["id"])
        threshold = int(user["quiet_days_threshold"])
        for d in deals:
            d["is_quiet"] = d["stage"] in OPEN_STAGES and (d["days_quiet"] or 0) >= threshold
        open_value = sum(d["value_inr"] for d in deals if d["stage"] in OPEN_STAGES)
        return {
            "deals": deals,
            "count": len(deals),
            "open_pipeline_inr": open_value,
            "won_inr": sum(d["value_inr"] for d in deals if d["stage"] == "won"),
        }

    @app.post("/api/deals", status_code=201)
    def create_deal(req: DealCreate, user: dict = Depends(current_user)) -> dict[str, Any]:
        deal = store.create_deal(user["id"], _sanitize_deal_payload(req.model_dump()))
        store.add_activity(
            user["id"],
            type="deal",
            title=f"Deal added: {deal['company']}",
            description=f"{deal['title']} · {format_inr(deal['value_inr'] * 100)}",
            deal_id=deal["id"],
        )
        return deal

    @app.get("/api/deals/{deal_id}")
    def get_deal(deal_id: str, user: dict = Depends(current_user)) -> dict[str, Any]:
        deal = store.get_deal(user["id"], deal_id)
        if deal is None:
            raise HTTPException(status_code=404, detail="Deal not found")
        return deal

    @app.put("/api/deals/{deal_id}")
    def update_deal(deal_id: str, req: DealUpdate, user: dict = Depends(current_user)) -> dict[str, Any]:
        before = store.get_deal(user["id"], deal_id)
        if before is None:
            raise HTTPException(status_code=404, detail="Deal not found")
        deal = store.update_deal(user["id"], deal_id, _sanitize_deal_payload(req.model_dump(exclude_none=True)))
        assert deal is not None
        if req.stage and req.stage != before["stage"]:
            store.add_activity(
                user["id"],
                type="deal",
                title=f"{deal['company']} moved to {req.stage.replace('_', ' ')}",
                description=deal["title"],
                deal_id=deal_id,
            )
        return deal

    @app.delete("/api/deals/{deal_id}")
    def delete_deal(deal_id: str, user: dict = Depends(current_user)) -> dict[str, str]:
        deal = store.get_deal(user["id"], deal_id)
        if deal is None or not store.delete_deal(user["id"], deal_id):
            raise HTTPException(status_code=404, detail="Deal not found")
        store.add_activity(user["id"], type="deal", title=f"Deal removed: {deal['company']}")
        return {"status": "deleted"}

    def draft_followup(user: dict[str, Any], deal: dict[str, Any], instructions: str = "") -> dict[str, Any]:
        if user["kill_switch_active"]:
            raise HTTPException(status_code=423, detail="Kill switch is active. Release it to draft outreach.")
        if deal["do_not_contact"]:
            raise HTTPException(status_code=409, detail=f"{deal['contact_name']} is marked do-not-contact (G12)")
        if not deal["contact_email"]:
            raise HTTPException(status_code=422, detail="Add a contact email to this deal before drafting")
        sender = user["signature"] or user["name"]
        system = (
            "You draft short, warm, professional B2B follow-up emails for a founder. "
            "Use ONLY the facts given. Never invent prices, discounts, dates, meetings, or promises. "
            "If you mention money, use only the deal value given, written in INR (₹). "
            f"Never offer a discount above {user['max_discount_pct']}%. "
            "Output format exactly:\nSUBJECT: <subject line>\n\n<email body ending with the signature>"
        )
        facts = (
            f"Founder: {user['name']} ({user['role']}) at {user['business_name'] or 'their company'}\n"
            f"Signature: {sender}\n"
            f"Recipient: {deal['contact_name']} <{deal['contact_email']}> at {deal['company']}\n"
            f"Deal: {deal['title']}\nStage: {deal['stage'].replace('_', ' ')}\n"
            f"Deal value: {format_inr(deal['value_inr'] * 100)}\n"
            f"Days since last contact: {deal['days_quiet'] if deal['days_quiet'] is not None else 'unknown'}\n"
            f"Founder notes: {deal['notes'] or 'none'}\n"
            f"Extra instructions from founder: {instructions or 'none'}"
        )
        result = call_llm(
            user,
            purpose="draft_followup",
            system=system,
            messages=[{"role": "user", "content": f"Draft the follow-up email.\n\n{facts}"}],
            max_tokens=4000,
        )
        subject, body = parse_draft(result.text, f"Following up: {deal['title']}")
        if not body:
            raise HTTPException(status_code=502, detail="The AI provider returned an empty draft")
        guard = run_guards(user=user, deal=deal, subject=subject, body=body)
        proposal = store.create_proposal(
            user["id"],
            {
                "deal_id": deal["id"],
                "deal_title": f"{deal['company']} · {deal['title']}",
                "contact_name": deal["contact_name"],
                "contact_email": deal["contact_email"],
                "subject": subject,
                "rendered_body": body,
                "rendered_hash": sha256_hex(body),
                "policy_verdict": guard["verdict"],
                "policy_reasons": guard["reasons"],
                "guards_checked": guard["guards_checked"],
                "facts_used": [
                    {"label": "Deal value", "value": format_inr(deal["value_inr"] * 100), "source": f"deal:{deal['id']}"},
                    {"label": "Stage", "value": deal["stage"], "source": f"deal:{deal['id']}"},
                    {"label": "Model", "value": f"{result.provider}/{result.model}", "source": "settings:api_keys"},
                ],
                "status": "blocked" if guard["verdict"] == "BLOCK" else "pending",
            },
        )
        store.add_activity(
            user["id"],
            type="proposed" if guard["verdict"] != "BLOCK" else "blocked",
            title=f"Follow-up drafted for {deal['contact_name']}",
            description=f"{deal['company']} · policy verdict {guard['verdict']}",
            action_ref=proposal["ref"],
            deal_id=deal["id"],
        )
        return proposal

    @app.post("/api/deals/{deal_id}/draft-followup", status_code=201)
    def draft_for_deal(deal_id: str, req: DraftRequest, user: dict = Depends(current_user)) -> dict[str, Any]:
        deal = store.get_deal(user["id"], deal_id)
        if deal is None:
            raise HTTPException(status_code=404, detail="Deal not found")
        return draft_followup(user, deal, req.instructions)

    @app.post("/api/sweep")
    def run_sweep(user: dict = Depends(current_user)) -> dict[str, Any]:
        if user["kill_switch_active"]:
            raise HTTPException(status_code=423, detail="Kill switch is active. Release it to run a sweep.")
        llm_config_for(user)  # fail fast before scanning
        threshold = int(user["quiet_days_threshold"])
        deals = store.list_deals(user["id"])
        drafted, skipped = [], []
        for deal in deals:
            label = f"{deal['company']} ({deal['id']})"
            if deal["stage"] not in OPEN_STAGES:
                continue
            if (deal["days_quiet"] or 0) < threshold:
                continue
            if deal["do_not_contact"]:
                skipped.append({"deal": label, "reason": "do-not-contact"})
                continue
            if not deal["contact_email"]:
                skipped.append({"deal": label, "reason": "no contact email"})
                continue
            if store.has_pending_proposal_for_deal(user["id"], deal["id"]):
                skipped.append({"deal": label, "reason": "already has a pending draft"})
                continue
            try:
                drafted.append(draft_followup(user, deal)["ref"])
            except HTTPException as exc:
                skipped.append({"deal": label, "reason": str(exc.detail)})
        store.add_activity(
            user["id"],
            type="sweep",
            title="Quiet-deal sweep completed",
            description=f"{len(drafted)} draft(s) created, {len(skipped)} skipped (threshold {threshold} days)",
        )
        return {
            "scanned": len(deals),
            "threshold_days": threshold,
            "drafted": drafted,
            "skipped": skipped,
        }

    # ---------------------------------------------------------------- approvals
    @app.get("/api/approvals")
    @app.get("/api/approvals/pending")
    def list_approvals(
        status_filter: str | None = Query(default="pending", alias="status"),
        user: dict = Depends(current_user),
    ) -> dict[str, Any]:
        status_value = None if status_filter in (None, "", "all") else status_filter
        proposals = store.list_proposals(user["id"], status_value)
        now = utcnow()
        for p in proposals:
            if p["status"] == "pending" and parse_iso(p["expires_at"]) <= now:
                store.update_proposal(user["id"], p["ref"], {"status": "expired"})
                p["status"] = "expired"
        if status_value:
            proposals = [p for p in proposals if p["status"] == status_value]
        return {"approvals": proposals, "count": len(proposals)}

    @app.get("/api/approvals/{ref}")
    def get_approval(ref: str, user: dict = Depends(current_user)) -> dict[str, Any]:
        proposal = store.get_proposal(user["id"], ref)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return proposal

    @app.put("/api/approvals/{ref}")
    def edit_approval(ref: str, req: ProposalEdit, user: dict = Depends(current_user)) -> dict[str, Any]:
        proposal = store.get_proposal(user["id"], ref)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        if proposal["status"] not in ("pending", "blocked"):
            raise HTTPException(status_code=409, detail="Only pending drafts can be edited")
        deal = store.get_deal(user["id"], proposal["deal_id"]) if proposal["deal_id"] else None
        deal = deal or {
            "contact_name": proposal["contact_name"],
            "contact_email": proposal["contact_email"],
            "value_inr": 0,
            "do_not_contact": False,
        }
        guard = run_guards(user=user, deal=deal, subject=req.subject, body=req.body)
        store.update_proposal(
            user["id"],
            ref,
            {
                "subject": req.subject.strip(),
                "rendered_body": req.body,
                "rendered_hash": sha256_hex(req.body),
                "status": "blocked" if guard["verdict"] == "BLOCK" else "pending",
                "policy_verdict": guard["verdict"],
                "policy_reasons": guard["reasons"],
            },
        )
        store.add_activity(user["id"], type="edited", title=f"Draft edited for {proposal['contact_name']}", action_ref=ref)
        updated = store.get_proposal(user["id"], ref)
        assert updated is not None
        return updated

    @app.post("/api/approvals/{ref}/decision")
    def decide(ref: str, req: DecisionRequest, user: dict = Depends(current_user)) -> dict[str, Any]:
        proposal = store.get_proposal(user["id"], ref)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        if proposal["status"] == "blocked" and req.decision == "approve":
            raise HTTPException(status_code=409, detail="Blocked by policy guards; edit the draft first")
        if proposal["status"] not in ("pending", "blocked"):
            raise HTTPException(status_code=409, detail=f"Proposal is already {proposal['status']}")
        if not hmac.compare_digest(proposal["rendered_hash"], sha256_hex(proposal["rendered_body"])):
            raise HTTPException(status_code=409, detail="Stored draft no longer matches its hash")
        if not hmac.compare_digest(proposal["rendered_hash"], req.rendered_hash):
            raise HTTPException(
                status_code=409,
                detail="This draft changed since you opened it. Refresh and review it again.",
            )
        if parse_iso(proposal["expires_at"]) <= utcnow():
            store.update_proposal(user["id"], ref, {"status": "expired"})
            raise HTTPException(status_code=409, detail="This draft has expired")

        now_iso = iso(utcnow())
        if req.decision == "reject":
            store.update_proposal(user["id"], ref, {"status": "rejected", "decided_at": now_iso})
            store.add_activity(
                user["id"],
                type="rejected",
                title=f"Rejected draft to {proposal['contact_name']}",
                description=req.rejection_reason or "Rejected by founder",
                action_ref=ref,
                deal_id=proposal["deal_id"],
            )
            return {"ref": ref, "status": "rejected", "receipt": None, "message": "Draft rejected"}

        if user["kill_switch_active"]:
            raise HTTPException(status_code=423, detail="Kill switch is active. Release it to send.")

        timeline = [{"timestamp": now_iso, "event": "Founder approved hash-bound draft"}]
        smtp = store.get_email_settings(user["id"], include_secret=True)
        external_id = None
        if smtp:
            try:
                external_id = mailer.send_email(
                    smtp,
                    to_email=proposal["contact_email"],
                    subject=proposal["subject"],
                    body=proposal["rendered_body"],
                    from_name=user["name"],
                )
            except mailer.MailerError as exc:
                receipt = store.create_receipt(
                    user["id"],
                    {
                        "action_ref": ref,
                        "status": "failed",
                        "recipient_email": proposal["contact_email"],
                        "subject": proposal["subject"],
                        "rendered_hash": proposal["rendered_hash"],
                        "detail": str(exc),
                        "guards_checked": proposal["guards_checked"],
                        "timeline": [*timeline, {"timestamp": iso(utcnow()), "event": f"Send failed: {exc}"}],
                    },
                )
                store.add_activity(
                    user["id"],
                    type="failed",
                    title=f"Email to {proposal['contact_name']} failed",
                    description=str(exc),
                    action_ref=ref,
                    receipt_id=receipt["receipt_id"],
                )
                raise HTTPException(status_code=502, detail=f"Send failed: {exc}. The draft is still pending.") from exc
            receipt_status = "sent"
            detail = f"Delivered to SMTP server {smtp['host']}"
            timeline.append({"timestamp": iso(utcnow()), "event": f"Sent via {smtp['host']} as {smtp['from_email']}"})
        else:
            receipt_status = "approved_manual"
            detail = "No email account connected. Copy the draft and send it yourself, or connect SMTP in Settings."
            timeline.append({"timestamp": iso(utcnow()), "event": "Approved; awaiting manual send (no SMTP configured)"})

        receipt = store.create_receipt(
            user["id"],
            {
                "action_ref": ref,
                "status": receipt_status,
                "recipient_email": proposal["contact_email"],
                "subject": proposal["subject"],
                "rendered_hash": proposal["rendered_hash"],
                "external_id": external_id,
                "detail": detail,
                "guards_checked": proposal["guards_checked"],
                "timeline": timeline,
            },
        )
        store.update_proposal(
            user["id"],
            ref,
            {"status": "sent" if receipt_status == "sent" else "approved", "decided_at": now_iso, "receipt_id": receipt["receipt_id"]},
        )
        if receipt_status == "sent" and proposal["deal_id"]:
            store.update_deal(user["id"], proposal["deal_id"], {"last_contact_at": now_iso})
        store.add_activity(
            user["id"],
            type="sent" if receipt_status == "sent" else "approved",
            title=(
                f"Email sent to {proposal['contact_name']}"
                if receipt_status == "sent"
                else f"Approved draft to {proposal['contact_name']}"
            ),
            description=detail,
            action_ref=ref,
            receipt_id=receipt["receipt_id"],
            deal_id=proposal["deal_id"],
        )
        return {
            "ref": ref,
            "status": "sent" if receipt_status == "sent" else "approved",
            "receipt": receipt,
            "message": detail,
        }

    # ---------------------------------------------------------------- records
    @app.get("/api/receipts")
    def list_receipts(user: dict = Depends(current_user)) -> dict[str, Any]:
        receipts = store.list_receipts(user["id"])
        return {"receipts": receipts, "count": len(receipts)}

    @app.get("/api/receipts/{ref_or_id}")
    def get_receipt(ref_or_id: str, user: dict = Depends(current_user)) -> dict[str, Any]:
        receipt = store.get_receipt(user["id"], ref_or_id)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Receipt not found")
        return receipt

    @app.get("/api/activity")
    def get_activity(
        limit: int = Query(default=100, ge=1, le=500), user: dict = Depends(current_user)
    ) -> dict[str, Any]:
        events = store.list_activity(user["id"], limit)
        return {"events": events, "count": len(events)}

    def build_brief(user: dict[str, Any]) -> dict[str, Any]:
        deals = list_deals(user)
        pending = store.list_proposals(user["id"], "pending")
        receipts = store.list_receipts(user["id"])
        stage_counts: dict[str, int] = {}
        for d in deals["deals"]:
            stage_counts[d["stage"]] = stage_counts.get(d["stage"], 0) + 1
        quiet = [d for d in deals["deals"] if d["is_quiet"]]
        return {
            "generated_at": iso(utcnow()),
            "deal_count": deals["count"],
            "open_pipeline_inr": deals["open_pipeline_inr"],
            "won_inr": deals["won_inr"],
            "stage_counts": stage_counts,
            "quiet_deals": [
                {"id": d["id"], "company": d["company"], "contact_name": d["contact_name"], "days_quiet": d["days_quiet"]}
                for d in quiet
            ],
            "pending_approvals": len(pending),
            "emails_sent": sum(1 for r in receipts if r["status"] == "sent"),
            "recent_activity": store.list_activity(user["id"], 8),
            "kill_switch_active": user["kill_switch_active"],
            "ai_provider": user.get("active_llm_provider"),
        }

    @app.get("/api/brief")
    def get_brief(user: dict = Depends(current_user)) -> dict[str, Any]:
        return build_brief(user)

    # ---------------------------------------------------------------- chat
    def chat_system_prompt(user: dict[str, Any]) -> str:
        brief = build_brief(user)
        deals = store.list_deals(user["id"])
        deal_lines = "\n".join(
            f"- {d['id']}: {d['company']} — {d['title']} | contact {d['contact_name']} <{d['contact_email'] or 'no email'}>"
            f" | stage {d['stage']} | value {format_inr(d['value_inr'] * 100)}"
            f" | quiet {d['days_quiet'] if d['days_quiet'] is not None else '?'}d"
            f"{' | DO NOT CONTACT' if d['do_not_contact'] else ''}"
            f"{' | notes: ' + d['notes'][:200] if d['notes'] else ''}"
            for d in deals[:100]
        ) or "(no deals yet)"
        pending = store.list_proposals(user["id"], "pending")
        pending_lines = "\n".join(
            f"- {p['ref']}: to {p['contact_name']} re '{p['subject']}' (verdict {p['policy_verdict']})" for p in pending[:20]
        ) or "(none)"
        return (
            f"You are the AI chief of staff for {user['name']}, {user['role']} at "
            f"{user['business_name'] or 'their company'}. Be concise, specific and practical. "
            "Ground every claim about deals, money or status in the workspace data below; if the data "
            "does not contain the answer, say so rather than guessing. Use INR (₹, Indian digit grouping) for money. "
            "You cannot send emails yourself: to contact someone, tell the founder to use 'Draft follow-up' on the deal "
            "in the Deals view, which creates a hash-bound draft that they approve in Approvals.\n\n"
            f"Today (UTC): {utcnow().strftime('%Y-%m-%d')}\n"
            f"Quiet-deal threshold: {user['quiet_days_threshold']} days; max autonomous discount: {user['max_discount_pct']}%\n"
            f"Kill switch: {'ACTIVE' if user['kill_switch_active'] else 'off'}\n"
            f"Open pipeline: {format_inr(brief['open_pipeline_inr'] * 100)}; won: {format_inr(brief['won_inr'] * 100)}; "
            f"emails sent: {brief['emails_sent']}\n\n"
            f"DEALS:\n{deal_lines}\n\nPENDING APPROVALS:\n{pending_lines}"
        )

    @app.post("/api/chat")
    def chat(req: ChatRequest, user: dict = Depends(current_user)) -> dict[str, Any]:
        text = req.message.strip()
        if not text:
            raise HTTPException(status_code=422, detail="Message cannot be empty")
        llm_config_for(user)  # 409 before persisting anything if no key
        session = store.get_chat_session(user["id"], req.session_id) if req.session_id else None
        if session is None:
            session = store.create_chat_session(user["id"], text[:60])
        history = store.list_chat_messages(user["id"], session["id"])[-20:]
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": text})
        result = call_llm(user, purpose="chat", system=chat_system_prompt(user), messages=messages)
        user_msg = store.add_chat_message(user["id"], session["id"], "user", text)
        reply = store.add_chat_message(
            user["id"], session["id"], "assistant", result.text or "(empty response)", result.provider, result.model
        )
        return {
            "session_id": session["id"],
            "session_title": session["title"],
            "user_message": user_msg,
            "reply": reply,
            "usage": {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens},
        }

    @app.get("/api/chat/sessions")
    def list_chat_sessions(user: dict = Depends(current_user)) -> dict[str, Any]:
        return {"sessions": store.list_chat_sessions(user["id"])}

    @app.get("/api/chat/sessions/{session_id}")
    def get_chat_session(session_id: str, user: dict = Depends(current_user)) -> dict[str, Any]:
        session = store.get_chat_session(user["id"], session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {**session, "messages": store.list_chat_messages(user["id"], session_id)}

    @app.put("/api/chat/sessions/{session_id}")
    def rename_chat_session(session_id: str, req: RenameChatRequest, user: dict = Depends(current_user)) -> dict[str, str]:
        if store.get_chat_session(user["id"], session_id) is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        store.rename_chat_session(user["id"], session_id, req.title.strip())
        return {"status": "renamed"}

    @app.delete("/api/chat/sessions/{session_id}")
    def delete_chat_session(session_id: str, user: dict = Depends(current_user)) -> dict[str, str]:
        if not store.delete_chat_session(user["id"], session_id):
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"status": "deleted"}

    # ---------------------------------------------------------------- settings: API keys
    def api_keys_view(user_id: str) -> dict[str, Any]:
        user = store.get_user(user_id)
        assert user is not None
        saved = {k["provider"]: k for k in store.list_api_keys(user_id)}
        providers = []
        for pid, meta in llm.PROVIDERS.items():
            entry = saved.get(pid)
            providers.append(
                {
                    "provider": pid,
                    "label": meta["label"],
                    "default_model": meta["default_model"],
                    "default_base_url": meta["base_url"],
                    "key_hint": meta["key_hint"],
                    "docs_url": meta["docs_url"],
                    "configured": bool(entry and (entry["has_key"] or pid == "custom")),
                    "masked_key": entry["masked_key"] if entry else None,
                    "model": entry["model"] if entry else None,
                    "base_url": entry["base_url"] if entry else None,
                    "updated_at": entry["updated_at"] if entry else None,
                    "last_tested_at": entry["last_tested_at"] if entry else None,
                    "last_test_ok": entry["last_test_ok"] if entry else None,
                    "last_test_message": entry["last_test_message"] if entry else None,
                }
            )
        return {"active_provider": user["active_llm_provider"], "providers": providers}

    def require_provider(provider: str) -> None:
        if provider not in llm.PROVIDERS:
            raise HTTPException(status_code=404, detail=f"Unknown provider '{provider}'")

    @app.get("/api/settings/api-keys")
    def get_api_keys(user: dict = Depends(current_user)) -> dict[str, Any]:
        return api_keys_view(user["id"])

    @app.put("/api/settings/api-keys/{provider}")
    def put_api_key(provider: str, req: ApiKeyUpdate, user: dict = Depends(current_user)) -> dict[str, Any]:
        require_provider(provider)
        existing = store.get_api_key(user["id"], provider)
        new_key = (req.api_key or "").strip() or None
        if provider != "custom" and not new_key and not (existing and existing["api_key"]):
            raise HTTPException(status_code=422, detail="Enter an API key")
        base_url = (req.base_url or "").strip() or None
        if base_url and not re.match(r"^https?://", base_url):
            raise HTTPException(status_code=422, detail="Base URL must start with http:// or https://")
        if provider == "custom" and not base_url:
            raise HTTPException(status_code=422, detail="Custom provider needs a base URL")
        model = (req.model or "").strip() or None
        if provider == "custom" and not model:
            raise HTTPException(status_code=422, detail="Custom provider needs a model name")
        store.upsert_api_key(user["id"], provider, api_key=new_key, model=model, base_url=base_url)
        if req.make_active or not user["active_llm_provider"]:
            store.set_active_provider(user["id"], provider)
        store.add_activity(user["id"], type="settings", title=f"{llm.PROVIDERS[provider]['label']} key saved")
        return api_keys_view(user["id"])

    @app.delete("/api/settings/api-keys/{provider}")
    def delete_api_key(provider: str, user: dict = Depends(current_user)) -> dict[str, Any]:
        require_provider(provider)
        store.delete_api_key(user["id"], provider)
        if user["active_llm_provider"] == provider:
            remaining = [k["provider"] for k in store.list_api_keys(user["id"])]
            store.set_active_provider(user["id"], remaining[0] if remaining else None)
        store.add_activity(user["id"], type="settings", title=f"{llm.PROVIDERS[provider]['label']} key removed")
        return api_keys_view(user["id"])

    @app.put("/api/settings/active-provider")
    def set_active_provider(req: ActiveProviderRequest, user: dict = Depends(current_user)) -> dict[str, Any]:
        if req.provider is not None:
            require_provider(req.provider)
            if store.get_api_key(user["id"], req.provider) is None:
                raise HTTPException(status_code=409, detail="Save a key for this provider first")
        store.set_active_provider(user["id"], req.provider)
        return api_keys_view(user["id"])

    @app.post("/api/settings/api-keys/{provider}/test")
    def test_api_key(provider: str, user: dict = Depends(current_user)) -> dict[str, Any]:
        require_provider(provider)
        try:
            config = llm.resolve_config(provider, store.get_api_key(user["id"], provider))
        except llm.LLMNotConfiguredError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        ok, message = llm.test_connection(config)
        store.record_api_key_test(user["id"], provider, ok, message)
        return {"provider": provider, "ok": ok, "message": message, "tested_at": iso(utcnow())}

    @app.get("/api/settings/usage")
    def get_usage(user: dict = Depends(current_user)) -> dict[str, Any]:
        rows = store.usage_summary(user["id"])
        return {
            "by_model": rows,
            "total_requests": sum(r["requests"] for r in rows),
            "total_input_tokens": sum(r["input_tokens"] or 0 for r in rows),
            "total_output_tokens": sum(r["output_tokens"] or 0 for r in rows),
        }

    # ---------------------------------------------------------------- settings: email
    @app.get("/api/settings/email")
    def get_email_settings(user: dict = Depends(current_user)) -> dict[str, Any]:
        return {"configured": store.get_email_settings(user["id"]) is not None, "settings": store.get_email_settings(user["id"])}

    @app.put("/api/settings/email")
    def put_email_settings(req: EmailSettingsUpdate, user: dict = Depends(current_user)) -> dict[str, Any]:
        from_email = req.from_email.strip().lower()
        if not EMAIL_RE.match(from_email):
            raise HTTPException(status_code=422, detail="From address is not a valid email")
        existing = store.get_email_settings(user["id"])
        if not req.password and not (existing and existing["has_password"]):
            raise HTTPException(status_code=422, detail="Enter the SMTP password or app password")
        store.upsert_email_settings(
            user["id"],
            host=req.host.strip(),
            port=req.port,
            username=req.username.strip(),
            password=(req.password or "").strip() or None,
            from_email=from_email,
            use_ssl=req.use_ssl,
        )
        store.add_activity(user["id"], type="settings", title="Email (SMTP) account saved", description=from_email)
        return get_email_settings(user)

    @app.delete("/api/settings/email")
    def delete_email_settings(user: dict = Depends(current_user)) -> dict[str, Any]:
        store.delete_email_settings(user["id"])
        store.add_activity(user["id"], type="settings", title="Email (SMTP) account removed")
        return {"configured": False, "settings": None}

    @app.post("/api/settings/email/test")
    def test_email_settings(user: dict = Depends(current_user)) -> dict[str, Any]:
        smtp = store.get_email_settings(user["id"], include_secret=True)
        if smtp is None:
            raise HTTPException(status_code=409, detail="Save SMTP settings first")
        ok, message = mailer.test_smtp(smtp)
        store.record_email_test(user["id"], ok, message)
        return {"ok": ok, "message": message, "tested_at": iso(utcnow())}

    # ---------------------------------------------------------------- settings: kill switch
    @app.post("/api/settings/kill-switch")
    def toggle_kill_switch(req: KillSwitchRequest, user: dict = Depends(current_user)) -> dict[str, Any]:
        updated = store.set_kill_switch(user["id"], req.active, req.reason or ("Paused by founder" if req.active else None))
        store.add_activity(
            user["id"],
            type="kill_switch",
            title="Kill switch engaged" if req.active else "Kill switch released",
            description=updated["kill_switch_reason"] or "",
        )
        return {"active": updated["kill_switch_active"], "reason": updated["kill_switch_reason"]}

    # ---------------------------------------------------------------- operations
    @app.get("/api/v1/ops/status")
    def ops_status(user: dict = Depends(current_user)) -> dict[str, Any]:
        db_ok = store.health_check()
        provider = user.get("active_llm_provider")
        key_entry = next((k for k in store.list_api_keys(user["id"]) if k["provider"] == provider), None)
        smtp = store.get_email_settings(user["id"])

        def test_status(entry: dict[str, Any] | None) -> str:
            if entry is None:
                return "not_configured"
            if entry.get("last_test_ok") is False:
                return "degraded"
            return "ready"

        components = {
            "api": {"status": "ready", "detail": "API process is serving requests"},
            "database": {
                "status": "ready" if db_ok else "unavailable",
                "detail": store.backend_label if db_ok else f"{store.backend_label} health check failed",
            },
            "ai_provider": {
                "status": test_status(key_entry),
                "detail": (
                    f"{llm.PROVIDERS[provider]['label']} · {key_entry['model'] or llm.PROVIDERS[provider]['default_model']}"
                    + (f" · last test: {key_entry['last_test_message']}" if key_entry and key_entry["last_test_message"] else "")
                    if provider and key_entry
                    else "Add your own API key in Settings → API Keys"
                ),
            },
            "email": {
                "status": test_status(smtp),
                "detail": (
                    f"{smtp['from_email']} via {smtp['host']}:{smtp['port']}" if smtp else "Approved drafts are recorded for manual sending"
                ),
            },
            "kill_switch": {
                "status": "degraded" if user["kill_switch_active"] else "ready",
                "detail": user["kill_switch_reason"] or ("Engaged" if user["kill_switch_active"] else "Released"),
            },
        }
        overall = "ready" if all(c["status"] == "ready" for c in components.values()) else "degraded"
        return {"status": overall, "checked_at": iso(utcnow()), "components": components}

    return app


app = create_app()

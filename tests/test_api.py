"""End-to-end tests for the multi-user Chief-of-Staff API (no network: LLM and SMTP are faked).

Every test runs against SQLite, and again against PostgreSQL when
``POSTGRES_TEST_DATABASE_URL`` is set (CI provides one).
"""

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api import app as app_module
from backend.services import llm
from backend.services.app_store import AppStore

POSTGRES_URL = os.getenv("POSTGRES_TEST_DATABASE_URL", "")
APP_TABLES = (
    "llm_usage",
    "chat_messages",
    "chat_sessions",
    "activity",
    "receipts",
    "proposals",
    "deals",
    "email_settings",
    "api_keys",
    "sessions",
    "users",
)


def _reset_postgres() -> None:
    import psycopg

    with psycopg.connect(POSTGRES_URL, autocommit=True) as conn:
        for table in APP_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


@pytest.fixture(params=["sqlite", "postgres"])
def database(request, tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", "")
    monkeypatch.setenv("APP_KEY_FILE", str(tmp_path / ".app_encryption_key"))
    if request.param == "postgres":
        if not POSTGRES_URL:
            pytest.skip("POSTGRES_TEST_DATABASE_URL is not set")
        _reset_postgres()
        return POSTGRES_URL
    return str(tmp_path / "test.db")


@pytest.fixture()
def client(database):
    application = app_module.create_app(database)
    with TestClient(application) as c:
        yield c


@pytest.fixture()
def fake_llm(monkeypatch):
    calls = []

    def fake_complete(config, *, system, messages, max_tokens=4000):
        calls.append({"config": config, "system": system, "messages": messages})
        last = messages[-1]["content"]
        if "Draft the follow-up email" in last:
            text = "SUBJECT: Checking in on the automation project\n\nHi Asha,\n\nJust checking in on next steps.\n\nBest,\nJay"
        else:
            text = f"echo: {last}"
        return llm.LLMResult(text=text, provider=config.provider, model=config.model, input_tokens=11, output_tokens=7)

    def fake_run_agent(config, *, system, messages, tools, handle_tool, **kwargs):
        calls.append({"config": config, "system": system, "messages": messages, "tools": tools})
        return llm.AgentResult(
            text=f"echo: {messages[-1]['content']}",
            provider=config.provider,
            model=config.model,
            input_tokens=11,
            output_tokens=7,
            steps=1,
        )

    monkeypatch.setattr(llm, "complete", fake_complete)
    monkeypatch.setattr(llm, "run_agent", fake_run_agent)
    return calls


def register(client, email="founder@example.com", password="correct-horse", name="Jay Founder"):
    res = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert res.status_code == 201, res.text
    return {"X-Session-ID": res.json()["session_id"]}


def add_key(client, headers, provider="openai", key="sk-test-1234567890"):
    res = client.put(f"/api/settings/api-keys/{provider}", json={"api_key": key}, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def add_deal(client, headers, **overrides):
    payload = {
        "company": "Acme Logistics",
        "title": "Warehouse automation",
        "contact_name": "Asha Rao",
        "contact_email": "asha@acme.example",
        "stage": "negotiating",
        "value_inr": 480000,
        "last_contact_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
    }
    payload.update(overrides)
    res = client.post("/api/deals", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


# --------------------------------------------------------------------------- auth
def test_register_login_logout_flow(client):
    headers = register(client)
    session = client.get("/api/session", headers=headers)
    assert session.status_code == 200
    assert session.json()["user"]["email"] == "founder@example.com"

    assert client.post("/api/auth/login", json={"email": "founder@example.com", "password": "wrong-pass"}).status_code == 401
    login = client.post("/api/auth/login", json={"email": "FOUNDER@example.com", "password": "correct-horse"})
    assert login.status_code == 200

    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/session", headers=headers).status_code == 401


def test_register_rejects_duplicates_and_weak_input(client):
    register(client)
    dup = client.post("/api/auth/register", json={"name": "X", "email": "founder@example.com", "password": "abcdefgh"})
    assert dup.status_code == 409
    assert client.post("/api/auth/register", json={"name": "X", "email": "bad", "password": "abcdefgh"}).status_code == 422
    assert client.post("/api/auth/register", json={"name": "X", "email": "a@b.co", "password": "short"}).status_code == 422


def test_unknown_email_cannot_log_in(client):
    res = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert res.status_code == 401


def test_protected_routes_require_session(client):
    for path in ("/api/deals", "/api/approvals", "/api/activity", "/api/brief", "/api/settings/api-keys"):
        assert client.get(path).status_code == 401
    assert client.get("/api/deals", headers={"X-Session-ID": "forged"}).status_code == 401


def test_new_account_starts_empty(client):
    headers = register(client)
    assert client.get("/api/deals", headers=headers).json()["count"] == 0
    assert client.get("/api/approvals", headers=headers).json()["count"] == 0
    brief = client.get("/api/brief", headers=headers).json()
    assert brief["deal_count"] == 0 and brief["pending_approvals"] == 0


# --------------------------------------------------------------------------- deals
def test_deal_crud_and_tenant_isolation(client):
    alice = register(client, "alice@example.com")
    bob = register(client, "bob@example.com")
    deal = add_deal(client, alice)
    assert deal["days_quiet"] == 5

    listing = client.get("/api/deals", headers=alice).json()
    assert listing["count"] == 1 and listing["deals"][0]["is_quiet"] is True
    assert listing["open_pipeline_inr"] == 480000

    assert client.get("/api/deals", headers=bob).json()["count"] == 0
    assert client.get(f"/api/deals/{deal['id']}", headers=bob).status_code == 404
    assert client.put(f"/api/deals/{deal['id']}", json={"stage": "won"}, headers=bob).status_code == 404
    assert client.delete(f"/api/deals/{deal['id']}", headers=bob).status_code == 404

    updated = client.put(f"/api/deals/{deal['id']}", json={"stage": "won"}, headers=alice).json()
    assert updated["stage"] == "won"
    assert client.delete(f"/api/deals/{deal['id']}", headers=alice).status_code == 200
    assert client.get("/api/deals", headers=alice).json()["count"] == 0


def test_deal_validation(client):
    headers = register(client)
    res = client.post(
        "/api/deals",
        json={"company": "A", "title": "B", "contact_name": "C", "contact_email": "not-an-email"},
        headers=headers,
    )
    assert res.status_code == 422


# --------------------------------------------------------------------------- API keys
def test_api_keys_are_masked_encrypted_and_per_user(client):
    alice = register(client, "alice@example.com")
    bob = register(client, "bob@example.com")
    view = add_key(client, alice, "anthropic", "sk-ant-secret-ABCD")
    entry = next(p for p in view["providers"] if p["provider"] == "anthropic")
    assert view["active_provider"] == "anthropic"
    assert entry["configured"] and entry["masked_key"] == "••••ABCD"
    assert "sk-ant-secret" not in str(view)

    stored = client.app.state.store._query("SELECT api_key_enc FROM api_keys")
    assert stored and all("sk-ant-secret" not in row["api_key_enc"] for row in stored)

    bob_view = client.get("/api/settings/api-keys", headers=bob).json()
    assert bob_view["active_provider"] is None
    assert not any(p["configured"] for p in bob_view["providers"])

    # Updating model without re-entering the key keeps the key.
    res = client.put("/api/settings/api-keys/anthropic", json={"model": "claude-sonnet-5-5"}, headers=alice)
    entry = next(p for p in res.json()["providers"] if p["provider"] == "anthropic")
    assert entry["masked_key"] == "••••ABCD" and entry["model"] == "claude-sonnet-5-5"

    res = client.delete("/api/settings/api-keys/anthropic", headers=alice)
    assert res.json()["active_provider"] is None


def test_api_key_validation(client):
    headers = register(client)
    assert client.put("/api/settings/api-keys/openai", json={}, headers=headers).status_code == 422
    assert client.put("/api/settings/api-keys/nope", json={"api_key": "x"}, headers=headers).status_code == 404
    assert client.put("/api/settings/api-keys/custom", json={"model": "llama"}, headers=headers).status_code == 422
    ok = client.put(
        "/api/settings/api-keys/custom",
        json={"base_url": "http://localhost:11434/v1", "model": "llama3"},
        headers=headers,
    )
    assert ok.status_code == 200


def test_api_key_test_endpoint(client, fake_llm):
    headers = register(client)
    add_key(client, headers)
    res = client.post("/api/settings/api-keys/openai/test", headers=headers)
    assert res.status_code == 200 and res.json()["ok"] is True
    status = client.get("/api/v1/ops/status", headers=headers).json()
    assert status["components"]["ai_provider"]["status"] == "ready"


# --------------------------------------------------------------------------- chat
def test_chat_requires_api_key(client):
    headers = register(client)
    res = client.post("/api/chat", json={"message": "hello"}, headers=headers)
    assert res.status_code == 409
    assert "API Keys" in res.json()["detail"]


def test_chat_uses_user_key_grounds_on_deals_and_tracks_usage(client, fake_llm):
    headers = register(client)
    add_key(client, headers, "openai", "sk-user-own-key-9999")
    add_deal(client, headers)

    res = client.post("/api/chat", json={"message": "What is quiet?"}, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["reply"]["content"] == "echo: What is quiet?"
    assert fake_llm[-1]["config"].api_key == "sk-user-own-key-9999"
    assert "Acme Logistics" in fake_llm[-1]["system"]

    follow = client.post("/api/chat", json={"message": "and next?", "session_id": body["session_id"]}, headers=headers)
    assert len(fake_llm[-1]["messages"]) == 3  # history replayed
    sessions = client.get("/api/chat/sessions", headers=headers).json()["sessions"]
    assert len(sessions) == 1 and sessions[0]["message_count"] == 4
    assert follow.json()["session_id"] == body["session_id"]

    usage = client.get("/api/settings/usage", headers=headers).json()
    assert usage["total_requests"] == 2
    assert usage["total_input_tokens"] == 22 and usage["total_output_tokens"] == 14

    assert client.delete(f"/api/chat/sessions/{body['session_id']}", headers=headers).status_code == 200
    assert client.get("/api/chat/sessions", headers=headers).json()["sessions"] == []


def test_llm_errors_surface_as_502(client, monkeypatch):
    headers = register(client)
    add_key(client, headers)

    def boom(*args, **kwargs):
        raise llm.LLMError("OpenAI error 401: the API key was rejected.")

    monkeypatch.setattr(llm, "complete", boom)
    res = client.post("/api/chat", json={"message": "hi"}, headers=headers)
    assert res.status_code == 502 and "rejected" in res.json()["detail"]


# --------------------------------------------------------------------------- approvals
def test_draft_approve_without_smtp_records_manual_receipt(client, fake_llm):
    headers = register(client)
    add_key(client, headers)
    deal = add_deal(client, headers)

    draft = client.post(f"/api/deals/{deal['id']}/draft-followup", json={}, headers=headers)
    assert draft.status_code == 201, draft.text
    proposal = draft.json()
    assert proposal["status"] == "pending" and proposal["policy_verdict"] == "ALLOW"
    assert proposal["subject"] == "Checking in on the automation project"

    stale = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": "0" * 64},
        headers=headers,
    )
    assert stale.status_code == 409

    ok = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": proposal["rendered_hash"]},
        headers=headers,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "approved"
    assert ok.json()["receipt"]["status"] == "approved_manual"

    replay = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": proposal["rendered_hash"]},
        headers=headers,
    )
    assert replay.status_code == 409
    receipt = client.get(f"/api/receipts/{proposal['ref']}", headers=headers)
    assert receipt.status_code == 200
    types = [e["type"] for e in client.get("/api/activity", headers=headers).json()["events"]]
    assert "approved" in types and "proposed" in types


def test_approve_sends_via_user_smtp(client, fake_llm, monkeypatch):
    sent = []
    monkeypatch.setattr(app_module.mailer, "send_email", lambda settings, **kw: sent.append((settings, kw)) or "<id@x>")
    headers = register(client)
    add_key(client, headers)
    deal = add_deal(client, headers)
    smtp = client.put(
        "/api/settings/email",
        json={
            "host": "smtp.gmail.com",
            "port": 587,
            "username": "me@gmail.com",
            "password": "app-password-1234",
            "from_email": "me@gmail.com",
        },
        headers=headers,
    )
    assert smtp.status_code == 200
    assert smtp.json()["settings"]["masked_password"] == "••••1234"

    proposal = client.post(f"/api/deals/{deal['id']}/draft-followup", json={}, headers=headers).json()
    res = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": proposal["rendered_hash"]},
        headers=headers,
    )
    assert res.status_code == 200 and res.json()["status"] == "sent"
    assert sent[0][0]["password"] == "app-password-1234"
    assert sent[0][1]["to_email"] == "asha@acme.example"
    refreshed = client.get(f"/api/deals/{deal['id']}", headers=headers).json()
    assert refreshed["days_quiet"] == 0


def test_edit_draft_rehashes_and_guards_block(client, fake_llm):
    headers = register(client)
    add_key(client, headers)
    deal = add_deal(client, headers)
    proposal = client.post(f"/api/deals/{deal['id']}/draft-followup", json={}, headers=headers).json()

    edited = client.put(
        f"/api/approvals/{proposal['ref']}",
        json={"subject": "Hi", "body": "Hello Asha, we can do 20% off this week if you sign. Best, Jay"},
        headers=headers,
    ).json()
    assert edited["rendered_hash"] != proposal["rendered_hash"]
    assert edited["policy_verdict"] == "ASK"  # discount above the 5% mandate

    blocked = client.put(
        f"/api/approvals/{proposal['ref']}",
        json={"subject": "Hi", "body": "Hello Asha, the price is $5000 total. Best regards, Jay"},
        headers=headers,
    ).json()
    assert blocked["policy_verdict"] == "BLOCK" and blocked["status"] == "blocked"
    res = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": blocked["rendered_hash"]},
        headers=headers,
    )
    assert res.status_code == 409

    rejected = client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "reject", "rendered_hash": blocked["rendered_hash"]},
        headers=headers,
    )
    assert rejected.json()["status"] == "rejected"


def test_sweep_and_kill_switch(client, fake_llm):
    headers = register(client)
    add_key(client, headers)
    add_deal(client, headers)
    add_deal(client, headers, company="Fresh Co", last_contact_at=datetime.now(timezone.utc).isoformat())
    add_deal(client, headers, company="Opted Out", do_not_contact=True)

    res = client.post("/api/sweep", headers=headers).json()
    assert len(res["drafted"]) == 1
    assert {"deal": res["skipped"][0]["deal"], "reason": "do-not-contact"} == res["skipped"][0]

    again = client.post("/api/sweep", headers=headers).json()
    assert again["drafted"] == [] and any(s["reason"] == "already has a pending draft" for s in again["skipped"])

    assert client.post("/api/settings/kill-switch", json={"active": True}, headers=headers).json()["active"] is True
    assert client.post("/api/sweep", headers=headers).status_code == 423
    pending = client.get("/api/approvals", headers=headers).json()["approvals"][0]
    res = client.post(
        f"/api/approvals/{pending['ref']}/decision",
        json={"decision": "approve", "rendered_hash": pending["rendered_hash"]},
        headers=headers,
    )
    assert res.status_code == 423
    client.post("/api/settings/kill-switch", json={"active": False}, headers=headers)


def test_profile_update(client):
    headers = register(client)
    res = client.put(
        "/api/profile",
        json={"business_name": "Jay Labs", "max_discount_pct": 10, "quiet_days_threshold": 7},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["business_name"] == "Jay Labs" and body["max_discount_pct"] == 10
    assert client.put("/api/profile", json={"max_discount_pct": 500}, headers=headers).status_code == 422


def test_store_persists_across_restarts(database):
    db = database
    store = AppStore(db)
    user = store.create_user(name="P", email="p@example.com", password="password123")
    store.upsert_api_key(user["id"], "openai", api_key="sk-persist-0000", model=None, base_url=None)
    token = store.create_session(user["id"])
    store.close()

    reopened = AppStore(db)
    assert reopened.authenticate("p@example.com", "password123") is not None
    assert reopened.user_for_session(token)["id"] == user["id"]
    assert reopened.get_api_key(user["id"], "openai")["api_key"] == "sk-persist-0000"
    reopened.close()


def test_health_endpoints(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/api/healthz").status_code == 200
    assert client.get("/readyz").json() == {"status": "ready"}

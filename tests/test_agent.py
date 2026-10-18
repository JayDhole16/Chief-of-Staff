"""Chat agent: provider tool loops, tools, confirmations, test mode, WhatsApp and Calendar.

Providers, Google, Twilio/Meta and SMTP are all faked; no network is used.
"""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.api import app as app_module
from backend.services import google, llm
from tests.test_api import add_deal, add_key, database, register  # noqa: F401  (fixtures)
from tests.test_google import FakeGoogle, connect

KOLKATA = ZoneInfo("Asia/Kolkata")
CONFIG = llm.LLMConfig(provider="openai", api_key="sk-test", model="gpt-test", base_url="https://api.example/v1")


# --------------------------------------------------------------------------- provider loops
class FakeHTTP:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, url, json=None, headers=None, timeout=None):
        self.requests.append({"url": url, "json": json})
        status, body = self.responses.pop(0)
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))


def echo_tool(name, args):
    return {"tool": name, "args": args}, False


def test_openai_compatible_tool_loop(monkeypatch):
    fake = FakeHTTP([
        (200, {"model": "gpt-test", "usage": {"prompt_tokens": 10, "completion_tokens": 5}, "choices": [{"message": {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "find_contacts", "arguments": '{"query": "asha"}'}}],
        }}]}),
        (200, {"model": "gpt-test", "usage": {"prompt_tokens": 20, "completion_tokens": 7}, "choices": [{"message": {"role": "assistant", "content": "Asha is at Acme."}}]}),
    ])
    monkeypatch.setattr(llm.httpx, "post", fake)
    result = llm.run_agent(CONFIG, system="s", messages=[{"role": "user", "content": "who is asha"}], tools=[{"name": "find_contacts", "description": "d", "parameters": {"type": "object", "properties": {}}}], handle_tool=echo_tool)
    assert result.text == "Asha is at Acme." and result.steps == 2
    assert (result.input_tokens, result.output_tokens) == (30, 12)
    assert result.tool_calls[0]["arguments"] == {"query": "asha"}
    second = fake.requests[1]["json"]["messages"]
    assert second[-1]["role"] == "tool" and second[-1]["tool_call_id"] == "c1"
    assert fake.requests[0]["json"]["tools"][0]["function"]["name"] == "find_contacts"


def test_gemini_tool_loop(monkeypatch):
    fake = FakeHTTP([
        (200, {"candidates": [{"content": {"role": "model", "parts": [{"functionCall": {"name": "find_contacts", "args": {"query": "x"}}}]}}], "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2}}),
        (200, {"candidates": [{"content": {"role": "model", "parts": [{"text": "done"}]}}], "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 1}}),
    ])
    monkeypatch.setattr(llm.httpx, "post", fake)
    config = llm.LLMConfig(provider="gemini", api_key="k", model="gemini-test", base_url="https://g.example/v1beta")
    result = llm.run_agent(config, system="s", messages=[{"role": "user", "content": "q"}], tools=[{"name": "find_contacts", "description": "d", "parameters": {"type": "object", "properties": {}}}], handle_tool=echo_tool)
    assert result.text == "done"
    reply_parts = fake.requests[1]["json"]["contents"][-1]["parts"]
    assert reply_parts[0]["functionResponse"]["name"] == "find_contacts"


def test_anthropic_tool_loop_passes_assistant_turn_back(monkeypatch):
    calls = []
    first = SimpleNamespace(
        stop_reason="tool_use",
        model="claude-test",
        usage=SimpleNamespace(input_tokens=5, output_tokens=3),
        content=[SimpleNamespace(type="tool_use", id="tu1", name="find_contacts", input={"query": "a"})],
    )
    final = SimpleNamespace(
        stop_reason="end_turn", model="claude-test", usage=SimpleNamespace(input_tokens=6, output_tokens=2),
        content=[SimpleNamespace(type="text", text="All set.")],
    )

    def fake_create(config, **params):
        calls.append(params)
        return first if len(calls) == 1 else final

    monkeypatch.setattr(llm, "_anthropic_create", fake_create)
    config = llm.LLMConfig(provider="anthropic", api_key="k", model="claude-test", base_url=None)
    result = llm.run_agent(config, system="s", messages=[{"role": "user", "content": "q"}], tools=[{"name": "find_contacts", "description": "d", "parameters": {"type": "object", "properties": {}}}], handle_tool=echo_tool)
    assert result.text == "All set."
    convo = calls[1]["messages"]
    assert convo[1]["content"] is first.content  # assistant turn passed back unchanged
    assert convo[2]["content"][0]["type"] == "tool_result" and convo[2]["content"][0]["tool_use_id"] == "tu1"
    assert calls[0]["tools"][0]["input_schema"]["type"] == "object"


def test_tool_crash_is_reported_not_raised(monkeypatch):
    fake = FakeHTTP([
        (200, {"choices": [{"message": {"tool_calls": [{"id": "c1", "function": {"name": "boom", "arguments": "{}"}}]}}]}),
        (200, {"choices": [{"message": {"content": "That tool failed, sorry."}}]}),
    ])
    monkeypatch.setattr(llm.httpx, "post", fake)

    def crash(name, args):
        raise RuntimeError("kaboom")

    result = llm.run_agent(CONFIG, system="s", messages=[{"role": "user", "content": "q"}], tools=[], handle_tool=crash)
    assert result.text == "That tool failed, sorry."
    assert result.tool_calls[0]["ok"] is False and "kaboom" in json.dumps(result.tool_calls[0]["output"])


def test_step_cap_returns_summary(monkeypatch):
    looping = (200, {"choices": [{"message": {"tool_calls": [{"id": "c", "function": {"name": "find_contacts", "arguments": "{}"}}]}}]})
    monkeypatch.setattr(llm.httpx, "post", FakeHTTP([looping] * 3))
    result = llm.run_agent(CONFIG, system="s", messages=[{"role": "user", "content": "q"}], tools=[], handle_tool=echo_tool, max_steps=3)
    assert "ran out of steps" in result.text and len(result.tool_calls) == 3


# --------------------------------------------------------------------------- end-to-end tools via /api/chat
class FakeGoogleFull(FakeGoogle):
    def __init__(self):
        super().__init__()
        self.events = {"evt-9": {"id": "evt-9", "summary": "Client check-in", "start": {"dateTime": "2026-12-01T09:30:00+00:00"}, "end": {"dateTime": "2026-12-01T10:00:00+00:00"}, "attendees": [{"email": "asha@acme.example"}]}}

    def handler(self, request):
        url = str(request.url).split("?")[0]
        if url.startswith(google.CALENDAR_EVENTS_URL + "/"):
            self.requests.append(request)
            event_id = url.rsplit("/", 1)[1]
            if request.method == "GET":
                return httpx.Response(200, json=self.events[event_id])
            if request.method == "PATCH":
                self.events[event_id].update(json.loads(request.content))
                return httpx.Response(200, json=self.events[event_id])
            if request.method == "DELETE":
                self.events.pop(event_id, None)
                return httpx.Response(204)
        if url == google.CALENDAR_EVENTS_URL and request.method == "GET" and not self.busy:
            self.requests.append(request)
            return httpx.Response(200, json={"items": list(self.events.values())})
        return super().handler(request)


class FakeTwilio:
    def __init__(self):
        self.sent = []

    def handler(self, request):
        url = str(request.url)
        if request.method == "POST" and url.endswith("/Messages.json"):
            form = parse_qs(request.content.decode())
            self.sent.append({k: v[0] for k, v in form.items()})
            return httpx.Response(201, json={"sid": f"SM{len(self.sent):032d}", "status": "queued"})
        if request.method == "GET" and "/Messages/" in url:
            return httpx.Response(200, json={"status": "delivered", "error_code": None})
        if request.method == "GET" and url.endswith(".json"):
            return httpx.Response(200, json={"friendly_name": "Test account", "status": "active"})
        return httpx.Response(404, json={"code": 20404, "message": "not found"})


@pytest.fixture()
def env(database, monkeypatch):  # noqa: F811
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    fake_google, twilio = FakeGoogleFull(), FakeTwilio()
    app = app_module.create_app(
        database,
        google_http=httpx.Client(transport=httpx.MockTransport(fake_google.handler)),
        whatsapp_http=httpx.Client(transport=httpx.MockTransport(twilio.handler)),
    )
    with TestClient(app, follow_redirects=False) as client:
        yield SimpleNamespace(client=client, google=fake_google, twilio=twilio)


@pytest.fixture()
def script(monkeypatch):
    """Replace the model with a script of tool calls; the real toolbox and endpoints run."""
    state = {"calls": [], "results": []}

    def fake_run_agent(config, *, system, messages, tools, handle_tool, **kwargs):
        result = llm.AgentResult(text="", provider=config.provider, model=config.model, steps=1)
        for name, args in state["calls"]:
            output, is_error = handle_tool(name, args)
            state["results"].append((name, output, is_error))
            result.tool_calls.append({"name": name, "arguments": args, "ok": not is_error, "output": output})
        result.text = "Prepared. Please confirm below." if state["calls"] else "ok"
        state["system"] = system
        return result

    monkeypatch.setattr(llm, "run_agent", fake_run_agent)
    return state


def setup_user(client, *, kolkata=True):
    headers = register(client)
    add_key(client, headers)
    if kolkata:
        client.put("/api/profile", headers=headers, json={"timezone": "Asia/Kolkata"})
    return headers


def chat(client, headers, text="go"):
    res = client.post("/api/chat", headers=headers, json={"message": text})
    assert res.status_code == 200, res.text
    return res.json()


def approve(client, headers, proposal):
    return client.post(
        f"/api/approvals/{proposal['ref']}/decision",
        headers=headers,
        json={"decision": "approve", "rendered_hash": proposal["rendered_hash"]},
    )


def test_natural_language_email_with_contact_lookup_and_test_mode(env, script, monkeypatch):
    sent = []
    monkeypatch.setattr(app_module.mailer, "send_email", lambda settings, **kw: sent.append(kw) or "<id@x>")
    c = env.client
    headers = setup_user(c)
    add_deal(c, headers)  # Asha Rao <asha@acme.example>
    c.put("/api/settings/email", headers=headers, json={"host": "smtp.x", "port": 587, "username": "u", "password": "p-1234", "from_email": "me@example.com"})
    profile = c.put("/api/profile", headers=headers, json={"sandbox_emails": "jayraj@example.com, lead@example.com", "sandbox_enabled": True})
    assert profile.status_code == 200 and profile.json()["sandbox_enabled"] is True

    script["calls"] = [
        ("find_contacts", {"query": "Asha"}),
        ("draft_email", {"to": "Asha", "subject": "Following up", "body": "Hi Asha, checking in on next steps.\n\nJay"}),
    ]
    body = chat(c, headers, "Send a follow-up email to Asha")
    assert script["results"][0][1]["contacts"][0]["email"] == "asha@acme.example"
    assert len(body["actions"]) == 1
    action = body["actions"][0]
    assert action["kind"] == "email" and action["contact_email"] == "asha@acme.example" and action["status"] == "pending"
    assert [t["name"] for t in body["tool_calls"]] == ["find_contacts", "draft_email"]

    res = approve(c, headers, action)
    assert res.status_code == 200, res.text
    assert sent[0]["to_email"] == "jayraj@example.com, lead@example.com"
    assert sent[0]["subject"].startswith("[TEST → asha@acme.example]")
    assert "test mode" in res.json()["message"]

    session = c.get(f"/api/chat/sessions/{body['session_id']}", headers=headers).json()
    assert session["messages"][1]["actions"][0]["status"] == "sent"


def test_contact_errors_are_reported_to_the_model(env, script):
    c = env.client
    headers = setup_user(c)
    add_deal(c, headers, contact_name="Raj Iyer", contact_email="raj@a.example")
    add_deal(c, headers, contact_name="Raj Mehta", contact_email="raj@b.example", company="Beta")
    script["calls"] = [
        ("draft_email", {"to": "Raj", "subject": "s", "body": "Hello there, following up."}),
        ("draft_email", {"to": "not-an-email@", "subject": "s", "body": "Hello there, following up."}),
        ("draft_email", {"to": "Nobody", "subject": "s", "body": "Hello there, following up."}),
    ]
    body = chat(c, headers)
    errors = [r[1]["error"] for r in script["results"]]
    assert "several contacts" in errors[0] and "not a valid email" in errors[1] and "No contact matches" in errors[2]
    assert body["actions"] == [] and all(not t["ok"] for t in body["tool_calls"])


def test_whatsapp_via_twilio_with_delivery_status(env, script):
    c = env.client
    headers = setup_user(c)
    deal = add_deal(c, headers, contact_phone="+91 98765 43210")
    assert deal["contact_phone"] == "+919876543210"

    script["calls"] = [("send_whatsapp", {"to": "Asha", "message": "We are ready."})]
    chat(c, headers)
    assert "not set up" in script["results"][0][1]["error"]

    bad = c.put("/api/settings/whatsapp", headers=headers, json={"provider": "twilio", "account_id": "nope", "token": "t", "from_number": "+14155238886"})
    assert bad.status_code == 422
    saved = c.put("/api/settings/whatsapp", headers=headers, json={"provider": "twilio", "account_id": "AC" + "0" * 32, "token": "tok-1234", "from_number": "+14155238886"})
    assert saved.status_code == 200 and saved.json()["settings"]["masked_token"] == "••••1234"
    assert c.post("/api/settings/whatsapp/test", headers=headers).json()["ok"] is True

    script["calls"], script["results"] = [("send_whatsapp", {"to": "Asha", "message": "We are ready."})], []
    action = chat(c, headers)["actions"][0]
    assert action["kind"] == "whatsapp" and action["contact_email"] == "+919876543210"

    res = approve(c, headers, action)
    assert res.status_code == 200, res.text
    assert env.twilio.sent[0] == {"From": "whatsapp:+14155238886", "To": "whatsapp:+919876543210", "Body": "We are ready."}
    receipt = res.json()["receipt"]
    assert receipt["delivery_status"] == "queued"
    refreshed = c.post(f"/api/receipts/{receipt['receipt_id']}/refresh-delivery", headers=headers).json()
    assert refreshed["delivery_status"] == "delivered"


def test_whatsapp_test_mode_reroutes_to_test_numbers(env, script):
    c = env.client
    headers = setup_user(c)
    add_deal(c, headers, contact_phone="+919876543210")
    c.put("/api/settings/whatsapp", headers=headers, json={"provider": "twilio", "account_id": "AC" + "1" * 32, "token": "tok", "from_number": "+14155238886"})
    assert c.put("/api/profile", headers=headers, json={"sandbox_enabled": True}).status_code == 422  # no targets yet
    assert c.put("/api/profile", headers=headers, json={"sandbox_phones": "12345"}).status_code == 422
    c.put("/api/profile", headers=headers, json={"sandbox_phones": "+91 90000 00001", "sandbox_enabled": True})
    script["calls"] = [("send_whatsapp", {"to": "+919876543210", "message": "Ready!"})]
    action = chat(c, headers)["actions"][0]
    approve(c, headers, action)
    assert env.twilio.sent[0]["To"] == "whatsapp:+919000000001"
    assert env.twilio.sent[0]["Body"].startswith("[TEST →")


def test_reminder_from_natural_language_uses_user_timezone(env, script):
    c = env.client
    headers = setup_user(c)
    connect(c, headers, env.google)
    tomorrow = (datetime.now(KOLKATA) + timedelta(days=1)).date()
    script["calls"] = [("set_reminder", {"title": "Client check-in", "at": f"{tomorrow}T15:00", "minutes_before": 10})]
    action = chat(c, headers, "Set a reminder for client check-in tomorrow at 3 PM")["actions"][0]
    assert action["kind"] == "calendar"
    expected = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 15, 0, tzinfo=KOLKATA).astimezone(timezone.utc)
    assert datetime.fromisoformat(action["payload"]["start_utc"]) == expected
    assert action["payload"]["attendees"] == [] and action["payload"]["reminder_minutes"] == 10

    res = approve(c, headers, action)
    assert res.status_code == 200 and res.json()["status"] == "booked"
    created = env.google.last(google.CALENDAR_EVENTS_URL)
    event = json.loads(created.content)
    assert event["attendees"] == [] and "sendUpdates=none" in str(created.url)
    assert event["reminders"] == {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}
    assert event["start"]["timeZone"] == "Asia/Kolkata"


def test_calendar_view_update_delete_and_meeting_with_contact(env, script):
    c = env.client
    headers = setup_user(c)
    connect(c, headers, env.google)
    add_deal(c, headers)

    script["calls"] = [("list_calendar_events", {"start": "2026-12-01T00:00", "end": "2026-12-01T23:59"})]
    chat(c, headers, "What's on my calendar on 1 Dec?")
    listed = script["results"][0][1]
    assert listed["events"][0]["event_id"] == "evt-9" and "15:00" in listed["events"][0]["start"]

    script["calls"], script["results"] = [("update_calendar_event", {"event_id": "evt-9", "start": "2026-12-01T16:00"})], []
    update = chat(c, headers)["actions"][0]
    assert update["kind"] == "calendar_update" and "16:00" in update["rendered_body"]
    assert approve(c, headers, update).json()["status"] == "updated"
    assert env.google.events["evt-9"]["start"]["dateTime"].startswith("2026-12-01T10:30")

    script["calls"], script["results"] = [("delete_calendar_event", {"event_id": "evt-9"})], []
    delete = chat(c, headers)["actions"][0]
    assert delete["kind"] == "calendar_delete"
    assert approve(c, headers, delete).json()["status"] == "deleted"
    assert "evt-9" not in env.google.events

    start = (datetime.now(KOLKATA) + timedelta(days=2)).replace(hour=11, minute=0, second=0, microsecond=0)
    script["calls"], script["results"] = [("create_calendar_event", {"title": "Pilot review", "start": start.strftime("%Y-%m-%dT%H:%M"), "attendees": ["Asha"], "duration_minutes": 45})], []
    meeting = chat(c, headers)["actions"][0]
    assert meeting["payload"]["attendees"] == ["asha@acme.example"] and meeting["payload"]["with_meet"] is True
    booked = approve(c, headers, meeting)
    assert booked.json()["status"] == "booked"
    event = json.loads(env.google.last(google.CALENDAR_EVENTS_URL).content)
    assert event["attendees"] == [{"email": "asha@acme.example"}]


def test_calendar_tools_without_google_explain_setup(env, script):
    c = env.client
    headers = setup_user(c)
    script["calls"] = [("list_calendar_events", {"start": "2026-12-01T00:00", "end": "2026-12-02T00:00"})]
    body = chat(c, headers)
    assert "Connect your Google account" in script["results"][0][1]["error"]
    assert body["tool_calls"][0]["ok"] is False


def test_past_times_and_bad_dates_are_rejected(env, script):
    c = env.client
    headers = setup_user(c)
    connect(c, headers, env.google)
    script["calls"] = [
        ("set_reminder", {"title": "x", "at": "2020-01-01T10:00"}),
        ("set_reminder", {"title": "x", "at": "next tuesday-ish"}),
    ]
    chat(c, headers)
    assert "in the past" in script["results"][0][1]["error"]
    assert "not a date-time" in script["results"][1][1]["error"]


def test_system_prompt_has_local_time_and_tool_rules(env, script):
    c = env.client
    headers = setup_user(c)
    chat(c, headers, "hello")
    assert "Asia/Kolkata" in script["system"] and "never invent" in script["system"]


def test_agent_tools_http_endpoint_used_by_mcp(env):
    c = env.client
    headers = setup_user(c)
    add_deal(c, headers)
    names = {t["name"] for t in c.get("/api/agent/tools", headers=headers).json()["tools"]}
    assert {"find_contacts", "draft_email", "send_whatsapp", "set_reminder", "delete_calendar_event"} <= names
    assert c.get("/api/agent/tools").status_code == 401

    found = c.post("/api/agent/tools/find_contacts", headers=headers, json={"arguments": {"query": "asha"}}).json()
    assert found["ok"] and found["result"]["contacts"][0]["email"] == "asha@acme.example"
    drafted = c.post(
        "/api/agent/tools/draft_email",
        headers=headers,
        json={"arguments": {"to": "Asha", "subject": "Hi", "body": "Hello Asha, quick follow-up on the pilot."}},
    ).json()
    assert drafted["ok"] and drafted["actions"][0]["status"] == "pending"
    failed = c.post("/api/agent/tools/send_whatsapp", headers=headers, json={"arguments": {"to": "Asha", "message": "x"}}).json()
    assert failed["ok"] is False and "not set up" in failed["result"]["error"]
    assert c.post("/api/agent/tools/rm_rf", headers=headers, json={}).status_code == 404

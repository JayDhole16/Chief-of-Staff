"""Google OAuth, Gmail send and Calendar booking, against a fake Google (httpx.MockTransport)."""

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.api import app as app_module
from backend.services import google
from tests.test_api import add_deal, add_key, database, fake_llm, register  # noqa: F401  (fixtures)


class FakeGoogle:
    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.busy: list[dict] = []
        self.refresh_fails = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if url.startswith(google.TOKEN_URL):
            form = parse_qs(request.content.decode())
            if form["grant_type"] == ["authorization_code"]:
                return httpx.Response(200, json={
                    "access_token": "ya29.first",
                    "refresh_token": "1//refresh",
                    "expires_in": 3600,
                    "scope": " ".join(google.SCOPES),
                })
            if self.refresh_fails:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "ya29.refreshed", "expires_in": 3600})
        if url.startswith(google.USERINFO_URL):
            return httpx.Response(200, json={"email": "founder@gmail.com"})
        if url.startswith(google.GMAIL_SEND_URL):
            return httpx.Response(200, json={"id": "gmail-123"})
        if url.startswith(google.CALENDAR_EVENTS_URL) and request.method == "GET":
            return httpx.Response(200, json={"items": self.busy})
        if url.startswith(google.CALENDAR_EVENTS_URL) and request.method == "POST":
            return httpx.Response(200, json={
                "id": "evt-1",
                "hangoutLink": "https://meet.google.com/abc-defg-hij",
                "htmlLink": "https://calendar.google.com/event?eid=1",
            })
        if url.startswith(google.REVOKE_URL):
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"error": "unexpected " + url})

    def last(self, prefix: str, method: str = "POST") -> httpx.Request:
        return [r for r in self.requests if str(r.url).startswith(prefix) and r.method == method][-1]


@pytest.fixture()
def fake_google():
    return FakeGoogle()


@pytest.fixture()
def gclient(database, fake_google, monkeypatch):  # noqa: F811
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-123.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:5173")
    http = httpx.Client(transport=httpx.MockTransport(fake_google.handler))
    application = app_module.create_app(database, google_http=http)
    with TestClient(application, follow_redirects=False) as c:
        yield c


def connect(client, headers, fake_google):
    res = client.post("/api/integrations/google/connect", headers=headers)
    assert res.status_code == 200, res.text
    query = parse_qs(urlparse(res.json()["auth_url"]).query)
    callback = client.get(f"/api/integrations/google/callback?state={query['state'][0]}&code=auth-code")
    return query, callback


def future(hours=26):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def test_google_disabled_without_server_credentials(database, monkeypatch):  # noqa: F811
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    with TestClient(app_module.create_app(database)) as c:
        headers = register(c)
        assert c.get("/api/integrations/google", headers=headers).json()["configured"] is False
        assert c.post("/api/integrations/google/connect", headers=headers).status_code == 503


def test_oauth_connect_with_pkce_and_single_use_state(gclient, fake_google):
    headers = register(gclient)
    query, callback = connect(gclient, headers, fake_google)
    assert query["client_id"] == ["client-123.apps.googleusercontent.com"]
    assert query["access_type"] == ["offline"] and query["code_challenge_method"] == ["S256"]
    assert google.GMAIL_SEND_SCOPE in query["scope"][0] and google.CALENDAR_EVENTS_SCOPE in query["scope"][0]
    assert query["redirect_uri"] == ["http://localhost:5173/api/integrations/google/callback"]

    assert callback.status_code == 303
    assert callback.headers["location"].startswith("http://localhost:5173/?google=connected")

    verifier = parse_qs(fake_google.last(google.TOKEN_URL).content.decode())["code_verifier"][0]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == query["code_challenge"][0]

    status = gclient.get("/api/integrations/google", headers=headers).json()
    assert status["connected"] and status["email"] == "founder@gmail.com"
    assert status["can_send_email"] and status["can_manage_calendar"]
    assert "ya29" not in json.dumps(status)

    replay = gclient.get(f"/api/integrations/google/callback?state={query['state'][0]}&code=auth-code")
    assert "google=error" in replay.headers["location"]
    forged = gclient.get("/api/integrations/google/callback?state=forged&code=x")
    assert "google=error" in forged.headers["location"]


def test_denied_consent_redirects_with_error(gclient, fake_google):
    headers = register(gclient)
    res = gclient.post("/api/integrations/google/connect", headers=headers)
    state = parse_qs(urlparse(res.json()["auth_url"]).query)["state"][0]
    callback = gclient.get(f"/api/integrations/google/callback?state={state}&error=access_denied")
    assert "google=error" in callback.headers["location"]
    assert gclient.get("/api/integrations/google", headers=headers).json()["connected"] is False


def test_approved_email_is_sent_through_gmail(gclient, fake_google, fake_llm):  # noqa: F811
    headers = register(gclient)
    connect(gclient, headers, fake_google)
    add_key(gclient, headers)
    deal = add_deal(gclient, headers)
    proposal = gclient.post(f"/api/deals/{deal['id']}/draft-followup", json={}, headers=headers).json()

    res = gclient.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": proposal["rendered_hash"]},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "sent"
    assert res.json()["receipt"]["external_id"] == "gmail-123"

    sent = fake_google.last(google.GMAIL_SEND_URL)
    assert sent.headers["authorization"] == "Bearer ya29.first"
    raw = base64.urlsafe_b64decode(json.loads(sent.content)["raw"])
    message = message_from_bytes(raw)
    assert message["To"] == "asha@acme.example" and "founder@gmail.com" in message["From"]
    assert message["Subject"] == proposal["subject"]


def test_meeting_is_proposed_hash_bound_and_booked(gclient, fake_google):
    headers = register(gclient)
    connect(gclient, headers, fake_google)
    deal = add_deal(gclient, headers)
    start = future()

    res = gclient.post(
        f"/api/deals/{deal['id']}/meeting",
        json={"title": "Intro call", "start_utc": start, "duration_minutes": 45, "agenda": "Walk through the pilot plan.", "timezone": "Asia/Kolkata"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    proposal = res.json()
    assert proposal["kind"] == "calendar" and proposal["policy_verdict"] == "ALLOW"
    assert proposal["payload"]["duration_minutes"] == 45

    edited = gclient.put(
        f"/api/approvals/{proposal['ref']}",
        json={"subject": "Intro call", "body": "Walk through the pilot plan and pricing questions."},
        headers=headers,
    ).json()
    assert edited["rendered_hash"] != proposal["rendered_hash"]
    stale = gclient.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": proposal["rendered_hash"]},
        headers=headers,
    )
    assert stale.status_code == 409

    booked = gclient.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": edited["rendered_hash"]},
        headers=headers,
    )
    assert booked.status_code == 200, booked.text
    body = booked.json()
    assert body["status"] == "booked" and body["receipt"]["external_id"] == "evt-1"
    assert "meet.google.com" in body["message"]

    created = fake_google.last(google.CALENDAR_EVENTS_URL)
    assert "sendUpdates=all" in str(created.url) and "conferenceDataVersion=1" in str(created.url)
    event = json.loads(created.content)
    assert event["attendees"] == [{"email": "asha@acme.example"}]
    assert event["start"]["timeZone"] == "Asia/Kolkata"
    assert event["description"].startswith("Walk through the pilot plan and pricing questions.")


def test_meeting_conflict_requires_review(gclient, fake_google):
    headers = register(gclient)
    connect(gclient, headers, fake_google)
    deal = add_deal(gclient, headers)
    fake_google.busy = [{"summary": "Board meeting", "status": "confirmed"}]
    res = gclient.post(
        f"/api/deals/{deal['id']}/meeting",
        json={"title": "Intro call", "start_utc": future(), "duration_minutes": 30},
        headers=headers,
    ).json()
    assert res["policy_verdict"] == "ASK"
    assert any("Board meeting" in r for r in res["policy_reasons"])


def test_meeting_requires_google_and_future_time(gclient, fake_google):
    headers = register(gclient)
    deal = add_deal(gclient, headers)
    no_google = gclient.post(
        f"/api/deals/{deal['id']}/meeting", json={"title": "Call", "start_utc": future()}, headers=headers
    )
    assert no_google.status_code == 409
    connect(gclient, headers, fake_google)
    past = gclient.post(
        f"/api/deals/{deal['id']}/meeting",
        json={"title": "Call", "start_utc": datetime.now(timezone.utc).isoformat()},
        headers=headers,
    )
    assert past.status_code == 422


def test_expired_access_token_is_refreshed(gclient, fake_google):
    headers = register(gclient)
    connect(gclient, headers, fake_google)
    store = gclient.app.state.store
    user_id = gclient.get("/api/session", headers=headers).json()["user"]["id"]
    store.update_google_access_token(user_id, "ya29.stale", (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat())

    res = gclient.post("/api/integrations/google/test", headers=headers).json()
    assert res["ok"] is True
    assert fake_google.last(google.USERINFO_URL, "GET").headers["authorization"] == "Bearer ya29.refreshed"


def test_revoked_access_keeps_draft_pending(gclient, fake_google):
    headers = register(gclient)
    connect(gclient, headers, fake_google)
    deal = add_deal(gclient, headers)
    proposal = gclient.post(
        f"/api/deals/{deal['id']}/meeting", json={"title": "Call", "start_utc": future()}, headers=headers
    ).json()

    store = gclient.app.state.store
    user_id = gclient.get("/api/session", headers=headers).json()["user"]["id"]
    store.update_google_access_token(user_id, "ya29.stale", (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat())
    fake_google.refresh_fails = True

    res = gclient.post(
        f"/api/approvals/{proposal['ref']}/decision",
        json={"decision": "approve", "rendered_hash": proposal["rendered_hash"]},
        headers=headers,
    )
    assert res.status_code == 409 and "Reconnect Google" in res.json()["detail"]
    assert gclient.get(f"/api/approvals/{proposal['ref']}", headers=headers).json()["status"] == "pending"
    assert gclient.get("/api/integrations/google", headers=headers).json()["last_error"]


def test_disconnect_revokes_and_forgets_tokens(gclient, fake_google):
    headers = register(gclient)
    connect(gclient, headers, fake_google)
    res = gclient.delete("/api/integrations/google", headers=headers).json()
    assert res["connected"] is False
    revoke = fake_google.last(google.REVOKE_URL)
    assert parse_qs(revoke.content.decode())["token"] == ["1//refresh"]

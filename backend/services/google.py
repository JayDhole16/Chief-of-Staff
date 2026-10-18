"""
Google OAuth 2.0 (Authorization Code + PKCE), Gmail send and Calendar events.

The app owner registers one OAuth client (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET);
each user then connects their own Google account. Tokens are stored per user,
encrypted, by AppStore. Only two scopes are requested: sending mail and managing
calendar events.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import httpx

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"
SCOPES = ("openid", "email", GMAIL_SEND_SCOPE, CALENDAR_EVENTS_SCOPE)
TIMEOUT_SECONDS = 20.0


class GoogleError(Exception):
    """Google call failed; message is safe to show to the user."""


class GoogleAuthRevokedError(GoogleError):
    """The refresh token is no longer valid; the user must reconnect."""


@dataclass
class GoogleConfig:
    client_id: str
    client_secret: str
    redirect_uri: str

    @classmethod
    def from_env(cls) -> GoogleConfig | None:
        client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            return None
        # The callback must reach the API: PUBLIC_API_URL when the API has its own domain
        # (hosted), otherwise APP_BASE_URL whose /api is proxied to the API (Vite, Compose).
        base = (
            os.getenv("PUBLIC_API_URL", "").strip()
            or os.getenv("APP_BASE_URL", "http://localhost:5173").strip()
        ).rstrip("/")
        redirect = os.getenv("GOOGLE_REDIRECT_URI", "").strip() or f"{base}/api/integrations/google/callback"
        return cls(client_id=client_id, client_secret=client_secret, redirect_uri=redirect)


def new_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


class GoogleClient:
    def __init__(self, config: GoogleConfig, http: httpx.Client | None = None):
        self.config = config
        self.http = http or httpx.Client(timeout=TIMEOUT_SECONDS)

    # ------------------------------------------------------------------ OAuth
    def authorization_url(self, state: str, code_challenge: str, login_hint: str | None = None) -> str:
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        if login_hint:
            params["login_hint"] = login_hint
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        return self._token_request(
            {
                "code": code,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            }
        )

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        return self._token_request(
            {
                "refresh_token": refresh_token,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "grant_type": "refresh_token",
            }
        )

    def revoke(self, token: str) -> None:
        try:
            self.http.post(REVOKE_URL, data={"token": token})
        except httpx.HTTPError:
            pass  # best effort; the local tokens are deleted regardless

    def userinfo(self, access_token: str) -> dict[str, Any]:
        return self._get(USERINFO_URL, access_token)

    def _token_request(self, data: dict[str, str]) -> dict[str, Any]:
        try:
            response = self.http.post(TOKEN_URL, data=data)
        except httpx.HTTPError as exc:
            raise GoogleError(f"Could not reach Google: {exc}") from exc
        body = _json(response)
        if response.status_code >= 400:
            error = body.get("error", "")
            if error == "invalid_grant":
                raise GoogleAuthRevokedError("Google access was revoked or expired. Reconnect Google.")
            if error in ("invalid_client", "unauthorized_client"):
                raise GoogleError("Google rejected the app's OAuth client. Check GOOGLE_CLIENT_ID/SECRET.")
            raise GoogleError(f"Google token error: {body.get('error_description') or error or response.status_code}")
        return body

    # ------------------------------------------------------------------ Gmail
    def send_email(self, access_token: str, *, from_email: str, from_name: str | None, to_email: str, subject: str, body: str) -> str:
        msg = EmailMessage()
        msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        result = self._post(GMAIL_SEND_URL, access_token, {"raw": raw})
        return str(result.get("id", ""))

    # ------------------------------------------------------------------ Calendar
    def list_events(self, access_token: str, *, time_min: str, time_max: str) -> list[dict[str, Any]]:
        params = {"timeMin": time_min, "timeMax": time_max, "singleEvents": "true", "orderBy": "startTime", "maxResults": "20"}
        result = self._get(f"{CALENDAR_EVENTS_URL}?{urlencode(params)}", access_token)
        return [e for e in result.get("items", []) if e.get("status") != "cancelled" and e.get("transparency") != "transparent"]

    def create_event(
        self,
        access_token: str,
        *,
        summary: str,
        description: str,
        start_utc: str,
        end_utc: str,
        timezone: str,
        attendee_email: str,
        with_meet: bool = True,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_utc, "timeZone": timezone},
            "end": {"dateTime": end_utc, "timeZone": timezone},
            "attendees": [{"email": attendee_email}],
            "reminders": {"useDefault": True},
        }
        query = {"sendUpdates": "all"}
        if with_meet:
            event["conferenceData"] = {
                "createRequest": {"requestId": uuid4().hex, "conferenceSolutionKey": {"type": "hangoutsMeet"}}
            }
            query["conferenceDataVersion"] = "1"
        return self._post(f"{CALENDAR_EVENTS_URL}?{urlencode(query)}", access_token, event)

    # ------------------------------------------------------------------ HTTP helpers
    def _get(self, url: str, access_token: str) -> dict[str, Any]:
        try:
            response = self.http.get(url, headers={"Authorization": f"Bearer {access_token}"})
        except httpx.HTTPError as exc:
            raise GoogleError(f"Could not reach Google: {exc}") from exc
        return _checked(response)

    def _post(self, url: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.http.post(url, json=payload, headers={"Authorization": f"Bearer {access_token}"})
        except httpx.HTTPError as exc:
            raise GoogleError(f"Could not reach Google: {exc}") from exc
        return _checked(response)


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _checked(response: httpx.Response) -> dict[str, Any]:
    body = _json(response)
    if response.status_code < 400:
        return body
    err = body.get("error")
    message = err.get("message") if isinstance(err, dict) else (err or response.text[:200])
    if response.status_code == 401:
        raise GoogleAuthRevokedError("Google session expired or was revoked. Reconnect Google.")
    if response.status_code == 403:
        raise GoogleError(
            f"Google denied the request (403): {message}. Make sure the Gmail and Calendar APIs are "
            "enabled in your Google Cloud project and the permissions were granted."
        )
    raise GoogleError(f"Google API error {response.status_code}: {message}")

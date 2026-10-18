"""
WhatsApp messaging via the user's own provider account: Twilio or Meta WhatsApp Cloud API.

Each user stores credentials in API Keys (encrypted by AppStore). Sends return the
provider's message id and initial status so every delivery is logged on a receipt.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

TIMEOUT_SECONDS = 20.0
TWILIO_API = "https://api.twilio.com/2010-04-01"
GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v23.0")
GRAPH_API = f"https://graph.facebook.com/{GRAPH_VERSION}"
PROVIDERS = {"twilio": "Twilio", "meta": "Meta WhatsApp Cloud API"}

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")

# Provider error codes worth explaining in plain words.
_TWILIO_HINTS = {
    20003: "Twilio rejected the Account SID / Auth Token.",
    20429: "Twilio rate limit reached. Try again in a moment.",
    21211: "The recipient number is not valid.",
    21606: "The 'from' number is not a WhatsApp-enabled Twilio sender.",
    63007: "The 'from' number is not a WhatsApp-enabled Twilio sender.",
    63015: "This recipient has not joined your Twilio WhatsApp Sandbox (they must send 'join <code>' first).",
    63016: "Outside WhatsApp's 24-hour window: the contact must message you first, or use an approved template.",
}
_META_HINTS = {
    190: "The Meta access token is invalid or expired.",
    100: "Meta rejected a parameter (check the Phone Number ID and recipient number).",
    130429: "Meta rate limit reached. Try again in a moment.",
    131030: "This recipient is not on your Meta test number's allowed list.",
    131047: "Outside WhatsApp's 24-hour window: the contact must message you first, or use an approved template.",
}


class WhatsAppError(Exception):
    """Send or test failed; message is safe to show to the user."""


@dataclass
class SendResult:
    message_id: str
    status: str


def normalize_phone(value: str) -> str:
    """Return an E.164 number (+<country><number>) or raise WhatsAppError."""
    cleaned = re.sub(r"[\s\-().]", "", value or "")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned.split(":", 1)[1]
    if not _E164.match(cleaned):
        raise WhatsAppError(f"'{value}' is not a valid phone number. Use international format, e.g. +919876543210.")
    return cleaned


def normalize_phone_safe(value: str) -> str | None:
    """normalize_phone, but None for invalid input (for matching stored numbers)."""
    try:
        return normalize_phone(value)
    except WhatsAppError:
        return None


class WhatsAppClient:
    def __init__(self, settings: dict[str, Any], http: httpx.Client | None = None):
        if settings.get("provider") not in PROVIDERS:
            raise WhatsAppError("Unknown WhatsApp provider")
        if not settings.get("token"):
            raise WhatsAppError("WhatsApp credentials are incomplete. Update them in API Keys.")
        self.settings = settings
        self.http = http or httpx.Client(timeout=TIMEOUT_SECONDS)

    @property
    def provider(self) -> str:
        return self.settings["provider"]

    # ------------------------------------------------------------------ public API
    def test(self) -> tuple[bool, str]:
        try:
            if self.provider == "twilio":
                body = self._twilio("GET", f"/Accounts/{self.settings['account_id']}.json")
                return True, f"Twilio account '{body.get('friendly_name', 'ok')}' ({body.get('status', 'active')})"
            body = self._meta("GET", f"/{self.settings['account_id']}", params={"fields": "display_phone_number,verified_name"})
            return True, f"Meta number {body.get('display_phone_number', '')} ({body.get('verified_name', 'unverified')})"
        except WhatsAppError as exc:
            return False, str(exc)

    def send_text(self, to: str, body: str) -> SendResult:
        number = normalize_phone(to)
        if not body.strip():
            raise WhatsAppError("Message text is empty")
        if self.provider == "twilio":
            sender = normalize_phone(self.settings.get("from_number", ""))
            result = self._twilio(
                "POST",
                f"/Accounts/{self.settings['account_id']}/Messages.json",
                data={"From": f"whatsapp:{sender}", "To": f"whatsapp:{number}", "Body": body[:1600]},
            )
            return SendResult(message_id=result.get("sid", ""), status=result.get("status", "queued"))
        result = self._meta(
            "POST",
            f"/{self.settings['account_id']}/messages",
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": number.lstrip("+"),
                "type": "text",
                "text": {"preview_url": False, "body": body[:4096]},
            },
        )
        messages = result.get("messages") or [{}]
        return SendResult(message_id=messages[0].get("id", ""), status=messages[0].get("message_status", "accepted"))

    def fetch_status(self, message_id: str) -> tuple[str, str | None]:
        """Current delivery status (Twilio only; Meta reports status through webhooks)."""
        if self.provider != "twilio":
            raise WhatsAppError("Meta delivers status updates by webhook only; refresh isn't available.")
        body = self._twilio("GET", f"/Accounts/{self.settings['account_id']}/Messages/{message_id}.json")
        error = body.get("error_message") or (_TWILIO_HINTS.get(body.get("error_code") or 0) if body.get("error_code") else None)
        return body.get("status", "unknown"), error

    # ------------------------------------------------------------------ HTTP
    def _twilio(self, method: str, path: str, data: dict[str, str] | None = None) -> dict[str, Any]:
        try:
            response = self.http.request(
                method,
                f"{TWILIO_API}{path}",
                data=data,
                auth=(self.settings["account_id"], self.settings["token"]),
            )
        except httpx.HTTPError as exc:
            raise WhatsAppError(f"Could not reach Twilio: {exc}") from exc
        body = _json(response)
        if response.status_code >= 400:
            code = body.get("code")
            hint = _TWILIO_HINTS.get(code) if isinstance(code, int) else None
            raise WhatsAppError(hint or f"Twilio error {code or response.status_code}: {body.get('message', response.text[:160])}")
        return body

    def _meta(self, method: str, path: str, *, params: dict[str, str] | None = None, json: dict | None = None) -> dict[str, Any]:
        try:
            response = self.http.request(
                method,
                f"{GRAPH_API}{path}",
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {self.settings['token']}"},
            )
        except httpx.HTTPError as exc:
            raise WhatsAppError(f"Could not reach Meta: {exc}") from exc
        body = _json(response)
        if response.status_code >= 400:
            error = body.get("error") or {}
            code = error.get("code")
            hint = _META_HINTS.get(code) if isinstance(code, int) else None
            details = (error.get("error_data") or {}).get("details") or error.get("message") or response.text[:160]
            raise WhatsAppError(hint or f"Meta error {code or response.status_code}: {details}")
        return body


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}

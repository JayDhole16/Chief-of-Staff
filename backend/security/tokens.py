"""
Slot models and signed slot tokens per BACKEND_SCHEMA §3.4 and §7.8.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from backend.contracts import CompatBaseModel


class SlotTokenInvalidError(Exception):
    """Raised when slot token signature is invalid, tampered, or malformed."""
    pass


class SlotTokenExpiredError(Exception):
    """Raised when slot token 30-minute validity period has expired."""
    pass


class SlotTokenScopeMismatchError(Exception):
    """Raised when slot token was minted for another task."""
    pass


class Slot(CompatBaseModel):
    """
    Slot representation returned by find_slots.
    Implements BACKEND_SCHEMA §7.8.
    """

    label: str  # e.g. "S1"
    slot_id: str  # signed token (sl_<payload>.<sig>)
    start: datetime
    end: datetime
    display_founder: str  # "Thu 15 Oct, 3:00-3:30 PM IST"
    display_contact: str | None = None  # contact local tz when contact tz differs


def _base64url_encode(data: bytes) -> str:
    """Encode bytes into base64url string without trailing = padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    """Decode base64url string with flexible padding."""
    padding = 4 - (len(data) % 4)
    if padding and padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("ascii"))


def mint_slot_token(
    task_id: UUID | str,
    start: datetime,
    end: datetime,
    signing_key: str,
    validity_seconds: int = 1800,  # 30 minutes per BACKEND_SCHEMA §3.4
    now_epoch: int | None = None,
) -> str:
    """
    Mint signed slot token:
    sl_ + base64url(JSON {"t": task_uuid, "s": start_iso, "e": end_iso, "x": exp_epoch})
    + . + base64url(HMAC-SHA256(SLOT_SIGNING_KEY, json))
    """
    if not str(task_id).strip():
        raise ValueError("task_id must be non-empty")
    if not signing_key or not signing_key.strip():
        raise ValueError("signing_key must be non-empty")
    if end <= start:
        raise ValueError("Slot end time must be after start time")
    if validity_seconds <= 0:
        raise ValueError("validity_seconds must be positive")

    if now_epoch is None:
        now_epoch = int(time.time())

    exp_epoch = now_epoch + validity_seconds

    payload = {
        "t": str(task_id),
        "s": start.isoformat(),
        "e": end.isoformat(),
        "x": exp_epoch,
    }

    # Deterministic compact JSON (canonical keys)
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _base64url_encode(payload_json)

    sig = hmac.new(signing_key.encode("utf-8"), payload_json, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(sig)

    return f"sl_{payload_b64}.{sig_b64}"


def verify_slot_token(
    token: str,
    expected_task_id: UUID | str,
    signing_key: str,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    """
    Verify signed slot token and check:
      - format and signature (tamper protection)
      - task scope isolation (token valid only for issuing task)
      - expiry (30-minute validity)

    Returns parsed payload dict {"t": task_id, "s": start_iso, "e": end_iso, "x": exp_epoch}.
    """
    if not token or not isinstance(token, str) or not token.startswith("sl_") or "." not in token:
        raise SlotTokenInvalidError("Malformed slot token format")
    if not signing_key:
        raise SlotTokenInvalidError("Missing slot token signing key")

    token_body = token[3:]  # Strip sl_
    parts = token_body.split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise SlotTokenInvalidError("Malformed slot token structure")

    payload_b64, sig_b64 = parts[0], parts[1]

    try:
        payload_bytes = _base64url_decode(payload_b64)
        sig_bytes = _base64url_decode(sig_b64)
    except Exception as e:
        raise SlotTokenInvalidError(f"Base64 decoding failed: {e}") from e

    expected_sig = hmac.new(signing_key.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(sig_bytes, expected_sig):
        raise SlotTokenInvalidError("Slot token signature mismatch (tampered or invalid key)")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise SlotTokenInvalidError(f"JSON decode failed: {e}") from e

    if not isinstance(payload, dict) or not {"t", "s", "e", "x"}.issubset(payload.keys()):
        raise SlotTokenInvalidError("Slot token payload missing required fields")

    exp_epoch = payload.get("x")
    if not isinstance(exp_epoch, (int, float)) or isinstance(exp_epoch, bool):
        raise SlotTokenInvalidError("Slot token expiry 'x' must be numeric")

    # Check task scope isolation
    if str(payload.get("t")) != str(expected_task_id):
        raise SlotTokenScopeMismatchError(
            f"Slot token task mismatch: expected {expected_task_id}, got {payload.get('t')}"
        )

    # Check expiry
    if now_epoch is None:
        now_epoch = int(time.time())

    if now_epoch > exp_epoch:
        raise SlotTokenExpiredError(f"Slot token expired at {exp_epoch}, current time {now_epoch}")

    return payload

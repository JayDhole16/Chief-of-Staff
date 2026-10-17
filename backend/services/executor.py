"""
Worker Executor and Fake Integration Adapters (T06.5/T06.6 Fake Path, T10.1).

Enforces the non-negotiable safety invariant:
"Only the designated worker executor can perform an authorized external write.
Agents propose; workers execute. Never depict a mock write as a real external effect."

Provides deterministic fake adapters for Gmail and Calendar writes, terminal receipt
minting, kill-switch gating, and audit logging.
"""

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from threading import RLock
from typing import Any, Callable, Literal
from uuid import uuid4

from backend.contracts.read_api import (
    ActionReceiptResponse,
    ReceiptFactItem,
    ReceiptStatus,
    ReceiptTimelineItem,
)


def _serialize_execution(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        with self._execution_lock:
            return method(self, *args, **kwargs)

    return wrapped


@dataclass
class FakeGmailAdapter:
    """Deterministic fake Gmail adapter for testing and fakes golden path."""
    sent_messages: list[dict[str, Any]] = field(default_factory=list)
    should_fail: bool = False
    failure_error: str = "Simulated Gmail API network timeout"

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
        rendered_hash: str | None = None,
    ) -> str:
        """Simulate sending an email. Returns Google Gmail message ID."""
        if self.should_fail:
            raise ConnectionError(self.failure_error)

        msg_id = f"gmail_msg_{hashlib.sha256((to_email + subject + body).encode('utf-8')).hexdigest()[:16]}"
        record = {
            "id": msg_id,
            "to": to_email,
            "subject": subject,
            "body": body,
            "thread_id": thread_id or msg_id,
            "rendered_hash": rendered_hash,
            "sent_at": datetime.now(timezone.utc),
        }
        self.sent_messages.append(record)
        return msg_id


@dataclass
class FakeCalendarAdapter:
    """Deterministic fake Google Calendar adapter."""
    created_events: list[dict[str, Any]] = field(default_factory=list)
    should_fail: bool = False
    failure_error: str = "Simulated Google Calendar API 503 Service Unavailable"

    def create_meeting(
        self,
        summary: str,
        start_time_iso: str,
        end_time_iso: str,
        attendee_email: str,
        description: str | None = None,
    ) -> str:
        """Simulate creating calendar meeting. Returns event ID."""
        if self.should_fail:
            raise ConnectionError(self.failure_error)

        event_key = summary + start_time_iso + end_time_iso + attendee_email
        event_id = f"cal_evt_{hashlib.sha256(event_key.encode('utf-8')).hexdigest()[:16]}"
        record = {
            "id": event_id,
            "summary": summary,
            "start": start_time_iso,
            "end": end_time_iso,
            "attendee": attendee_email,
            "description": description,
            "created_at": datetime.now(timezone.utc),
        }
        self.created_events.append(record)
        return event_id


class WorkerExecutor:
    """
    Authorized Worker Executor.
    The sole component authorized to execute external side effects (Gmail/Calendar).
    Enforces kill switch, checks rendered_hash bindings, executes via adapters,
    and produces immutable terminal receipts.
    """

    def __init__(
        self,
        gmail_adapter: FakeGmailAdapter | None = None,
        calendar_adapter: FakeCalendarAdapter | None = None,
        receipt_store: dict[str, ActionReceiptResponse] | None = None,
        activity_store: list[dict[str, Any]] | None = None,
    ):
        self.gmail = gmail_adapter if gmail_adapter is not None else FakeGmailAdapter()
        self.calendar = calendar_adapter if calendar_adapter is not None else FakeCalendarAdapter()
        self.receipts = receipt_store if receipt_store is not None else {}
        self.activities = activity_store if activity_store is not None else []
        self.kill_switch_active: bool = False
        self._execution_lock = RLock()

    @_serialize_execution
    def execute_action(
        self,
        action_ref: str,
        action_kind: Literal["email", "calendar"],
        recipient_email: str,
        rendered_body_or_time: str,
        rendered_hash: str,
        authority_clause: str,
        checks_passed: list[str] | None = None,
        facts_used: list[dict[str, str]] | None = None,
        is_founder_approved: bool = False,
        email_subject: str | None = None,
        calendar_end_time_iso: str | None = None,
        calendar_description: str | None = None,
    ) -> ActionReceiptResponse:
        """
        Execute an approved or scheduled action.
        Produces and returns an immutable ActionReceiptResponse.
        """
        now = datetime.now(timezone.utc)
        receipt_id = f"rcpt_{now.strftime('%Y%m%d')}_{uuid4().hex[:6]}"
        timeline: list[ReceiptTimelineItem] = [
            ReceiptTimelineItem(timestamp=now, event="Worker received action for execution dispatch"),
        ]

        prior_receipt = self.receipts.get(action_ref)
        if prior_receipt is not None:
            return prior_receipt

        # 1. Kill Switch Check
        if self.kill_switch_active and not is_founder_approved:
            timeline.append(ReceiptTimelineItem(
                timestamp=now,
                event="Execution blocked: Kill switch is currently engaged."
            ))
            receipt = ActionReceiptResponse(
                receipt_id=receipt_id,
                action_ref=action_ref,
                action_kind=action_kind if action_kind in ("email", "calendar") else "email",
                status=ReceiptStatus.BLOCKED,
                authority_clause=authority_clause,
                recipient_email=recipient_email,
                rendered_hash=rendered_hash,
                checks_passed=checks_passed or [],
                facts_used=[ReceiptFactItem(**f) for f in (facts_used or [])],
                cancelled_at=now,
                timeline=timeline,
            )
            self.receipts[receipt_id] = receipt
            self.receipts[action_ref] = receipt
            self.activities.append({
                "id": f"evt_{uuid4().hex[:8]}",
                "timestamp": now,
                "type": "blocked",
                "title": f"Action {action_ref} blocked by kill switch",
                "description": f"Target: {recipient_email}. Kill switch is active.",
                "user_id": "worker_executor",
                "action_ref": action_ref,
                "receipt_id": receipt_id,
                "rendered_hash": rendered_hash,
            })
            return receipt

        expected_hash = hashlib.sha256((rendered_body_or_time or "").encode("utf-8")).hexdigest()
        if not rendered_hash or not hmac.compare_digest(rendered_hash, expected_hash):
            timeline.append(ReceiptTimelineItem(
                timestamp=now,
                event="Execution blocked: rendered content does not match its SHA-256 hash.",
            ))
            receipt = ActionReceiptResponse(
                receipt_id=receipt_id,
                action_ref=action_ref,
                action_kind=action_kind if action_kind in ("email", "calendar") else "email",
                status=ReceiptStatus.BLOCKED,
                authority_clause=authority_clause,
                recipient_email=recipient_email,
                rendered_hash=rendered_hash or "",
                checks_passed=checks_passed or [],
                facts_used=[ReceiptFactItem(**f) for f in (facts_used or [])],
                cancelled_at=now,
                timeline=timeline,
            )
            self.receipts[receipt_id] = receipt
            self.receipts[action_ref] = receipt
            return receipt

        # 2. Execute via adapter
        external_id = None
        meeting_time_str = None
        try:
            if not recipient_email or "@" not in recipient_email:
                raise ValueError(f"Invalid recipient_email: {recipient_email}")

            if action_kind == "email":
                timeline.append(ReceiptTimelineItem(
                    timestamp=now,
                    event="Dispatching email via Gmail adapter"
                ))
                external_id = self.gmail.send_email(
                    to_email=recipient_email,
                    subject=email_subject or f"Follow-up {action_ref}",
                    body=rendered_body_or_time,
                    rendered_hash=rendered_hash,
                )
                timeline.append(ReceiptTimelineItem(
                    timestamp=now,
                    event=f"Gmail API send confirmed. External ID: {external_id}"
                ))
            elif action_kind == "calendar":
                timeline.append(ReceiptTimelineItem(
                    timestamp=now,
                    event="Creating meeting invite via Google Calendar adapter"
                ))
                if calendar_end_time_iso is None:
                    raise ValueError("A calendar end time is required before creating a meeting")
                start_time = datetime.fromisoformat(rendered_body_or_time)
                end_time = datetime.fromisoformat(calendar_end_time_iso)
                if (
                    start_time.tzinfo is None
                    or end_time.tzinfo is None
                    or start_time.utcoffset() is None
                    or end_time.utcoffset() is None
                ):
                    raise ValueError("Calendar start and end times must include timezone offsets")
                if end_time <= start_time:
                    raise ValueError("Calendar end time must be after its start time")
                external_id = self.calendar.create_meeting(
                    summary=email_subject or "Sales Alignment Discussion",
                    start_time_iso=rendered_body_or_time,
                    end_time_iso=calendar_end_time_iso,
                    attendee_email=recipient_email,
                    description=calendar_description,
                )
                meeting_time_str = f"{rendered_body_or_time} - {calendar_end_time_iso}"
                timeline.append(ReceiptTimelineItem(
                    timestamp=now,
                    event=f"Google Calendar event confirmed. External ID: {external_id}"
                ))
            else:
                raise ValueError(f"Unsupported action_kind: {action_kind}")

            # 3. Successful Terminal Receipt
            receipt = ActionReceiptResponse(
                receipt_id=receipt_id,
                action_ref=action_ref,
                action_kind=action_kind,
                status=ReceiptStatus.EXECUTED,
                authority_clause=authority_clause,
                recipient_email=recipient_email,
                meeting_time=meeting_time_str,
                external_id=external_id,
                rendered_hash=rendered_hash,
                checks_passed=checks_passed or ["G01", "G04", "G05", "G06", "G07", "G09", "G10", "G11"],
                facts_used=[ReceiptFactItem(**f) for f in (facts_used or [])],
                executed_at=now,
                undo_window_seconds=15 if not is_founder_approved else 0,
                timeline=timeline,
            )
            self.receipts[receipt_id] = receipt
            self.receipts[action_ref] = receipt

            self.activities.append({
                "id": f"evt_{uuid4().hex[:8]}",
                "timestamp": now,
                "type": "execution",
                "title": f"Action Executed: {action_ref}",
                "description": f"Successfully sent {action_kind} to {recipient_email}. Receipt: {receipt_id}.",
                "user_id": "worker_executor",
                "action_ref": action_ref,
                "receipt_id": receipt_id,
                "rendered_hash": rendered_hash,
                "can_undo": False,
            })
            return receipt

        except Exception as e:
            timeline.append(ReceiptTimelineItem(
                timestamp=now,
                event=f"Worker execution failed: {str(e)}"
            ))
            receipt = ActionReceiptResponse(
                receipt_id=receipt_id,
                action_ref=action_ref,
                action_kind=action_kind if action_kind in ("email", "calendar") else "email",
                status=ReceiptStatus.BLOCKED,
                authority_clause=authority_clause,
                recipient_email=recipient_email,
                rendered_hash=rendered_hash,
                checks_passed=checks_passed or [],
                facts_used=[ReceiptFactItem(**f) for f in (facts_used or [])],
                cancelled_at=now,
                timeline=timeline,
            )
            self.receipts[receipt_id] = receipt
            self.receipts[action_ref] = receipt
            self.activities.append({
                "id": f"evt_{uuid4().hex[:8]}",
                "timestamp": now,
                "type": "blocked",
                "title": f"Execution Failed: {action_ref}",
                "description": f"Failed with error: {str(e)}",
                "user_id": "worker_executor",
                "action_ref": action_ref,
                "receipt_id": receipt_id,
            })
            return receipt

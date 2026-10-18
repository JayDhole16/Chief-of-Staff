"""
Chat agent tools: contact lookup, email, WhatsApp and Google Calendar.

Read tools (find_contacts, list_calendar_events) run immediately. Every write tool
creates a hash-bound *pending action* instead of acting: the user confirms the exact
recipient, content and time in the chat (or in Approvals) before anything is sent,
booked, changed or deleted. Tool problems are returned to the model as readable
errors so the conversation never breaks.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

from backend.services import google, whatsapp
from backend.services.app_store import AppStore, iso, utcnow

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CONFIRM_NOTE = "Pending: the user must confirm this in the chat before it happens. Tell them what you prepared and ask them to confirm."

TOOLS: list[dict[str, Any]] = [
    {
        "name": "find_contacts",
        "description": (
            "Search the user's deals/contacts by name, company, email or phone. Use this to look up "
            "email addresses and phone numbers. Never guess contact details. Empty query lists recent contacts."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Name, company, email or phone fragment"}},
            "required": [],
        },
    },
    {
        "name": "draft_email",
        "description": (
            "Prepare an email for the user to confirm (it is NOT sent until they confirm). "
            "'to' may be an email address or a contact name from find_contacts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address or contact name"},
                "subject": {"type": "string"},
                "body": {"type": "string", "description": "Plain-text email body ending with the user's signature"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "send_whatsapp",
        "description": (
            "Prepare a WhatsApp text message for the user to confirm (NOT sent until confirmed). "
            "'to' may be a phone number in international format or a contact name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Phone like +919876543210, or a contact name"},
                "message": {"type": "string"},
            },
            "required": ["to", "message"],
        },
    },
    {
        "name": "list_calendar_events",
        "description": "List events on the user's Google Calendar between two local date-times (inclusive).",
        "parameters": {
            "type": "object",
            "properties": {
                "start": {"type": "string", "description": "Local date-time, e.g. 2026-10-20T00:00"},
                "end": {"type": "string", "description": "Local date-time, e.g. 2026-10-20T23:59"},
            },
            "required": ["start", "end"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": (
            "Prepare a Google Calendar event (meeting) for the user to confirm. Attendees may be emails "
            "or contact names; they get invitations once confirmed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start": {"type": "string", "description": "Local start date-time, e.g. 2026-10-20T15:00"},
                "duration_minutes": {"type": "integer", "description": "Default 30"},
                "attendees": {"type": "array", "items": {"type": "string"}, "description": "Emails or contact names"},
                "description": {"type": "string"},
                "reminder_minutes": {"type": "integer", "description": "Pop-up reminder minutes before start"},
                "add_meet_link": {"type": "boolean", "description": "Add a Google Meet link (default true when there are attendees)"},
            },
            "required": ["title", "start"],
        },
    },
    {
        "name": "set_reminder",
        "description": (
            "Prepare a personal reminder on the user's Google Calendar (no attendees) for the user to confirm, "
            "e.g. 'remind me to check in with the client tomorrow at 3 PM'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "at": {"type": "string", "description": "Local date-time, e.g. 2026-10-20T15:00"},
                "minutes_before": {"type": "integer", "description": "Pop-up this many minutes before (default 10)"},
                "notes": {"type": "string"},
            },
            "required": ["title", "at"],
        },
    },
    {
        "name": "update_calendar_event",
        "description": "Prepare a change to an existing Google Calendar event (use an id from list_calendar_events).",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string"},
                "title": {"type": "string"},
                "start": {"type": "string", "description": "New local start date-time"},
                "duration_minutes": {"type": "integer", "description": "New duration; keeps the old one if omitted"},
                "description": {"type": "string"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "delete_calendar_event",
        "description": "Prepare deletion of a Google Calendar event (use an id from list_calendar_events).",
        "parameters": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
            "required": ["event_id"],
        },
    },
]


class ToolError(Exception):
    """Expected problem to report back to the model (bad input, missing setup...)."""


def user_zone(user: dict[str, Any]) -> ZoneInfo:
    try:
        return ZoneInfo(user.get("timezone") or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def parse_local(value: str, zone: ZoneInfo) -> datetime:
    """Parse a local (or offset-qualified) ISO date-time into an aware UTC datetime."""
    text = (value or "").strip().replace("Z", "+00:00")
    if len(text) == 10:  # date only
        text += "T09:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ToolError(f"'{value}' is not a date-time. Use the format YYYY-MM-DDTHH:MM.") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zone)
    return dt.astimezone(timezone.utc)


def local_label(dt_utc: datetime, zone: ZoneInfo) -> str:
    return dt_utc.astimezone(zone).strftime("%a %d %b %Y, %H:%M") + f" ({zone.key})"


class AgentToolbox:
    def __init__(
        self,
        *,
        store: AppStore,
        user: dict[str, Any],
        google_session: Callable[[str], tuple[google.GoogleClient, str, dict[str, Any]]],
        run_guards: Callable[..., dict[str, Any]],
        content_hash: Callable[[str, str, dict[str, Any] | None, str], str],
    ):
        self.store = store
        self.user = user
        self.zone = user_zone(user)
        self._google_session = google_session
        self._run_guards = run_guards
        self._content_hash = content_hash
        self.actions: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ dispatch
    def handle(self, name: str, args: dict[str, Any]) -> tuple[Any, bool]:
        method = getattr(self, f"tool_{name}", None)
        if method is None:
            return {"error": f"Unknown tool '{name}'"}, True
        try:
            return method(**{k: v for k, v in args.items() if v is not None}), False
        except ToolError as exc:
            return {"error": str(exc)}, True
        except HTTPException as exc:
            return {"error": str(exc.detail)}, True
        except (google.GoogleError, whatsapp.WhatsAppError) as exc:
            return {"error": str(exc)}, True
        except TypeError as exc:  # wrong/missing arguments from the model
            return {"error": f"Invalid arguments for {name}: {exc}"}, True

    # ------------------------------------------------------------------ helpers
    def _contacts(self, query: str = "") -> list[dict[str, Any]]:
        q = query.strip().lower()
        deals = self.store.list_deals(self.user["id"])
        if q:
            digits = re.sub(r"\D", "", q)
            deals = [
                d
                for d in deals
                if q in d["contact_name"].lower()
                or q in d["company"].lower()
                or q in (d["contact_email"] or "").lower()
                or (digits and len(digits) >= 4 and digits in re.sub(r"\D", "", d.get("contact_phone") or ""))
            ]
        return deals

    def _resolve_one(self, who: str, need: str) -> tuple[dict[str, Any] | None, str]:
        """Resolve a name or address to (deal or None, address). ``need`` is 'email' or 'phone'."""
        who = (who or "").strip()
        if not who:
            raise ToolError("Recipient is empty")
        if need == "email" and "@" in who:
            if not EMAIL_RE.match(who):
                raise ToolError(f"'{who}' is not a valid email address")
            match = next((d for d in self.store.list_deals(self.user["id"]) if (d["contact_email"] or "").lower() == who.lower()), None)
            return match, who.lower()
        if need == "phone" and re.search(r"\d{6,}", re.sub(r"[\s\-()]", "", who)):
            number = whatsapp.normalize_phone(who)
            match = next(
                (
                    d
                    for d in self.store.list_deals(self.user["id"])
                    if whatsapp.normalize_phone_safe(d.get("contact_phone") or "") == number
                ),
                None,
            )
            return match, number
        matches = self._contacts(who)
        if not matches:
            raise ToolError(f"No contact matches '{who}'. Ask the user for the {need} or add the contact as a deal.")
        if len(matches) > 1:
            names = "; ".join(f"{d['contact_name']} ({d['company']})" for d in matches[:5])
            raise ToolError(f"'{who}' matches several contacts: {names}. Ask the user which one.")
        deal = matches[0]
        if deal["do_not_contact"]:
            raise ToolError(f"{deal['contact_name']} is marked do-not-contact (G12). Do not message them.")
        address = deal["contact_email"] if need == "email" else deal.get("contact_phone")
        if not address:
            raise ToolError(f"{deal['contact_name']} has no {need} on file. Ask the user for it or update the deal.")
        if need == "phone":
            address = whatsapp.normalize_phone(address)
        return deal, address

    def _create_action(
        self,
        *,
        kind: str,
        deal: dict[str, Any] | None,
        contact_name: str,
        recipient: str,
        subject: str,
        body: str,
        payload: dict[str, Any] | None,
        guard_contact_verified: bool | None = None,
        extra_reasons: list[str] | None = None,
        facts: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        guard_deal = deal or {"contact_name": contact_name, "contact_email": recipient if "@" in recipient else "", "value_inr": 0, "do_not_contact": False}
        guard = self._run_guards(user=self.user, deal=guard_deal, subject=subject, body=body, contact_verified=guard_contact_verified)
        verdict, reasons = guard["verdict"], list(guard["reasons"]) + list(extra_reasons or [])
        if extra_reasons and verdict == "ALLOW":
            verdict = "ASK"
        proposal = self.store.create_proposal(
            self.user["id"],
            {
                "deal_id": deal["id"] if deal else None,
                "kind": kind,
                "deal_title": f"{deal['company']} · {deal['title']}" if deal else "Chat request",
                "contact_name": contact_name,
                "contact_email": recipient,
                "subject": subject,
                "rendered_body": body,
                "rendered_hash": self._content_hash(kind, body, payload, recipient),
                "policy_verdict": verdict,
                "policy_reasons": reasons,
                "guards_checked": guard["guards_checked"],
                "facts_used": facts or [],
                "status": "blocked" if verdict == "BLOCK" else "pending",
                "payload": payload,
            },
        )
        self.store.add_activity(
            self.user["id"],
            type="proposed",
            title=f"Agent prepared {kind.replace('_', ' ')}: {subject}"[:200],
            description=f"For {contact_name} · verdict {verdict}",
            action_ref=proposal["ref"],
            deal_id=deal["id"] if deal else None,
        )
        self.actions.append(proposal)
        summary = {
            "action_ref": proposal["ref"],
            "status": proposal["status"],
            "policy_verdict": verdict,
            "kind": kind,
            "recipient": recipient,
            "subject": subject,
            "note": CONFIRM_NOTE if proposal["status"] == "pending" else "Blocked by policy guards; tell the user why.",
        }
        if reasons:
            summary["guard_findings"] = reasons
        return summary

    def _google(self) -> tuple[google.GoogleClient, str, dict[str, Any]]:
        try:
            return self._google_session(self.user["id"])
        except HTTPException as exc:
            raise ToolError(f"{exc.detail} The user can connect Google in API Keys.") from exc

    # ------------------------------------------------------------------ tools
    def tool_find_contacts(self, query: str = "") -> dict[str, Any]:
        deals = self._contacts(query)[:10]
        return {
            "count": len(deals),
            "contacts": [
                {
                    "deal_id": d["id"],
                    "name": d["contact_name"],
                    "company": d["company"],
                    "email": d["contact_email"] or None,
                    "phone": d.get("contact_phone") or None,
                    "deal": d["title"],
                    "stage": d["stage"],
                    "value_inr": d["value_inr"],
                    "days_since_contact": d["days_quiet"],
                    "do_not_contact": d["do_not_contact"],
                }
                for d in deals
            ],
        }

    def tool_draft_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        if not subject.strip() or not body.strip():
            raise ToolError("Subject and body are required")
        deal, address = self._resolve_one(to, "email")
        if deal and deal["do_not_contact"]:
            raise ToolError(f"{deal['contact_name']} is marked do-not-contact (G12).")
        name = deal["contact_name"] if deal else address
        return self._create_action(kind="email", deal=deal, contact_name=name, recipient=address, subject=subject.strip()[:300], body=body.strip(), payload=None)

    def tool_send_whatsapp(self, to: str, message: str) -> dict[str, Any]:
        if not message.strip():
            raise ToolError("Message text is empty")
        if self.store.get_whatsapp_settings(self.user["id"]) is None:
            raise ToolError("WhatsApp is not set up. The user can add Twilio or Meta credentials in API Keys.")
        deal, number = self._resolve_one(to, "phone")
        name = deal["contact_name"] if deal else number
        return self._create_action(
            kind="whatsapp",
            deal=deal,
            contact_name=name,
            recipient=number,
            subject=f"WhatsApp to {name}",
            body=message.strip()[:1600],
            payload={"to": number},
            guard_contact_verified=True,
        )

    def tool_list_calendar_events(self, start: str, end: str) -> dict[str, Any]:
        start_utc, end_utc = parse_local(start, self.zone), parse_local(end, self.zone)
        if end_utc <= start_utc:
            end_utc = start_utc + timedelta(days=1)
        client, token, _ = self._google()
        events = client.list_events(token, time_min=iso(start_utc), time_max=iso(end_utc))
        out = []
        for e in events:
            s, en = e.get("start", {}), e.get("end", {})
            out.append(
                {
                    "event_id": e.get("id"),
                    "title": e.get("summary") or "(no title)",
                    "start": _event_time_label(s, self.zone),
                    "end": _event_time_label(en, self.zone),
                    "attendees": [a.get("email") for a in e.get("attendees", []) if a.get("email")],
                    "meet_link": e.get("hangoutLink"),
                }
            )
        return {"timezone": self.zone.key, "count": len(out), "events": out}

    def tool_create_calendar_event(
        self,
        title: str,
        start: str,
        duration_minutes: int = 30,
        attendees: list[str] | None = None,
        description: str = "",
        reminder_minutes: int | None = None,
        add_meet_link: bool | None = None,
    ) -> dict[str, Any]:
        start_utc = parse_local(start, self.zone)
        if start_utc <= utcnow():
            raise ToolError(f"{local_label(start_utc, self.zone)} is in the past. Ask the user for a future time.")
        duration = max(5, min(int(duration_minutes or 30), 24 * 60))
        end_utc = start_utc + timedelta(minutes=duration)
        emails, names, deal = [], [], None
        for who in attendees or []:
            d, address = self._resolve_one(who, "email")
            emails.append(address)
            names.append(d["contact_name"] if d else address)
            deal = deal or d
        client, token, account = self._google()
        busy = client.list_events(token, time_min=iso(start_utc), time_max=iso(end_utc))
        conflicts = [f"Overlaps '{e.get('summary') or 'busy'}' on your calendar" for e in busy[:3]]
        with_meet = bool(emails) if add_meet_link is None else bool(add_meet_link)
        payload = {
            "start_utc": iso(start_utc),
            "end_utc": iso(end_utc),
            "duration_minutes": duration,
            "timezone": self.zone.key,
            "with_meet": with_meet,
            "organizer": account["email"],
            "attendees": emails,
            "reminder_minutes": reminder_minutes,
        }
        body = description.strip() or (f"Meeting with {', '.join(names)}." if names else title)
        return self._create_action(
            kind="calendar",
            deal=deal,
            contact_name=", ".join(names) or "Just you",
            recipient=emails[0] if emails else "",
            subject=title.strip()[:200],
            body=body,
            payload=payload,
            guard_contact_verified=True,
            extra_reasons=conflicts,
            facts=[
                {"label": "When", "value": local_label(start_utc, self.zone), "source": "agent:parsed"},
                {"label": "Duration", "value": f"{duration} min", "source": "agent:parsed"},
                {"label": "Calendar", "value": account["email"], "source": "google:calendar"},
            ],
        ) | {"when": local_label(start_utc, self.zone)}

    def tool_set_reminder(self, title: str, at: str, minutes_before: int = 10, notes: str = "") -> dict[str, Any]:
        return self.tool_create_calendar_event(
            title=title,
            start=at,
            duration_minutes=15,
            attendees=[],
            description=notes or f"Reminder: {title}",
            reminder_minutes=max(0, int(minutes_before)),
            add_meet_link=False,
        )

    def tool_update_calendar_event(
        self,
        event_id: str,
        title: str | None = None,
        start: str | None = None,
        duration_minutes: int | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        client, token, _ = self._google()
        current = client.get_event(token, event_id)
        changes: dict[str, Any] = {}
        before = {
            "title": current.get("summary"),
            "start": _event_time_label(current.get("start", {}), self.zone),
            "end": _event_time_label(current.get("end", {}), self.zone),
        }
        if title:
            changes["summary"] = title.strip()[:200]
        if description is not None:
            changes["description"] = description
        if start or duration_minutes:
            old_start = _event_dt(current.get("start", {}))
            old_end = _event_dt(current.get("end", {}))
            new_start = parse_local(start, self.zone) if start else old_start
            if new_start is None:
                raise ToolError("This event has no start time to keep; give a new start.")
            length = timedelta(minutes=int(duration_minutes)) if duration_minutes else ((old_end - old_start) if old_start and old_end else timedelta(minutes=30))
            new_end = new_start + length
            changes["start"] = {"dateTime": iso(new_start), "timeZone": self.zone.key}
            changes["end"] = {"dateTime": iso(new_end), "timeZone": self.zone.key}
        if not changes:
            raise ToolError("Nothing to change. Say what to update (title, start, duration or description).")
        after = {
            "title": changes.get("summary", before["title"]),
            "start": local_label(parse_local(changes["start"]["dateTime"], self.zone), self.zone) if "start" in changes else before["start"],
        }
        payload = {"event_id": event_id, "changes": changes, "before": before}
        attendees = [a.get("email") for a in current.get("attendees", []) if a.get("email")]
        return self._create_action(
            kind="calendar_update",
            deal=None,
            contact_name=", ".join(attendees) or "Just you",
            recipient=attendees[0] if attendees else "",
            subject=f"Update '{before['title'] or 'event'}'",
            body=f"From: {before['title']} · {before['start']}\nTo:   {after['title']} · {after['start']}",
            payload=payload,
            guard_contact_verified=True,
        )

    def tool_delete_calendar_event(self, event_id: str) -> dict[str, Any]:
        client, token, _ = self._google()
        current = client.get_event(token, event_id)
        title = current.get("summary") or "(no title)"
        when = _event_time_label(current.get("start", {}), self.zone)
        attendees = [a.get("email") for a in current.get("attendees", []) if a.get("email")]
        return self._create_action(
            kind="calendar_delete",
            deal=None,
            contact_name=", ".join(attendees) or "Just you",
            recipient=attendees[0] if attendees else "",
            subject=f"Delete '{title}'",
            body=f"Delete the event '{title}' on {when}." + (f" Attendees will be notified: {', '.join(attendees)}." if attendees else ""),
            payload={"event_id": event_id, "title": title, "when": when},
            guard_contact_verified=True,
        )


def _event_dt(part: dict[str, Any]) -> datetime | None:
    value = part.get("dateTime")
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _event_time_label(part: dict[str, Any], zone: ZoneInfo) -> str:
    dt = _event_dt(part)
    if dt is not None:
        return local_label(dt.astimezone(timezone.utc), zone)
    return f"{part.get('date', '?')} (all day)"

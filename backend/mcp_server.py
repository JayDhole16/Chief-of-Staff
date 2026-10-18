"""
Chief-of-Staff MCP server (Model Context Protocol, stdio transport).

Exposes the same agent tools as the in-app chat (contact lookup, email, WhatsApp,
Google Calendar) to any MCP client such as Claude Desktop or Cursor. It is a thin
client of the Chief-of-Staff API, signed in as one user:

- read tools return data directly;
- write tools only PREPARE actions; nothing is sent, booked or deleted until the
  user confirms it in the Chief-of-Staff app (Approvals page or chat). There is
  deliberately no confirm tool here.

Configuration (environment variables):
    COS_API_URL    API base URL (default http://localhost:8000)
    COS_EMAIL      account email      } or COS_SESSION_TOKEN
    COS_PASSWORD   account password   }

Run:  python -m backend.mcp_server
Claude Desktop config (claude_desktop_config.json):
    {"mcpServers": {"chief-of-staff": {"command": "python", "args": ["-m", "backend.mcp_server"],
      "cwd": "<repo path>", "env": {"COS_API_URL": "...", "COS_EMAIL": "...", "COS_PASSWORD": "..."}}}}
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.getenv("COS_API_URL", "http://localhost:8000").rstrip("/")

mcp = FastMCP(
    "chief-of-staff",
    instructions=(
        "Tools for a founder's AI chief of staff. Look up contacts with find_contacts before "
        "messaging anyone; never invent emails or phone numbers. Write tools only prepare actions: "
        "tell the user to confirm them in the Chief-of-Staff app. Times are local to the user's "
        "profile timezone, formatted like 2026-10-20T15:00."
    ),
)

_session: dict[str, str] = {}


def _token() -> str:
    if "token" in _session:
        return _session["token"]
    token = os.getenv("COS_SESSION_TOKEN", "").strip()
    if not token:
        email, password = os.getenv("COS_EMAIL", ""), os.getenv("COS_PASSWORD", "")
        if not email or not password:
            raise RuntimeError("Set COS_EMAIL and COS_PASSWORD (or COS_SESSION_TOKEN) for the MCP server")
        res = httpx.post(f"{API_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
        if res.status_code != 200:
            raise RuntimeError(f"Chief-of-Staff login failed ({res.status_code}): {res.text[:200]}")
        token = res.json()["session_id"]
    _session["token"] = token
    return token


def _call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    args = {k: v for k, v in arguments.items() if v is not None}
    for attempt in (1, 2):
        res = httpx.post(
            f"{API_URL}/api/agent/tools/{name}",
            json={"arguments": args},
            headers={"X-Session-ID": _token()},
            timeout=120,
        )
        if res.status_code == 401 and attempt == 1 and not os.getenv("COS_SESSION_TOKEN"):
            _session.pop("token", None)  # session expired: log in again once
            continue
        break
    if res.status_code != 200:
        return {"ok": False, "error": res.json().get("detail", res.text[:200]) if res.headers.get("content-type", "").startswith("application/json") else res.text[:200]}
    body = res.json()
    out: dict[str, Any] = {"ok": body["ok"], "result": body["result"]}
    if body.get("actions"):
        out["next_step"] = "Ask the user to confirm the prepared action in the Chief-of-Staff app (Approvals)."
    return out


@mcp.tool()
def find_contacts(query: str = "") -> dict[str, Any]:
    """Search the user's deals/contacts by name, company, email or phone (empty query lists recent ones)."""
    return _call("find_contacts", {"query": query})


@mcp.tool()
def draft_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Prepare an email (email address or contact name) for the user to confirm in the app. Not sent until confirmed."""
    return _call("draft_email", {"to": to, "subject": subject, "body": body})


@mcp.tool()
def send_whatsapp(to: str, message: str) -> dict[str, Any]:
    """Prepare a WhatsApp message (phone in international format or contact name) for the user to confirm."""
    return _call("send_whatsapp", {"to": to, "message": message})


@mcp.tool()
def list_calendar_events(start: str, end: str) -> dict[str, Any]:
    """List Google Calendar events between two local date-times, e.g. 2026-10-20T00:00 and 2026-10-20T23:59."""
    return _call("list_calendar_events", {"start": start, "end": end})


@mcp.tool()
def create_calendar_event(
    title: str,
    start: str,
    duration_minutes: int = 30,
    attendees: list[str] | None = None,
    description: str = "",
    reminder_minutes: int | None = None,
    add_meet_link: bool | None = None,
) -> dict[str, Any]:
    """Prepare a Google Calendar event (attendees as emails or contact names) for the user to confirm."""
    return _call(
        "create_calendar_event",
        {
            "title": title,
            "start": start,
            "duration_minutes": duration_minutes,
            "attendees": attendees or [],
            "description": description,
            "reminder_minutes": reminder_minutes,
            "add_meet_link": add_meet_link,
        },
    )


@mcp.tool()
def set_reminder(title: str, at: str, minutes_before: int = 10, notes: str = "") -> dict[str, Any]:
    """Prepare a personal calendar reminder (no attendees) at a local date-time for the user to confirm."""
    return _call("set_reminder", {"title": title, "at": at, "minutes_before": minutes_before, "notes": notes})


@mcp.tool()
def update_calendar_event(
    event_id: str,
    title: str | None = None,
    start: str | None = None,
    duration_minutes: int | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Prepare a change to an existing calendar event (id from list_calendar_events) for the user to confirm."""
    return _call(
        "update_calendar_event",
        {"event_id": event_id, "title": title, "start": start, "duration_minutes": duration_minutes, "description": description},
    )


@mcp.tool()
def delete_calendar_event(event_id: str) -> dict[str, Any]:
    """Prepare deletion of a calendar event (id from list_calendar_events) for the user to confirm."""
    return _call("delete_calendar_event", {"event_id": event_id})


@mcp.tool()
def list_pending_actions() -> dict[str, Any]:
    """List actions waiting for the user's confirmation in the app."""
    res = httpx.get(f"{API_URL}/api/approvals", params={"status": "pending"}, headers={"X-Session-ID": _token()}, timeout=30)
    if res.status_code != 200:
        return {"ok": False, "error": res.text[:200]}
    return {
        "ok": True,
        "pending": [
            {"ref": a["ref"], "kind": a["kind"], "subject": a["subject"], "recipient": a["contact_name"], "verdict": a["policy_verdict"]}
            for a in res.json()["approvals"]
        ],
    }


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()

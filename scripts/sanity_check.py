"""End-to-end sanity check of a running Chief-of-Staff API.

Registers a throwaway user, exercises every endpoint group with expected status
codes, reports any 5xx or mismatch, and deletes the user afterwards. No AI or
SMTP credentials are needed: provider calls use deliberately invalid keys and
must fail *gracefully* (handled 4xx/ok=false, never 5xx).

Usage:
    python scripts/sanity_check.py                          # http://localhost:8000
    python scripts/sanity_check.py https://chief-of-staff-eight-sigma.vercel.app
"""

from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
results: list[tuple[str, bool, str]] = []


def check(name: str, response: httpx.Response, expected: int | tuple[int, ...], note: str = "") -> httpx.Response:
    allowed = (expected,) if isinstance(expected, int) else expected
    ok = response.status_code in allowed
    detail = f"{response.status_code} in {response.elapsed.total_seconds():.2f}s"
    if not ok:
        detail += f" (expected {allowed}) {response.text[:160]}"
    results.append((name, ok, f"{detail} {note}".strip()))
    return response


def main() -> int:
    email = f"sanity+{uuid.uuid4().hex[:8]}@example.com"
    password = "sanity-check-password-1"
    client = httpx.Client(base_url=BASE, timeout=120)
    started = time.time()

    check("GET /healthz", client.get("/healthz"), 200)
    check("GET /readyz (database)", client.get("/readyz"), 200)
    check("GET /docs", client.get("/docs"), 200)
    check("unauthenticated request rejected", client.get("/api/deals"), 401)

    r = check("POST /api/auth/register", client.post("/api/auth/register", json={"name": "Sanity", "email": email, "password": password}), 201)
    token = r.json().get("session_id", "")
    h = {"X-Session-ID": token}
    check("duplicate register rejected", client.post("/api/auth/register", json={"name": "x", "email": email, "password": password}), 409)
    check("wrong password rejected", client.post("/api/auth/login", json={"email": email, "password": "nope-nope-1"}), 401)
    check("POST /api/auth/login", client.post("/api/auth/login", json={"email": email, "password": password}), 200)
    check("GET /api/session", client.get("/api/session", headers=h), 200)
    check("GET /api/profile", client.get("/api/profile", headers=h), 200)
    check("PUT /api/profile", client.put("/api/profile", headers=h, json={"business_name": "Sanity Labs", "max_discount_pct": 7}), 200)
    check("invalid profile rejected", client.put("/api/profile", headers=h, json={"max_discount_pct": 900}), 422)

    deal = check(
        "POST /api/deals",
        client.post("/api/deals", headers=h, json={
            "company": "Sanity Co", "title": "Check", "contact_name": "Tess",
            "contact_email": "tess@example.com", "stage": "negotiating", "value_inr": 150000,
            "last_contact_at": (datetime.now(timezone.utc) - timedelta(days=9)).isoformat(),
        }),
        201,
    ).json()
    check("invalid deal email rejected", client.post("/api/deals", headers=h, json={"company": "a", "title": "b", "contact_name": "c", "contact_email": "bad"}), 422)
    check("GET /api/deals", client.get("/api/deals", headers=h), 200)
    check("GET /api/deals/{id}", client.get(f"/api/deals/{deal['id']}", headers=h), 200)
    check("PUT /api/deals/{id}", client.put(f"/api/deals/{deal['id']}", headers=h, json={"stage": "proposal_sent"}), 200)
    check("draft without AI key -> 409", client.post(f"/api/deals/{deal['id']}/draft-followup", headers=h, json={}), 409)
    check("sweep without AI key -> 409", client.post("/api/sweep", headers=h), 409)
    check("chat without AI key -> 409", client.post("/api/chat", headers=h, json={"message": "hi"}), 409)

    check("GET /api/settings/api-keys", client.get("/api/settings/api-keys", headers=h), 200)
    check("PUT api key (openai)", client.put("/api/settings/api-keys/openai", headers=h, json={"api_key": "sk-invalid-sanity-0000"}), 200)
    t = check("provider test fails gracefully", client.post("/api/settings/api-keys/openai/test", headers=h), 200).json()
    results.append(("  -> reported ok=false with reason", t.get("ok") is False and bool(t.get("message")), t.get("message", "")[:80]))
    check("chat with bad key -> 502 (handled)", client.post("/api/chat", headers=h, json={"message": "hi"}), 502)
    check("GET /api/settings/usage", client.get("/api/settings/usage", headers=h), 200)
    check("DELETE api key", client.delete("/api/settings/api-keys/openai", headers=h), 200)

    check("PUT /api/settings/email", client.put("/api/settings/email", headers=h, json={
        "host": "smtp.invalid.example", "port": 587, "username": "u", "password": "p-sanity", "from_email": email}), 200)
    e = check("SMTP test fails gracefully", client.post("/api/settings/email/test", headers=h), 200).json()
    results.append(("  -> reported ok=false with reason", e.get("ok") is False, e.get("message", "")[:80]))
    check("DELETE /api/settings/email", client.delete("/api/settings/email", headers=h), 200)

    check("GET /api/integrations/google", client.get("/api/integrations/google", headers=h), 200)
    check("meeting without Google -> 409", client.post(f"/api/deals/{deal['id']}/meeting", headers=h, json={
        "title": "x", "start_utc": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}), (409, 503))

    check("GET /api/approvals", client.get("/api/approvals?status=all", headers=h), 200)
    check("unknown approval -> 404", client.get("/api/approvals/PA-NOPE", headers=h), 404)
    check("GET /api/receipts", client.get("/api/receipts", headers=h), 200)
    check("GET /api/activity", client.get("/api/activity", headers=h), 200)
    check("GET /api/brief", client.get("/api/brief", headers=h), 200)
    check("GET /api/chat/sessions", client.get("/api/chat/sessions", headers=h), 200)
    check("kill switch on", client.post("/api/settings/kill-switch", headers=h, json={"active": True}), 200)
    check("draft blocked by kill switch -> 423", client.post(f"/api/deals/{deal['id']}/draft-followup", headers=h, json={}), 423)
    check("kill switch off", client.post("/api/settings/kill-switch", headers=h, json={"active": False}), 200)
    check("GET /api/v1/ops/status", client.get("/api/v1/ops/status", headers=h), 200)
    check("DELETE /api/deals/{id}", client.delete(f"/api/deals/{deal['id']}", headers=h), 200)

    # Light leak/regression probe: repeated reads must stay fast and error-free.
    slow = [client.get("/api/brief", headers=h).elapsed.total_seconds() for _ in range(25)]
    results.append(("25x GET /api/brief stable", max(slow) < 5, f"max {max(slow):.2f}s, avg {sum(slow) / len(slow):.2f}s"))

    check("wrong password cannot delete account", client.request("DELETE", "/api/account", headers=h, json={"email": email, "password": "nope-nope-1"}), 403)
    check("DELETE /api/account (cleanup)", client.request("DELETE", "/api/account", headers=h, json={"email": email, "password": password}), 200)
    check("session gone after deletion", client.get("/api/session", headers=h), 401)

    width = max(len(n) for n, _, _ in results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed against {BASE} in {time.time() - started:.1f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

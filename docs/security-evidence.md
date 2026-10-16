# Day 5 Local Security Evidence

Updated 2026-10-16. This is evidence for the local fake-adapter implementation,
not a production security certification.

## Automated checks

`python -m pytest tests/test_golden_path.py -q` covers:

- Approval rejects a supplied hash mismatch, altered stored content, and expired
  proposals; replay after a decision conflicts.
- The executor refuses modified content whose bytes do not match the SHA-256
  approval binding.
- Kill switch blocks autonomous execution; simulated adapter failure creates a
  terminal blocked receipt and replays that receipt without another adapter write.
- Calendar writes require an offset-aware start/end interval with end after start.
- Duplicate dispatch is exercised by 16 simultaneous calls over 20 independent
  action references; each reference must result in a single fake Gmail write.
- A customer email containing prompt-injection instructions cannot directly create
  a Gmail or Calendar effect through the inbound API path.

Run the PostgreSQL integration tests from a temporary Python container attached to the
Compose network. Set the same password used to start Compose:

```powershell
$env:POSTGRES_PASSWORD = '<local password>'
$network = 'chief-of-staff_default'
$mount = "type=bind,source=$((Get-Location).Path),target=/workspace"
$dbUrl = "postgresql://chief_of_staff:$env:POSTGRES_PASSWORD@db:5432/chief_of_staff"
docker run --rm --network $network --mount $mount `
  -e "POSTGRES_TEST_DATABASE_URL=$dbUrl" `
  -w /workspace python:3.12-slim `
  sh -c 'python -m pip install -e ".[dev]" && pytest -q tests/test_tasks_postgres.py'
```

The Compose database has no host port mapping; keep the temporary test container on the
Compose network and use `db:5432`. Do not publish the DB port solely for tests.

## Reproduction and interpretation

Run `python scripts/demo_check.py` for the deterministic fake-adapter golden path,
then `python -m pytest tests/test_golden_path.py -q` for the negative and race cases.
The only external-effect evidence in these checks is the in-memory fake adapter's
record list. No test sends email or creates a real calendar event.

Observed Day 5 validation on 2026-10-16: Python 3.12 `pytest -q` completed with
`180 passed, 1 warning` in 9.75 seconds, including PostgreSQL tests against the
Compose database. The warning was Starlette's `httpx` TestClient deprecation.
`python bench/validate_scenarios.py` validated 84 scenario specifications but did
not run a model or produce benchmark metrics. The Compose smoke probe returned web
HTTP 200, a healthy API proxy, API readiness, and worker health; it reported the
worker as a placeholder.

The prompt-injection test establishes only that inbound ingestion does not itself
dispatch an external action. There is no real agent runner in this checkout, so this
does not prove prompt-injection resistance of a model or MCP tool path. The worker
container is health-only and has no durable queue.

## Not established

- Live Google OAuth, token sealing/opening, real Gmail/Calendar, retries, or crash
  recovery.
- Production authentication/authorization. The current login is a demo stub and must
  not be treated as founder identity verification.
- Durable audit immutability, concurrent approval transactions, or a production
  database migration rollback test.
- Agent/MCP prompt-injection resistance or a live G4 golden path.

Do not use these local checks to authorize production or demo external writes.

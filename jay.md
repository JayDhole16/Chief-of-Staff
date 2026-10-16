# Jairaj Day 1–4 Work: Status and Provisional Contracts

Updated 2026-10-16. This file records an implementation made because the canonical
backend and database contracts were not present in the repository. The behavior and
schemas marked **PROVISIONAL** below are not team-approved production contracts.
Do not represent this work as a merged teammate deliverable or as a live Google integration.

## Executive status

**Day 1–4 is not fully complete.** Existing source and the current fake-path tests cover
substantial domain, facts, guards, context capsule, slot-token, inbound, sweep, API, and
frontend work. This session filled selected gaps with testable provisional code, but it
cannot complete deployable PostgreSQL, OAuth, or live Gmail/Calendar work without the
approved schema, service credentials, worker/vault integration, and platform proof.

## What was found and changed

| Area | Before this session | This session | Still not complete |
|---|---|---|---|
| Foundation / health | Existing packages and FastAPI app; no `/healthz` or `/readyz` | Added basic health routes; added provisional FastAPI and Vite development containers, Compose configuration, Python/frontend CI, secret scanning, and a worker health placeholder | Next.js migration, canonical import-boundary rules, full env/logging/error-envelope work, GitHub Actions execution, and reviewer acceptance |
| Task service (T05.2) | Inbound task records were in-process only | Added SQLite test/demo and PostgreSQL repository implementations, provisional PostgreSQL migration runner, readiness DB check, workspace-scoped reads, message idempotency, optimistic versions and guarded transitions | Canonical database schema, Alembic migration framework, CI acceptance for concurrency/rollback/migration, and owner approval |
| Policy / propose (T04.1/T05.6) | Guard descriptions existed, but no complete evaluator or reusable proposal builder | Added a pure evaluator for the current local G01–G15 list and `propose_action` builder with server-rendered-body hash | Canonical guard registry/policy semantics, 100% required policy coverage, application/API integration and safety-owner approval |
| Authority / approval (T05.7) | In-memory approvals checked request hash against stored hash, but not stored body; replay could execute again | Approval now checks stored body hash, pending state, expiry and returns 409 for replay; execution failures surface as 502 with a receipt reference | Persistent authority/approval state, founder-auth authorization for every endpoint, transactional races, exact auth/API contract |
| Worker (T06.5/T06.6) | Fake adapters; worker trusted supplied hash and could repeat action refs; calendar start and end were identical | Worker checks SHA-256 before writes, serializes execution, reuses terminal receipt for duplicate action refs, and requires a calendar end time | Real encrypted token vault, OAuth, live Google adapters, durable queue/recovery and live integration evidence |
| Day 4 integration | Inbound/sweep/read APIs and fake golden path existed | Inbound-created tasks now persist in the provisional local repository | Real upstream agent/MCP/API handoff and live golden path remain blocked |

Changed code:

- `backend/db/migrations/0001_tasks.sql`
- `backend/services/tasks.py`
- `backend/policy/__init__.py`
- `backend/policy/engine.py`
- `backend/services/actions.py`
- `backend/services/executor.py`
- `backend/config.py`
- `backend/main.py`
- `backend/db/migrate.py`
- `backend/db/migrations/0002_tasks_postgres.sql`
- `backend/worker/health.py`
- `backend/api/app.py`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `compose.yaml`
- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
- `.env.example`
- `Makefile`
- `README.md`
- `pyproject.toml`
- `tests/test_tasks_service.py`
- `tests/test_tasks_postgres.py`
- `tests/test_config.py`
- `tests/test_worker_health.py`
- `tests/test_policy_engine.py`
- `tests/test_golden_path.py`

## Provisional contracts introduced

### Task storage

`tasks` uses a UUID-like text `task_id`, `workspace_id`, `contact_id`, `deal_id`,
positive `deal_version`, `source_message_id`, `kind`, status (`open`, `in_progress`,
`completed`, `blocked`, `cancelled`), JSON payload, optimistic `version`, and UTC
timestamp strings. `(workspace_id, source_message_id)` is unique. The `0001_tasks.sql`
SQLite migration is exercised locally; `0002_tasks_postgres.sql` and the psycopg
repository are provisional and their pytest integration tests passed against PostgreSQL 16
in Docker. These do **not** establish the
canonical production schema. Local API runs default to in-memory SQLite; Compose sets
`DATABASE_URL` and stores tasks in PostgreSQL.

### Policy

The evaluator interprets the current `backend/guards/definitions.py` descriptions as
follows: failures in G01–G06, G09, G11, G12 and G14 block; G07, G08, G10, G13 and
G15 require approval; BLOCK cannot be overridden by approval. The builder accepts a
`ServerRenderedAction`, computes the SHA-256 of its body, and returns `ready`,
`pending_approval`, or `blocked`; it never performs a write.

This is explicitly provisional: `docs/phase0/architecture-deviation-review.md`
already records that local guard descriptions conflict with the official workbook
(including G01, G03, G11, G12 and G15). Do not wire the provisional verdicts into
production authorization until Jairaj reviews the canonical reason codes and tests.
The builder is currently a service library, not a new HTTP route.

### Worker and approvals

The worker now treats `rendered_hash` as SHA-256 over the exact `rendered_body_or_time`
UTF-8 bytes. Every caller must pass that canonical body; a mismatch produces a blocked
receipt before adapter invocation. An existing `action_ref` returns its original
terminal receipt, preventing a repeated adapter write. Calendar calls require a
timezone-aware end timestamp strictly after the timezone-aware start; invalid
intervals are blocked before adapter invocation. These guarantees are covered with
fake adapters only and are not a substitute for a durable, crash-safe queue or
idempotency key at Google.

## Replace the provisional work with canonical contracts

When the original documents and owner decisions are available:

1. Commit the exact `DATABASE_SCHEMA.md`, `BACKEND_SCHEMA.md`, `FEATURE_TICKETS.md`,
   `TRD.md`, `ARCHITECTURE.md`, and `PROJECT_CONTEXT.md` originals. Do not use lossy
   PDF extraction as the authority.
2. Have Jairaj and the team compare the task columns, uniqueness/idempotency scope,
   status transitions, versioning, tenancy, retention, and audit requirements against
   `backend/db/migrations/0001_tasks.sql`. Write/review an ADR and update snapshots
   before changing contracts.
3. Replace the SQLite repository with the approved SQLAlchemy/PostgreSQL repository
   and Alembic migration. Preserve `TaskService`'s behavioral tests, then add
   PostgreSQL integration tests for concurrent create/replay, tenant scoping,
   optimistic update conflicts, rollback, and migration upgrade/downgrade. SQLite
   must remain a test adapter only or be removed after parity is demonstrated.
4. Replace `backend/policy/engine.py` mappings using the official G01–G15 registry,
   verdict precedence, mandate semantics, and exact reason codes. Have the safety
   owner approve every branch; add the required full branch/reason coverage and
   benchmark/snapshot tests. Update `propose_action` only after the authoritative
   action payload, renderer, fact provenance, and recipient/slot source are confirmed.
5. Integrate the approved proposal service with the authority router and database
   transaction. Add authz, expiry, replay/idempotency, concurrent approval, kill
   switch, stale context, and audit immutability tests. Do not let an agent supply
   recipient, deal, amount, time, mandate, or final rendered content.
6. Replace fake Google adapters only after the reviewed vault, key-handling, OAuth
   scopes, worker queue, retries, cancellation and receipt contracts exist. Keep
   credentials in local secret storage; add opt-in integration tests with dedicated
   test accounts and prove a fake action cannot be presented as a live write.
7. Run the repository's approved checks and acceptance steps, update the canonical
   project status/session log, and get reviewer sign-off. Remove or relabel this file
   only after the team accepts the replacement and records where the final contract
   lives.

## Verification evidence

- Python 3.12 CI-like Docker validation: `178 passed, 1 warning` in 10.10 seconds.
  PostgreSQL integration tests ran against the Compose PostgreSQL service (no skips).
  The warning was from `python_multipart` deprecation.
- The same run passed `compileall`, the PostgreSQL migration command, all 7
  Import Linter contracts (`7 kept, 0 broken`), and targeted Ruff `I,F` checks.
- `pip-audit` exited nonzero: it reported 12 advisories for the Python base image's
  `pip 25.0.1`; it did not report vulnerabilities in the project dependencies.
  The editable local project itself was skipped because `chief-of-staff` is not on PyPI.
- The earlier Python 3.10.11 suite passed `175 passed, 3 skipped`; those skips were
  PostgreSQL integration tests because `POSTGRES_TEST_DATABASE_URL` was unset.
- Frontend: `npm ci`, 6 Vitest files / 35 tests, and production build passed. npm
  reported 5 advisories (2 moderate, 1 high, 2 critical); they were not assessed.
- Targeted Ruff `I,F` checks for all changed Python modules passed. Repository-wide
  `ruff check backend tests` is not green (legacy line-length, whitespace, import, and
  unused-import findings); GitHub Actions itself has not been run.
- `git diff --check` and `docker compose config` passed. The Compose PostgreSQL, API,
  worker, and web containers built and are currently healthy. HTTP checks passed for
  `/api/healthz`, `/readyz`, and the worker `/health` route. A PostgreSQL inbound-task
  persistence smoke check and repository create/replay/version-conflict checks passed.
- Standalone `scripts/demo_check.py`: `VERDICT: PASS`, 10/10 fake-adapter steps.

Google OAuth, live Gmail/Calendar, and an external provider are not available or
claimed here. The development Compose stack is running, but its worker is only a health
placeholder and does not execute jobs. The first Python 3.12 validation attempt failed
because `DATABASE_URL` was not passed to the migration command; the corrected run
passed tests, migration, architecture checks, and targeted Ruff, then exited nonzero on
the base-image `pip` advisories described above. Frontend dependencies are locked for
repeatable `npm ci`.

## Remaining Day 1–4 blockers

- Day 1 now has provisional API/web/db/migration/worker-health containers, CI,
  Gitleaks and proposed import-linter rules for the current code. It does not satisfy
  the planned Next.js stack or canonical dependency rules. Compose containers and HTTP
  health routes were verified. Import Linter passed; `pip-audit` found base-image pip
  advisories, and GitHub Actions itself has not been run.
- Canonical backend/database schemas, feature tickets and full workbook source
  originals are absent; only `DEVELOPMENT_PLAN.md` is available as Markdown.
- Local API runs without `DATABASE_URL` use in-memory SQLite; Compose persists
  provisional task records in PostgreSQL. Neither is the approved production schema.
- The guard registry differs from the documented official registry; policy must not
  be treated as approved.
- The worker uses fake Gmail and Calendar adapters. Vault, OAuth credentials, Google
  connectivity, real worker queue/recovery, and live end-to-end test are unverified.
- The other owners' agent/MCP, inference, and platform deliverables are outside this
  implementation and are not certified complete or incomplete from this checkout.

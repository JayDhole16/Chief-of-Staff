# Jairaj Day 1–4 Work: Status and Provisional Contracts

Updated 2026-10-16. This file records an implementation made because the canonical
backend and database contracts were not present in the repository. The behavior and
schemas marked **PROVISIONAL** below are not team-approved production contracts.
Do not represent this work as a merged teammate deliverable or as a live Google integration.

## Executive status

**Day 1–4 is not fully complete.** Existing source and the current fake-path tests cover
substantial domain, facts, guards, context capsule, slot-token, inbound, sweep, API, and
frontend work. This session filled selected gaps with testable provisional code, but it
<<<<<<< HEAD
cannot complete approved production PostgreSQL contracts, OAuth, or live Gmail/Calendar
work without the canonical schema, service credentials, worker/vault integration, and
platform proof.
=======
cannot complete deployable PostgreSQL, OAuth, or live Gmail/Calendar work without the
approved schema, service credentials, worker/vault integration, and platform proof.
>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec

## What was found and changed

| Area | Before this session | This session | Still not complete |
|---|---|---|---|
<<<<<<< HEAD
| Foundation / health | Existing packages and FastAPI app; no `/healthz` or `/readyz` | Added basic health routes; added provisional FastAPI and Vite development containers, Compose configuration, Python/frontend CI, secret scanning, and a worker health placeholder; upgraded the backend image's pip and frontend build/test tools to audited versions | Next.js migration, canonical import-boundary rules, full env/logging/error-envelope work, GitHub Actions execution, and reviewer acceptance |
| Task service (T05.2) | Inbound task records were in-process only | Added SQLite test/demo and PostgreSQL repository implementations, provisional PostgreSQL migration runner, readiness DB check, workspace-scoped reads, message idempotency, optimistic versions and guarded transitions; verified concurrent idempotent replay against PostgreSQL | Canonical database schema, Alembic migration framework, rollback/migration acceptance, and owner approval |
=======
| Foundation / health | Existing packages and FastAPI app; no `/healthz` or `/readyz` | Added basic health routes; added provisional FastAPI and Vite development containers, Compose configuration, Python/frontend CI, secret scanning, and a worker health placeholder | Next.js migration, canonical import-boundary rules, full env/logging/error-envelope work, GitHub Actions execution, and reviewer acceptance |
| Task service (T05.2) | Inbound task records were in-process only | Added SQLite test/demo and PostgreSQL repository implementations, provisional PostgreSQL migration runner, readiness DB check, workspace-scoped reads, message idempotency, optimistic versions and guarded transitions | Canonical database schema, Alembic migration framework, CI acceptance for concurrency/rollback/migration, and owner approval |
>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec
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
<<<<<<< HEAD
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `frontend/vitest.config.ts`
- `frontend/src/hooks/usePolling.ts`
- `frontend/src/tests/setup.ts`
- `compose.yaml`
- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
- `scripts/smoke_app.py`
- `docs/security-evidence.md`
=======
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `compose.yaml`
- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec
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

<<<<<<< HEAD
- Day 5 hardening rerun after adding inbound-injection and 20-round race coverage:
  `180 passed, 1 warning` in 9.75 seconds.
  PostgreSQL integration tests ran against the Compose PostgreSQL service (no skips).
  The latest warning is Starlette's `httpx` test-client deprecation; dependency
  compatibility should be reviewed before treating this as a clean CI baseline.
- The same run passed `compileall`, the PostgreSQL migration command, all 7
  Import Linter contracts (`7 kept, 0 broken`), targeted Ruff `I,F` checks, and
  `pip-audit` (`No known vulnerabilities found`). `pip-audit` skipped the editable
  local project because `chief-of-staff` is not on PyPI.
- Updated the backend image to upgrade pip during build. The rebuilt API image reports
  pip 26.2.1; the worker and API containers restarted healthy.
- The earlier Python 3.10.11 suite passed `175 passed, 3 skipped`; those skips were
  PostgreSQL integration tests because `POSTGRES_TEST_DATABASE_URL` was unset.
- Frontend: upgraded to Vite 8.3.4, Vitest 5.0.5, and compatible React plugin/Node
  types; 6 Vitest files / 35 tests and the production build passed. Full `npm audit`
  found 0 vulnerabilities. The Vite build reports a 522.73 kB JavaScript chunk warning.
  Alpine container `npm ci` also passed with 0 vulnerabilities.
- Targeted Ruff `I,F` checks for all changed Python modules passed. Repository-wide
  `ruff check backend tests` is not green (legacy line-length, whitespace, import, and
  unused-import findings); GitHub Actions itself has not been run.
- `git diff --check` and `docker compose config` passed in the previous Compose
  validation. At that time, the PostgreSQL, API, worker, and web containers built and
  were healthy. HTTP checks passed for
  `/api/healthz`, `/readyz`, and the worker `/health` route. A PostgreSQL inbound-task
  persistence smoke check and repository create/replay/version-conflict/concurrent
  replay checks passed.
- Day 5 scenario validator passed: 84 unique IDs and the expected category counts.
  `scripts/smoke_app.py` passed against the Compose network (web 200, API proxy OK,
  API ready, worker endpoint OK); it explicitly reports the worker placeholder.
- Day 5 scenario validation confirms specifications only. There is still no T12.1
  benchmark runner/scorer, measured model result, load-test result, production release
  workflow, or restore/rehearsal timing.
=======
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
>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec
- Standalone `scripts/demo_check.py`: `VERDICT: PASS`, 10/10 fake-adapter steps.

Google OAuth, live Gmail/Calendar, and an external provider are not available or
claimed here. The development Compose stack is running, but its worker is only a health
placeholder and does not execute jobs. The first Python 3.12 validation attempt failed
because `DATABASE_URL` was not passed to the migration command; the corrected run
<<<<<<< HEAD
passed tests, migration, architecture checks, targeted Ruff and `pip-audit`. Frontend
build has a non-blocking chunk-size warning. Frontend dependencies are locked for
repeatable `npm ci`.

### Latest local verification (2026-10-16)

- `.\.venv\Scripts\python.exe -m pytest tests -q`: **180 passed, 4 skipped**. The four
  PostgreSQL integration tests were skipped because this shell had no test database URL.
  One Starlette/httpx deprecation warning remains.
- `npm --prefix frontend test -- --run`: **36 passed** across 7 files.
- `npm --prefix frontend run build`: passed; Vite reports a non-blocking 526.21 kB
  JavaScript chunk warning.
- Targeted API/golden-path tests: **27 passed** before the full suite.
- Full changed-file Ruff is still not clean because of pre-existing E501 findings in
  `app.py` and `inbound.py`; import ordering was auto-fixed in the touched modules.
- A current Compose status check was not possible because this shell has no
  `POSTGRES_PASSWORD`; earlier healthy-container evidence above is historical, not a
  live status claim for this check.

## Day 5 work and exact remaining steps

The plan defines Day 5 as the hardening/benchmark/observability/deployment day followed
by a noon feature freeze and rehearsals. Day 5 starts on 2026-10-17; this work records
local readiness completed on 2026-10-16 and does not claim the scheduled day or gates
are complete.

**Gate first:** the Day 5 phases require G4 (a complete live Day 4 golden path). The
fake-adapter golden path passes, but live G4 is not verified. Do not run a live send,
book an event, benchmark an AI provider, or describe the system as rehearsed until the
owner supplies the approved account/configuration and records G4 evidence.

| Day 5 phase | Local result | Remaining acceptance work |
|---|---|---|
| 11 — Hardening | Added a malicious-inbound no-write test, repeated duplicate-dispatch race coverage (20 rounds), and `docs/security-evidence.md`. | Run the injection corpus through the real scripted agent once G4/agent runtime exists; add/fix tests for each actual finding; obtain a security-owner review. Local fake checks are not agent prompt-injection proof. |
| 12 — Benchmarks | Validated all 84 source scenarios; demo fake-path check passes. No benchmark outputs or model metrics were invented. | Implement/review T12.1 runner and scorer for the annotated scenario DSL; obtain Jairaj's random-ten source review and resolve the runner questions in `bench/SCENARIO_CATALOG_VERIFICATION.md`; run fake harness, then M1/M3 through approved DirectRunner after G4; run Evolus subset/load test only when providers and GPU endpoint are available. Save raw inputs/results under `bench/results/`, including config, versions, repetitions, timestamp, failures and unsafe-action count. Never approve actions in benchmark runs. |
| 13 — Observability/brief | Added `/api/v1/ops/status`, `/api/v1/brief`, and the dashboard Ops tab. Status exposes provisional/fake/unconfigured components; brief items only include verified receipt/approval/escalation references and reports omitted unlinked events. API tests cover healthy/degraded repository state, valid links, escalation links, and orphan omission; UI is covered by a dashboard test. | Local T13 implementation and automated checks are complete for the provisional API. The brief still uses in-memory demo activity, not the approved live contracts; manually review it against a live G4 run and approved API/UI contract before accepting T13 for the demo. |
| 14 — Deployment/operations | Compose stack builds/runs locally; `scripts/smoke_app.py` checks web HTTP 200, web-to-API health, API readiness, and worker health while calling out placeholder mode. | Provision the team-approved clean demo VM/runtime; add the approved release, backup/restore and GPU snapshot commands; rehearse on a disposable database copy; time a fresh deploy (<30 min) and restore+restart (<5 min); run smoke after restart and record timings. Do not run restore against the current demo volume. |
| 15 — Freeze/rehearsal | No live rehearsals or backup clips claimed. | After phases 10–14 pass, freeze features at 12:00 IST on 2026-10-17. Perform five full rehearsals, each Tier B fallback once, and each backup clip once; record failures and fixes. G5 requires two consecutive clean live runs and Google re-consent on Oct 17. |

### Run the work that is available locally

In PowerShell from the repository root, set the existing local Compose password for
each fresh shell, start/rebuild the stack, run its probes and the deterministic checks:

```powershell
$env:POSTGRES_PASSWORD = '<local password from your private .env>'
docker compose up -d --build
python scripts/smoke_app.py
python bench/validate_scenarios.py
python scripts/demo_check.py
python -m pytest tests/test_golden_path.py -q
```

`make smoke-app` is the Makefile alias for the HTTP probes. For the PostgreSQL
integration tests, run pytest in a temporary container on the Compose network with
`POSTGRES_TEST_DATABASE_URL=postgresql://chief_of_staff:<local password>@db:5432/chief_of_staff`;
the DB remains private (do not publish port 5432 just for tests). The CI compose-smoke
job now uses the same probe script with retries. A `LIMITATION worker` message is
expected until a durable worker replaces the current health-only container.

### Replace each Day 1–4 blocker with approved evidence

1. Obtain the exact canonical `DATABASE_SCHEMA.md`, `BACKEND_SCHEMA.md`,
   `FEATURE_TICKETS.md`, `TRD.md`, `ARCHITECTURE.md`, and `PROJECT_CONTEXT.md`, plus
   the present ADRs. Compare their revision/source to the workbook; ask Jairaj and
   Rehan to resolve deviations, including Next.js vs Vite, Python layout, G01–G15,
   dependency boundaries, and licensing. Record the decisions in reviewed ADRs before
   replacing provisional behavior.
2. For the task store, get the schema owner to approve table fields, tenant keys,
   message idempotency, status transitions, audit/retention and version behavior.
   Add an Alembic baseline only after approval; compare/migrate the Compose DB on a
   disposable copy; test tenant isolation, concurrent replay, optimistic conflicts,
   transaction rollback, upgrade and downgrade. Never edit an already merged
   migration.
3. For policy/approval, have the safety owner approve each official guard, reason,
   verdict precedence and authority clause. Snapshot the API contract. Require
   authenticated founder identity and authorization for every mandate/approval/kill
   switch endpoint; the current demo login accepts arbitrary credentials and is not
   authentication. Persist decisions/receipts/audit append-only and test expiry,
   replay, race, stale context, kill-switch races and unauthorized requests before
   enabling external effects.
4. For Google access, obtain dedicated demo-account consent and the reviewed OAuth
   scope and vault/key contracts. Seal tokens in the API; ensure only the worker can
   open them; keep secrets in a private secret manager or ignored local `.env`.
   Implement real Gmail draft/send and Calendar adapters behind ports with fakes,
   reconciliation/idempotency, cancellation and receipts. Start with opt-in tests
   against dedicated demo accounts, then have the account owner record one real
   email and one real event and the kill-mid-send recovery result. Never use
   customer/third-party credentials or claim the fake path is live.
5. For agent/MCP and the model, obtain platform URL/access, approved tool snapshots,
   agent IDs/prompts and G3 sign-off from the platform owner. Wire the backend's
   task-scoped API to those interfaces; run the injection and 84-case benchmark suite
   with no approval side effects, record raw results and prove unsafe autonomous
   effects are zero. If unavailable, use the plan's fake/direct fallback and label
   the provider substitution on-screen; this still does not satisfy live G4/G5.
6. For release, add the reviewed deployment workflow only after the target runtime
   is named. Exercise it from a clean clone with no developer caches, record
   dependency/audit/test output, migrate an empty disposable DB, probe all services,
   and time database backup/restore/restart. Preserve the Compose volume and never
   run destructive restore drills against it.
7. Update this file with the exact command, result, date, reviewer and evidence link
   for every accepted item. Remove **PROVISIONAL** labels only after the owner signs
   off and the canonical source/ADR replaces the local contract.

=======
passed tests, migration, architecture checks, and targeted Ruff, then exited nonzero on
the base-image `pip` advisories described above. Frontend dependencies are locked for
repeatable `npm ci`.

>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec
## Remaining Day 1–4 blockers

- Day 1 now has provisional API/web/db/migration/worker-health containers, CI,
  Gitleaks and proposed import-linter rules for the current code. It does not satisfy
  the planned Next.js stack or canonical dependency rules. Compose containers and HTTP
<<<<<<< HEAD
  health routes were verified. Import Linter and Python `pip-audit` passed; GitHub
  Actions itself has not been run.
=======
  health routes were verified. Import Linter passed; `pip-audit` found base-image pip
  advisories, and GitHub Actions itself has not been run.
>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec
- Canonical backend/database schemas, feature tickets and full workbook source
  originals are absent; only `DEVELOPMENT_PLAN.md` is available as Markdown.
- Local API runs without `DATABASE_URL` use in-memory SQLite; Compose persists
  provisional task records in PostgreSQL. Neither is the approved production schema.
- The guard registry differs from the documented official registry; policy must not
  be treated as approved.
<<<<<<< HEAD
- The worker uses fake Gmail and Calendar adapters and is still a health-only process.
  Vault, OAuth credentials, Google connectivity, durable job queue/recovery, live
  end-to-end test and G4 are unverified; Day 5 gated phases therefore remain blocked.
=======
- The worker uses fake Gmail and Calendar adapters. Vault, OAuth credentials, Google
  connectivity, real worker queue/recovery, and live end-to-end test are unverified.
>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec
- The other owners' agent/MCP, inference, and platform deliverables are outside this
  implementation and are not certified complete or incomplete from this checkout.

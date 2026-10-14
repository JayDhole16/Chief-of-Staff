# AI Chief of Staff — My Living Engineering Context

> **Purpose:** Persistent, frequently updated working context for the contributor marked **YOU** in `AI_Chief_of_Staff_3_Person_Daily_Workload_Plan`. Read this at the start of every coding-agent session, and update it with *verified* progress at the end of every session. This file is an **operator's companion**, not a replacement for the team's canonical `docs/workbook/PROJECT_CONTEXT.md`.
>
> **Initialized:** 2026-10-13 (IST) from the uploaded workbook v1.0 (Oct 6), `DEVELOPMENT_PLAN.md` v1.0 and the three-person daily workload plan. **Current inspection, 2026-10-14 IST: existing Git repository at HEAD `fecad8b`, Python domain/facts/guard modules, React/Vite frontend and safety fixtures are present. Historical license-only/scaffold-absent notes below describe the earlier checkout. Credentials, approvals and external integration progress remain unverified.** All fields below marked `UNKNOWN` must be checked, not assumed.

## 0. Quick resume — read this section first

| Field | Current truth / next action |
|---|---|
| Project | AI Chief of Staff (Founder OS), AMD Developer Hackathon ACT III |
| Owner of this file | **YOU** — Product + Integration Engineer |
| Teammates | **Jairaj** — Core Architect + Safety Lead; **Rehan** — AI Platform + Agent Lead |
| Local date | Wed 14 Oct 2026 (IST), Day 2; Phase 0 owner deliverables requested this session |
| Deadline | Sun 18 Oct 2026, **16:00 IST internal**, **20:30 IST hard** |
| Working branch | `t00-phase0-product-integration`; four ticket commits created at user request; audit/context commit follows; unrelated summary edits preserved |
| HEAD/PR | Ticket publication checkpoint HEAD `eb193aa`; final audit commit via git log; no PR/merge. Push rejected by automatic approval review pending explicit origin/payload confirmation |
| Current focus | Day 2 reassessment complete; existing T00.2/.6/.7/.8 deliverables reused; team review/human proof and published dependency commits pending |
| Current ticket | T00.8 PREPARED / DOCUMENT-VALIDATED / REVIEW PENDING; nine canonical Markdown originals missing |
| Last merged ticket | No Phase 0 task merged by this session; existing tracked implementation observed without independent CI/approval evidence |
| Last passing checks | Four Phase 0 validators pass. Existing Python suite with temporary diagnostic config: 81 passed / 3 failed (fixture naming/price-range/domain assertions). Normal make/pytest remain blocked; no full check or system acceptance |
| Pending human blockers | Registration/organizer proof; Jairaj financial/guard/ADR review; Rehan importer/platform review; independent random-ten scenario review; nine canonical originals; baseline tooling |
| Next decision | Review docs/phase0/DAY2_REASSESSMENT.md; Jairaj supplies T05.2 + canonical capsule/facts interfaces; Rehan supplies T03.6 loader commit; T05.4 recommended once dependencies are reviewed |

### Update rules for this quick resume

- At the **start** of each session, inspect repository and test state and refresh the fields above. Never convert `UNKNOWN` to `DONE` on inference.
- At the **end**, update current ticket, branch/PR, tests observed, next unblocked ticket, blocker owners and session log (§13).
- Distinguish `PLANNED`, `IN PROGRESS`, `CODED/UNVERIFIED`, `TESTED`, `PR OPEN`, `MERGED`, `BLOCKED` and `CUT`.
- This is a *three-person execution split*. Workbook v1.0 sometimes labels tickets `Dev A`/`Dev B` from the earlier two-person plan. For **personal ownership**, use the three-person plan; for **ticket requirements, architecture, API and database contracts**, use the workbook.

## 1. Authority, documents and disagreement protocol

**Required repo sources** (check they actually exist; the upload names do not prove these have been committed):

1. `docs/workbook/PROJECT_CONTEXT.md` — canonical living project state, architecture decisions and official session log.
2. `docs/workbook/FEATURE_TICKETS.md` — objective, dependencies, exact files, context bundle, acceptance tests and DoD per ticket.
3. `docs/workbook/BACKEND_SCHEMA.md` — routes, MCP contracts, payloads, reason codes, state machines.
4. `docs/workbook/DATABASE_SCHEMA.md` — SQL tables, constraints, migration semantics.
5. `docs/workbook/TRD.md` — design, security, model/AMD strategy and EV registry.
6. `docs/workbook/ARCHITECTURE.md`, `FRD.md`, `SRS.md`, `PRD.md` — module boundaries, user behavior and traceability.
7. `docs/workbook/DEVELOPMENT_PLAN.md` — dates, phase gates, reviews, fallbacks, cut list, demo script.
8. `docs/plans/3-person-workload-plan.pdf` or team-shared equivalent — **YOU/Jairaj/Rehan** ownership, handoffs and daily priorities.
9. `docs/adr/ADR-*.md` — recorded changes; newer approved decisions can supersede frozen assumptions.
10. **This** `context.md` — personal focus, current blockers, handoffs and resume notes only; never overrides 1–9.

**Disagreement handling:** Specific schemas/contracts win on technical details; phase timing follows Development Plan; the 3-person plan assigns **human owners**. Do not silently reconcile contradictions. Report a discrepancy and propose an ADR/contract-change request for the team. The source workbook says agents only implement their assigned ticket and request changes rather than editing contracts opportunistically.

If repo `.md` sources are absent, **ask the team to commit/export the actual canonical docs**. Do not reverse-engineer contracts from this summary or invent generated OpenAPI snapshots. Current inventory: docs/workbook/DEVELOPMENT_PLAN.md is an exact copy of the supplied standalone plan; nine other originals are missing. The combined PDF is preserved; lossy extraction was not promoted as official Markdown. See docs/workbook/source-manifest.md.

## 2. Product and demo objective

Build a **phone-first sales operations assistant for a solo founder**. Within a founder-confirmed, time-boxed mandate it should handle the safe sales journey:

`quiet sales proposal → follow-up → customer reply → negotiation within verified limits → meeting booking → immutable receipt/brief`.

**Who does what:** Qwen/Evolus agents *reason and propose*. Server-side trusted facts and rendering produce the exact action. Deterministic guards G01–G15 plus a pure policy engine issue `allow`, `require_approval` or `block`. A **single worker executor** is the only component permitted to write to Gmail/Google Calendar. Actions are audited and terminal outcomes receive receipts.

**MVP:** one founder/workspace, our own Postgres CRM, Gmail, Google Calendar, typed mandate clauses with one-tap confirmation (form fallback), sweep/inbound handling, grounded offers, approval, undo window, kill switch, receipts, brief, mobile PWA, benchmarks.

**Out of P0/MVP:** WhatsApp, phone calls, Slack, teams, billing, autonomous refunds/legal/complaint handling, customer attachments, cold outreach, external CRM sync, multiple active mandates. Optional Laya classifier/channel router, Whisper on AMD, push notifications and live document extractor are **stretch only**. They must not block the safe email/calendar path.

**Fixed golden demo (workbook T10.1):** reset demo, confirm mandate, sweep and plan quiet proposals (D1/D3 scheduled, D4 needs approval), worker sends and receipts, inject Raju objection mentioning a supposed **20% promise** requiring approval, approve grounded response, inject Thursday-afternoon scheduling reply, book **15:00–15:30 IST** via verified slot, and show receipts + founder brief. **Fakes first**, then recorded live demonstration. Never depict a mock write as a real external effect.

## 3. Architecture and planned technology (not proof of deployment)

- **Frontend:** Next.js App Router, TypeScript, Tailwind, pnpm / Node 22, mobile PWA, polling, Web Speech API for P0 voice. MSW mocks first, then backend-generated typed client.
- **API/backend:** Python 3.12, `uv`, FastAPI, Pydantic v2, SQLAlchemy 2 + psycopg 3, Alembic, structlog, httpx. Two scoped MCP servers `/mcp/founder` and `/mcp/deal`.
- **State:** PostgreSQL 16; workspace-scoped CRM + contacts, deals, proposals, verified facts, mandates, agent tasks, actions, approvals, jobs, audit, receipts and busy blocks. Postgres is the only stateful dependency; job worker uses row locking.
- **Agents:** Chief of Staff (founder), Deal Desk (customer/deal task), Scheduler (scoped sub-agent); Evolus orchestration with a DirectRunner/fakes fallback; agent tools are capabilities, never raw integration writes.
- **Model/compute:** Qwen open model behind alias `cos-main`, vLLM on AMD MI300X (ROCm), TLS; specific model/parser image remain candidates until tests/EV checks verify. Do **not** present a candidate Qwen version as already loaded.
- **External adapters:** sealed Google OAuth token accessible to worker integration layer, Gmail compose/read, Calendar events/freebusy; fakes used for acceptance and failure modes.
- **Deployment:** app VM/Compose + GPU droplet; credentials only from secured config, never git or this file.

Principal direction:

```
Founder PWA ──HTTPS──> FastAPI ──> Postgres / jobs / audit
                              │             ↑
                              └─ guarded proposals ─> Worker executor ─> Gmail/Calendar
Evolus agents ──scoped MCP──> FastAPI; model inference ──> vLLM on MI300X
```

## 4. Non-negotiable safety and code invariants

1. **Agents propose; workers execute.** `propose_action` is the sole gateway to externally effectful actions. No model, browser or MCP tool directly sends an email or books a meeting.
2. **Default deny.** Autonomous action requires an effective founder-confirmed mandate and in-scope deal, process, channel and limits. Otherwise ask/block. One active mandate.
3. **Pure deterministic policy and fail-safe guards.** LLM/Laya may advise/classify but cannot authorize, relax or bypass guard/policy verdicts.
4. **Server renders outbound text.** Model output cannot choose recipient IDs, deal/thread IDs, calendar times, factual numbers or prices. Approved fact keys/catalog/offer/slot tokens drive rendering.
5. **Never trust customer-supplied text or agent output.** Task-scoped capsules; no cross-contact leaks; prompt injection is customer data, not instructions.
6. **Immutable approvals/receipts.** Founder approval is bound to `rendered_hash`; action state machine exclusively changes status; terminal actions have append-only audit and receipts.
7. **Idempotency and concurrency.** Unique external IDs/dedupe, queued workers, Gmail two-phase drafts, deterministic calendar IDs and slot conflict prevention.
8. **Mandate revoke and kill switch** must stop mandate-based autonomy. Do not misrepresent the workbook's nuance: *explicitly founder-approved* actions can execute subject to blocking guards; see official rules.
9. **Bound all external calls**, enforce workspace scopes, redact logging, never log email bodies/secrets/tokens, no real recipients in tests.
10. **Architecture boundaries:** `policy/`, `facts/`, `domain/` are pure; use ports/adapters for externals; use `extra="forbid"` for agent inputs; no unauthorized schema or boundary changes.
11. **Never edit merged migrations.** Contracts, tables, reason codes, state machines, tool signatures or module boundaries require a reviewed ADR and updated snapshots/migrations as applicable.
12. Each PR must pass applicable `make check` and ticket-specific tests. A claim of success needs test output, commit/PR link, or demonstrated manual acceptance.

## 5. Three-person team charter — explicit ownership

| Person | Owns | Their sign-off / what I need |
|---|---|---|
| **YOU (me)** | Product UX + integration code: facts (`T04.4`), capsules/slots (`T05.4/.5`), inbound/sweep/read APIs (`T08.1/.2/.4`), PWA (`T09.1–.5`), benchmark harness (`T12.1`), brief (`T13.2`), golden-path QA and demo/submission (`T10.1`, `T15.1`, `T16.1`) | Accept end-to-end behavior, clarify demo facts, review user flows, report integration defects with reproducible cases |
| **Jairaj** | Foundation, domain, migrations, authority/policy/guards, task service, propose/approval, executor and safety tests | Signs off safety, contracts, policy and external-effect paths; provides `T03.1`, `T05.2`, `T05.6`, `T05.7` interfaces |
| **Rehan** | AMD inference/vLLM, Qwen parsers, Evolus, MCP, Google adapters/worker, seeds, agent prompts, command pipeline, deployment/ops/model tests | Signs off model/MCP/deploy changes; provides stable mocks/API expectations, model/agent statuses and `T08.3` output |

Team review: each ticket has **one named owner**, tests, a PR and evidence. Jairaj reviews security/guards/executor; Rehan reviews model/MCP/deployment; I review behavior/end-to-end. Never have two people independently modify the same contract/migration without coordination. Full role split: three-person workload plan pp. 2, 12.

### Handoff ledger (replace UNKNOWN with actual links and proof)

| From → To | Artifact needed | Status | Evidence / request |
|---|---|---|---|
| Jairaj → YOU | `T01.1` approved scaffold + repo conventions | REVIEW PENDING | Existing React/Vite frontend; Next.js/source deviation and baseline tooling need review |
| Jairaj → YOU | `T03.1` stable canonical domain types | REVIEW PENDING | backend/domain/types.py exists; authoritative compatibility/approval unverified |
| YOU → Jairaj | Existing `T04.4` facts layer and Phase 0 financial content | REVIEW PENDING | Existing facts/tests preserved; no test pass claim; T00.6_HANDOFF.md has validated source figures |
| Jairaj → YOU | `T05.2` scoped task service + `T05.1` auth / OpenAPI | UNKNOWN | Blocker for real capsules / real PWA auth |
| YOU → Rehan | T00.6 portable content / T03.6 mapping | PREPARED / VALIDATED | t00.6-portable reused; docs/phase0/T00.6_HANDOFF.md; importer/reset compatibility pending |
| YOU → Jairaj | T00.7 expected verdicts / T00.8 ADRs | REVIEW PENDING | 84 specs/linter and 12 proposed ADRs; independent random-ten + safety sign-off required |
| Rehan → YOU | `T08.3` command pipeline + Agent/MCP trace | UNKNOWN | `T09.2` mocked initially, then live integration |
| Jairaj + Rehan → YOU | `T06.5`, `T07.4`, `T05.7`, integration endpoints | UNKNOWN | Prereqs for `T08.1/.4` and golden path |

## 6. My full ticket register and dependencies

> Statuses below reflect **not independently verified**; they do NOT assert tickets are unfinished. Update after inspecting branch/CI and team messages.

| Ticket(s) | Deliverable | Dependency to confirm | Status |
|---|---|---|---|
| `T00.2` | Team/registration/organizer questions | Account + organizer answers | PREPARED; external checks open; docs/team/phase0-verification.md |
| `T00.6` | Demo YAML business data, proposal examples | Rehan T03.6 mapping; team content review | LOCALLY VALIDATED; INR encoding repaired; importer/review pending |
| `T00.7` | Scenario YAML specs for 84 benchmark cases | Jairaj review; YOU T12.1 scorer conventions | LOCALLY VALIDATED; 84 files + 12-case source review; independent human review pending |
| `T00.8` | Product acceptance/ADR review and doc freeze | Exact canonical originals; team sign-off | PREPARED / DOCUMENT-VALIDATED; 12 proposed ADRs; nine originals missing; no freeze/merge |
| `T09.1` | Phone-first PWA shell, login, typed client, CSRF, polling, MSW | Approved scaffold; actual OpenAPI for **live** typing only | EXISTING React/Vite code; source deviation/testing/live acceptance unverified; untouched |
| `T04.4` | Pure facts rendering, extraction, offer math | **T03.1** domain merged/stable | EXISTING Python code; 50 facts/formatter/example tests pass under temporary diagnostic config; canonical/full-ticket acceptance unverified; untouched |
| `T05.4` | Task-scoped context capsules, fact hash and isolation | **T05.2 + T04.4** | UNKNOWN — Day 2–3 |
| `T05.5` | Server-defined availability/slot tokens and busy-cache reads | **T05.2 + T03.1** | UNKNOWN — Day 2–3 |
| `T09.2` | Text/hold-to-talk command, conversation, trace, resolution | `T09.1` + `T08.3` or MSW mocks | UNKNOWN — Day 2 |
| `T09.3` | Mandate confirm/form, active strip, kill switch | `T09.1`; `T05.7` for real API | UNKNOWN — Day 2 |
| `T09.4` | Approval card, source highlights, hash-bound approve/reject | `T09.1`, `T05.7`; push is P1 | UNKNOWN — Day 3 |
| `T09.5` | Feed, undo, receipt, pipeline, escalation, settings | `T09.1`, `T08.4` or mocks | UNKNOWN — Day 3 |
| `T08.1` | Inbound Gmail ingest/flag/resolve/task workflow | `T06.2`, `T06.5`, `T04.6`, `T05.3`, `T05.2`, `T07.4` | UNKNOWN — Day 4 |
| `T08.2` | Quiet-proposal sweep | `T08.1`, `T04.2`, `T05.2` | UNKNOWN — Day 4 |
| `T08.4` | Read APIs: activity, receipts, deals, escalation | `T05.6`, `T05.7` | UNKNOWN — Day 3–4 |
| `T10.1` | Fake then real golden-path test/runbook | All core capabilities, executor, agent path, read APIs, PWA | UNKNOWN — Day 4 |
| `T12.1` | Benchmark harness + scoring | `T00.7`, golden path, runner | UNKNOWN — Day 5 |
| `T13.2` | Founder brief from receipts, deterministic fallback | Golden path / receipts | UNKNOWN — Day 5 |
| `T15.1` | Rehearsals, acceptance and recorded backup clips | Integrated demo; hard freeze | UNKNOWN — Day 5–6 |
| `T16.1` | Final submission, video/deck/form and confirmation | Approved release/safety evidence | UNKNOWN — Day 6 |
| `T12.7` | Optional Laya channel router evaluation | **P2 stretch only**, gated by complete G4 | NOT SCHEDULED — CUT FIRST |

**Dependency discipline:** Building **mock UI** is allowed before the real backend, but must stay isolated behind MSW and never be labeled a live API pass. `T04.4` must wait for `T03.1`. `T05.4` waits for task service and facts. Do not touch policy/guards while implementing facts.

## 7. Time-critical runbook (all times IST)

| Date | My focus | Team checkpoint |
|---|---|---|
| **12 Oct (Day 0)** | PWA mocked starter; fixture samples; contract review | Repo foundation and GPU path started |
| **13 Oct (Day 1, today)** | `T09.1`, `T04.4` (after `T03.1`), facts/benchmark fixtures | **G1:** app + model + MCP/tool + Google connectivity evidenced |
| **14 Oct (Day 2)** | `T05.4/.5`, `T09.2/.3` mocked | **G2:** typed mandate + policy, unauthorized action never `allow` |
| **15 Oct (Day 3)** | Finish capsule/slots; `T09.4/.5`; prep read/inbound fixtures | **G3:** validated proposed action through MCP/direct tool, guards enforced |
| **16 Oct (Day 4)** | `T08.1/.2/.4`, connect PWA to real API, own `T10.1` | **14:00:** fake golden path; **19:00:** recorded live golden path (G4) |
| **17 Oct (Day 5)** | `T12.1`, `T13.2`, QA, demo assets | **12:00 hard feature freeze**, G5 two clean live runs |
| **18 Oct (Day 6)** | Final PWA acceptance, video/deck/submission | **16:00** internal submit; **20:30** hard deadline |

**Cut order if late:** cut optional Laya (`T12.5`, `T12.7`), Whisper (`T12.6`), Web Push and polish; reduce extractor/model breadth; keep deterministic safety, mandate/approval, executor, receipts and fake golden path intact. No new features after freeze. Problems with model or Evolus require a documented fallback, not relaxed guards.

## 8. Historical Day 1 action plan (13 October 2026)

Current session scope is the four Phase 0 tickets in §0/§6, explicitly authorized sequentially by the 2026-10-14 owner prompt. The older one-ticket/separate-session guidance below does not replace that request. Do not start new PWA/facts implementation in this session.

### Before coding (15–30 minutes)

- [ ] Open repo and `git status -sb`, identify any local/remote uncommitted changes; ask owner before overwriting.
- [ ] Confirm `docs/workbook/*.md` exist and are up to date, and `Makefile` / `apps/web` scaffold from `T01.1` exists.
- [ ] Ask Jairaj for `T03.1` status and the PWA/CSRF/OpenAPI contract readiness. Ask Rehan which mock payloads are stable; do not assume G0/G1 is green.
- [ ] Read `FEATURE_TICKETS` `T09.1` and context bundle **CTX-CORE**, `FRD` UI behavior, `BACKEND_SCHEMA` §§1,2,3.2,4.1 and `TRD` §16.5.
- [ ] Pick one ticket for the next Codex session. **First choice: `T09.1`, mocked-only**. If there is no frontend scaffold, stop before creating conflicting project structure and ask Jairaj or switch to unfinished `T00.6/.7` fixtures.

### Ticket T09.1 — complete only this ticket in its own branch/session

- [ ] Next.js App Router phone-first layout; login shell; headers/integration banner; kill-switch placeholder only.
- [ ] Typed API client derived from real OpenAPI if present; otherwise create **explicitly mock-only** types/fixtures, avoid guessed production schema.
- [ ] CSRF cookie header handling; 401 route guard to `/login?next=...`; explicit 403/409/5xx and offline/loading states.
- [ ] `usePolling(url, intervalMs, {etag})`, controlled MSW test server, service worker and manifest; no fabricated live network responses.
- [ ] Tests for login/401 redirect, CSRF header, poll cleanup/ETag/error behavior. Run `pnpm -C apps/web test`, `pnpm -C apps/web build`, relevant lint/typecheck, and `make check` if targets exist.
- [ ] Record a screenshot, test results and whether phone install/live login was **actually** verified. Create PR on `t09.1-pwa-shell`; do not claim live acceptance until real API works.

**T09.1 workbook acceptance:** installable Android Chrome PWA + login against real API in Compose. Until T05.1 auth exists, mark outcome **mock-only / live integration pending**, not DONE.

### Ticket T04.4 — *separate* coding session, only after `T03.1` merged

- [ ] Read ticket and context: CTX-CORE, `BACKEND_SCHEMA` §§7.1,7.2,7.10 and `TRD` §10.4.
- [ ] Implement pure `facts/placeholders.py`, `facts/money_format.py`, `facts/numbers.py`, `facts/dates.py`, `facts/offer.py`; coordinate precise domain money/fact types with Jairaj.
- [ ] Parse/validate/render `{{fact:…}}`, `{{offer:…}}` and approved slot placeholders with spans; strict source fact map, never model-invented numbers.
- [ ] Indian INR grouping (`₹4,56,000`), Decimal amounts; extraction for price, numeric/word percentages, dates, times, numeric units, with canonical values + spans.
- [ ] Offer arithmetic uses verified proposal base + allowed discount + catalog add-ons; `Decimal` and `ROUND_HALF_UP` whole-rupee rules per ticket.
- [ ] Write ≥60 extraction cases, span and rounding tests, and negative cases (`4.8 lakh`, `₹4,80,000/-`, `5%` vs `0.5%`, phone/year ≠ money, `2 quick questions` ≠ price). Run mypy strict and `make check`.
- [ ] PR on `t04.4-facts`; hand off public API and evidence to Jairaj for guard/action pipeline; mark done only on merged, passing checks.

**Never use a single implementation prompt to change both T09.1 and T04.4.** They are separate PRs, separately reviewed; they can be worked on in parallel only if repo and ownership allow isolated file paths.

### Day 1 proof expected (do not precheck)

- [ ] Mock PWA displays correctly on mobile width and passes its test/build.
- [ ] T04.4 tests pass once domain types available, and handoff to Jairaj recorded.
- [ ] G1 evidence gathered from Jairaj/Rehan: fresh clone/setup/check, GPU response and parser, Evolus↔MCP, OAuth/Gmail/Calendar behavior; record any missing capability as a blocker, **not** green.

## 9. Ticket execution contract — for every coding-agent session

1. Inspect repo, `git status`, upstream status and open PRs; do not overwrite another teammate's edits.
2. Read **this file** and canonical PROJECT_CONTEXT, then only the ticket's required source sections. Confirm dependencies.
3. Choose exactly one ticket and branch `t<id>-<slug>` (e.g. `t09.1-pwa-shell`). Establish the acceptance and safe file paths before code.
4. Implement **only** within that scope; write focused tests for new behavior; no unreviewed changes to contracts, database, state machines or external effects.
5. Use a branch/PR and report `make check`; if a check cannot run, state *why* with exact command/error; don't claim it passed.
6. Reviewer checks acceptance evidence, typed interfaces, safety and cross-team handoffs. Do not claim merged/approved until it is.
7. Update **this** file with facts observed: quick resume, ticket status, check results, open blockers, handoff ledger and a session log entry.
8. Propose exact changes to the canonical `docs/workbook/PROJECT_CONTEXT.md` (its §§14–20), to be applied on PR merge following its §19. Don't silently rewrite its frozen architectural details.
9. Report: changed files; tests run/result; evidence; unresolved/untested cases; risks; PR/commit link; next safe ticket.

**Stop-and-escalate format if a contract change is necessary:**

```
CONTRACT CHANGE REQUEST
Ticket: ...
Existing contract + source section: ...
Observed conflict: ...
Proposed exact change: ...
Schema/migration/security consequences: ...
Tests/snapshots needed: ...
Owners required: Jairaj, Rehan, YOU (as applicable)
Do not implement pending sign-off.
```

## 10. Workstation and repo checks (commands are probes, not success claims)

```bash
git status -sb
git log -5 --oneline
find docs/workbook -maxdepth 1 -type f | sort    # or PowerShell Get-ChildItem
find apps/web -maxdepth 2 -type f | head         # or PowerShell Get-ChildItem -Recurse
make setup      # only if standard tooling and prerequisites exist
make check      # record actual result
pnpm -C apps/web test
pnpm -C apps/web build
```

Use Windows/WSL equivalents as appropriate. If the repo differs, inspect `README`/`Makefile`; do not create an unrelated frontend or alter team scripts without approval. Treat `make check`/CI as the source of test truth.

## 11. External verification / risks dashboard

Do **not** mark as verified based on the Oct 6 workbook's `open` statuses; verify live state with owners and update canonical TRD §22.2.

| Item | Owner to ask | Local status | Evidence/location |
|---|---|---|---|
| G0 ready: credits/GPU route, Google consent, mailboxes, seed/scenarios, ADRs | Rehan + Jairaj + YOU | UNVERIFIED | Content prepared/validated; docs/team/phase0-verification.md has open proof items |
| G1: base repo/CI green, model serving, parser, MCP, Google spikes | Team | UNKNOWN | — |
| EV-01…06 (Evolus MCP, workflow/subagents, model/parser/ROCm) | Rehan | UNKNOWN | — |
| EV-07…10 (AMD billing/credits, kickoff rules, uptime, workspace expiry) | Rehan + organizers | UNKNOWN | — |
| EV-11…13 / EV-21 (Gmail drafts, OAuth expiry, Calendar ID, OOO classification) | Jairaj | UNKNOWN | — |
| EV-15 optional Laya; proposed channel router | Rehan + YOU | NOT P0 | — |
| Demo seeded fact agreement, including D1 contradictory PDF timeline | YOU + Jairaj + Rehan | LOCALLY VALIDATED / TEAM REVIEW PENDING | docs/phase0/T00.6_HANDOFF.md; conflict preserved, no human sign-off |
| Real OpenAPI version used by web typed client | Jairaj | UNKNOWN | — |

**Leading risks:** schedule overrun; late G1 GPU/MCP issues; mock UI mistaken for working system; generated constants that contradict backend; unsafe action authorization; mismatched demo facts; OAuth/Google edge behavior. Prioritize reproducible golden path over breadth.

## 12. Decisions, blockers, PRs and evidence — append as facts appear

### Approved decisions since this file was initialized

None **independently verified after 2026-10-06**. Older decisions are in canonical PROJECT_CONTEXT §16 and ADRs. Never duplicate an old documented design choice as a newly confirmed build decision.

T00.8 prepared docs/adr/ADR-0001.md through ADR-0012.md from DEVELOPMENT_PLAN §15 on 2026-10-14; all remain Proposed / pending team review. Source/runtime deviations are open in docs/phase0/architecture-deviation-review.md. No newly approved architecture decision.

### Active blockers

| ID | Blocker / question | Owner | Date opened | Next action | State |
|---|---|---|---|---|---|
| B-001 | Existing React/Vite frontend differs from Next.js workbook plan; approved foundation status unverified | Jairaj + Rehan + YOU | 2026-10-14 | Review DEV-01; supply approved stack/API snapshots | REVIEW PENDING |
| B-002 | Domain/facts modules exist; official domain/guard compatibility and test acceptance unverified | Jairaj | 2026-10-14 | Review DEV-02/03; supply stable types/contracts | REVIEW PENDING |
| B-003 | Are G0 docs/credits/OAuth prerequisites complete? | Team | 2026-10-13 | Verify with owners and links | UNVERIFIED |
| B-004 | Nine canonical workbook Markdown originals missing; ADR sign-off absent | Team | 2026-10-14 | Supply exact originals and reviewed decisions | BLOCKED SOURCE HANDOFF |
| B-005 | make absent; Makefile/pyproject contain prose; normal pytest TOML parse error; diagnostic suite has 3 existing fixture failures | Jairaj + Rehan | 2026-10-14 | Owner-reviewed tooling and fixture-test repair; temporary-config 81 pass / 3 fail is not full make check | BLOCKED FULL CHECKS |
| B-006 | 84-case OR/conditional/sequence/predicate conventions need harness mapping | YOU + Jairaj | 2026-10-14 | Review bench README/questions before T12.1 scoring | REVIEW PENDING |
| B-007 | Apache license vs MIT source/event requirement | Rehan + all owners | 2026-10-14 | Organizer/contributor review; no unilateral relicensing | OPEN |

### Recent PRs / tests

| Date/time IST | Ticket | Branch / PR | Tests / observed outcome | Reviewer | State |
|---|---|---|---|---|---|
| 2026-10-14 02:13 IST | T00.2/.6/.7/.8 | t00-phase0-product-integration; no PR | Demo/spec/document checks pass; make absent; pytest blocked before collection by invalid TOML | Jairaj + Rehan pending | LOCAL CONTENT VALIDATION |
| 2026-10-14 02:21 IST | Day 2 reassessment / same Phase 0 scope | Same branch/HEAD; no PR | Four Phase 0 validators pass; temporary-config Python diagnostic: 81 pass / 3 fail in existing fixture assertions; remote main unchanged | Owners review pending | DIAGNOSTIC ONLY / FULL CHECKS BLOCKED |
| 2026-10-14 IST | Phase 0 publication | Ticket commits 1afde8a / 90eaebb / ab54c23 / eb193aa | Four content validators pass; Git-stored document/source hashes checked; no full check or approval claim | Team review pending | COMMITTED LOCALLY / PUSH AUTO-REVIEW REJECTED |

### Metrics / demo proofs

| Proof | Evidence path/link | Actual observed result |
|---|---|---|
| Fresh clone and `make check` | — | UNKNOWN |
| PWA mocked login/screens | — | UNKNOWN |
| Existing facts/formatter/example tests | docs/phase0/DAY2_REASSESSMENT.md | 50 passed under temporary diagnostic config; full canonical extraction/grounding/T04.4 acceptance unverified |
| G1 model/MCP/Google smoke | — | UNKNOWN |
| G4 fake golden path (`make demo-check`) | — | UNKNOWN |
| G4 live recorded run | — | UNKNOWN |
| G5 rehearsals | — | UNKNOWN |

### Phase 0 evidence observed on 2026-10-14

- `python scripts/phase0/validate_demo_content.py`: exit 0; ten YAML, refs/units/catalog, hashes, three PDFs/six pages, conflict/OOO/quiet/trust/relative-calendar/email checks. All six regenerated pages visually reviewed.
- `python bench/validate_scenarios.py`: exit 0; 84 unique source IDs across ten categories, founder involvement 41 required / 34 not_required / 9 optional. Twelve cases source-reviewed; independent random-ten human review pending.
- `python scripts/phase0/validate_phase0_documents.py`: exit 0; twelve exact proposed ADR decisions, source hashes/copy, canonical inventory, local links, seven beats and five gate criteria.
- `make check`: failed to start because make is not installed. `python -m pytest tests/ -q`: failed before collection, existing pyproject.toml invalid at line 3 column 14. No baseline/application tests passed or executed in this session. Frontend/DB/model/live tests not run.

## 13. Append-only session log (one verified entry per coding session)

> Keep the newest ~30 entries here, archive older ones to `docs/session-log-archive.md`. Update timestamps in IST. Entries should be concise, **evidence-led**, and carry an explicit next action. No long code, stack traces or secrets.

### Entry template (copy and fill)

```
- Date/time IST:
  Ticket + goal:
  Branch/commit/PR:
  Dependency check:
  Files changed:
  Code behavior delivered:
  Tests run / actual results:
  Manual acceptance / screenshot:
  Handoff + reviewer:
  Decisions / ADR required:
  Blockers or failures (owner):
  Status (mock-only/tested/PR-open/merged):
  Next exact task:
  Canonical PROJECT_CONTEXT §§14–20 update proposal:
```

### Known entries

- **2026-10-13 — Session planning only:** Created living engineering context and Day 1 prompts from supplied plans. **No repo inspected, no code written, no tests run and no status certified.** Next: inspect repo and begin T09.1 only after scaffold check.

## 14. Fast restart prompt to paste next time

```
Read context.md first and treat it as my session memory, not as authority over the canonical docs. I am the contributor marked YOU (Product + Integration Engineer). Inspect git/PR state and canonical PROJECT_CONTEXT + exact FEATURE_TICKET before any change. Tell me the current verified status, the single highest-priority UNBLOCKED ticket I own, its dependencies, acceptance and safe file paths. Work on exactly that ticket, run its tests and make check, report evidence and then update context.md's quick resume, register, handoffs, blockers and session log. Propose exact PROJECT_CONTEXT.md §19 updates for PR merge. Never invent progress, touch teammate-owned code without coordination or relax security contracts. Today’s date/time must be verified when used in status updates.
```

---

**Source references for maintainers:** `AI-Chief-of-Staff-Workbook(2).pdf` pp. 2–10 (PROJECT_CONTEXT), 168–202 (FEATURE_TICKETS), 203–238 (DEVELOPMENT_PLAN); `DEVELOPMENT_PLAN (1)(1).md` §§1–4, 9–11, 15; `AI_Chief_of_Staff_3_Person_Daily_Workload_Plan (3)(1).pdf` pp. 1–12. This companion does not replace the team's exact full source text.


### 2026-10-13 ? T00.6 portable content session

- Repository state: local Chief-of-Staff Git checkout exists, `main`, HEAD `071323f` (initial license-only commit), origin configured. Application scaffold, backend, database models, APIs and tests are unavailable. No remote freshness claim, commit, PR or merge.
- Accessible sources: AI-Chief-of-Staff-Workbook.pdf, DEVELOPMENT_PLAN.md, AI_Chief_of_Staff_Daily_Workload_Plan_Jayraj_Corrected.pdf, context.md. Names differ from pasted upload names; inspected content includes T00.6/T00.7, demo ??9.1/9.3, benchmark ??10.2-10.3, relevant database/backend schema, and three-person ownership. Workload spells Jayraj; session spells Jairaj.
- Ticket/status: ONLY T00.6 authored and locally content-validated; team review and T03.6 import acceptance pending. T00.7 not implemented. No canonical PROJECT_CONTEXT.md modified.
- Files created: t00.6-portable/README.md and VERIFICATION.md; seed/demo/{workspace,founder,companies,contacts,deals,proposals,catalog,calendar,threads,documents}.yaml; seed/demo/proposals/PR-{1,2,3}.{md,pdf}; knowledge/{services,faq,pricing}.md. Render intermediates are in tmp/pdfs/t00.6/ and are not handoff content.
- Verification: all 10 YAML parse; cross-entity references and primary memberships resolve; catalog prices/flags and five proposal values match source; mailbox scan permits only placeholders/seed.invalid; OOO stays outside human activity; independent content sweep selects D-1/D-3/D-4 with D-4 approval-required; D-2/D-5/D-6 excluded. PDF text confirms prices and PR-1 six/eight-week conflict on pages 2/4. All six rendered pages visually inspected via PDFium. SHA-256/byte-size metadata verified. No make check, database, integration, CI or live external tests attempted.
- Assumptions/open questions: relative dates and symbolic refs are authoring conventions for importer mapping, not frozen production contracts. Synthetic wording, D-2 recent exchange dates, D-5 proposal age and two extra calendar blocks are documented fixture details. PR-4/PR-5 missing commercial details remain unspecified. Retention/certifications/contractual data handling require founder confirmation. Fixture verified terms are desired demo state, not proof of actual human review. Confirm source variants and name spelling at review.
- Dependencies: Jairaj reviews financial facts, domain/schema/safety semantics and supplies T03.1 + scaffold/contracts; Rehan owns T03.6 import/reset, adapters, live mailbox/vacation-responder/Calendar setup. No teammate messages sent.
- Move later: t00.6-portable/seed/demo/ and knowledge/ into the shared application repository; place README/VERIFICATION in team-agreed handoff docs. Importer allocates UUIDs/seqs/defaults, resolves secure mailbox config and relative times, stores documents, and preserves timeline conflict. Do not integrate review PNGs or real addresses.
- Next exact action: team review of T00.6. After review, T00.7 benchmark specifications in a separate coding session. T04.4 waits for Jairaj T03.1; T09.1 waits for Next.js scaffold and API contracts.
- Canonical update proposal only: record T00.6 authored/local checks passed/review pending, portable artifact paths, absent application foundation and T03.6 handoff; no MERGED or live-test claim.

### 2026-10-14 02:13 IST — Phase 0 owner deliverables

- Scope: read context.md, supplied full Phase 0 prompt (received mid-session), development plan, corrected workload, relevant official workbook sections, existing portable content and safety fixtures/code. No PWA/facts/guard/backend changes made.
- Repository: starting main/HEAD fecad8b; review branch t00-phase0-product-integration in original checkout. Existing two modified summaries and untracked user sources preserved. No staging, commit, PR, push, merge or phase tag. Remote configured; no freshness/public-access claim.
- T00.2 PREPARED: docs/team/phase0-verification.md and docs/phase0/T00.2-registration-and-questions.md contain proof ledger, public-source references, EV-08/09/10/17/19 and eligibility questions. No registration/posting/answer/approval performed.
- T00.6 LOCALLY VALIDATED: reused portable assets, repaired confirmed INR/source-punctuation encoding defects, re-exported three PDFs and refreshed hashes. docs/phase0/T00.6_HANDOFF.md records exact inventory/mapping/review questions. No competing seed tree; commercial values and PR-1 conflict preserved. Import/reset/team review pending.
- T00.7 LOCALLY VALIDATED: 84 bench/scenarios files, read-only validator, bench README and SCENARIO_CATALOG_VERIFICATION.md. Source alternatives and conditional meanings preserved; twelve cases reviewed across all categories; three negative linter probes rejected. No benchmark/model executed. Jairaj random-ten review and YOU/T12.1 DSL/scorer mapping pending.
- T00.8 PREPARED / DOCUMENT-VALIDATED: twelve proposed ADRs; one-page Markdown acceptance brief; beats 0-6; workbook README/manifests; byte-identical standalone DEVELOPMENT_PLAN copy; architecture deviations and proposed PROJECT_CONTEXT §§14-20 updates. Nine canonical Markdown originals missing; safety/platform approval and freeze pending.
- Verification: content/spec/document validators exit 0. Six rendered proposal pages visually inspected. make absent; pytest cannot parse existing pyproject.toml (line 3 column 14), so no application tests executed. Existing guard registry/frontend/layout/license/check-tooling conflicts documented, untouched.
- Preservation: all 92 baseline files retained; 78 protected files byte-identical; 14 authorized edits limited to context.md and exact T00.6 encoding/PDF/metadata repair paths. docs/phase0/preservation-report.json and ARTIFACT_MANIFEST.md record evidence and exact per-ticket paths. git diff --check reports only whitespace in the two original dirty summaries; no unrelated repair.
- Reviewers: Jairaj financial/safety/ADRs/scenarios; Rehan content/importer/platform/runtime; YOU organizer/registration proof and product acceptance. No teammate messages sent; handoffs prepared locally.
- Next exact action: supply canonical originals and account/organizer proof; independent scenario/financial/ADR review; confirm T03.6 importer and T12.1 authoring semantics. No new production engineering ticket is independently verified unblocked. T09.2 mocked work needs source/interface alignment; T05.4/.5 and T12.1 still need their official dependencies. Do not recreate existing T04.4/T09.1.
- Canonical update proposal: docs/phase0/PROJECT_CONTEXT-proposed-updates.md; apply only through reviewed human merge workflow, with actual PR/evidence links.

### 2026-10-14 02:21 IST — Day 2 follow-up reassessment

- Read full attached follow-up prompt; continued the same four Phase 0 tickets without restarting authoring or modifying teammate Day 2 areas.
- Repo: same fecad8b/review branch, empty index, original dirty summaries/untracked sources intact. Live ls-remote exposes only main at fecad8b. Existing stash inspected by path only, never applied/dropped. No newer Day 2 service/loader commits visible; user-reported work may exist in unpublished/separate checkouts and is not declared incomplete elsewhere.
- Existing evidence: domain/facts modules, guard description registry, React/Vite frontend, 24 safety cases and Google spike remain. No T03.6 seed loader/integrated dataset, migrations/repos/audit, mandate/policy/auth/task services, inbound flags/OAuth worker implementation or approved teammate ADR found here. No live spike run.
- Phase 0: ten seed YAML and all 84 scenarios revalidate; 12 proposed ADRs/product/source documents validate. Prior PDFs unchanged; previous six-page visual review retained. Human registration/proof, financial/independent-scenario/ADR review and nine source originals remain open. Rehan importer compatibility cannot be claimed until exact loader interfaces/reset tests arrive.
- New diagnostic test evidence: `python -X utf8 -m pytest -c tmp/phase0-followup/pytest-diagnostic.ini --rootdir=. tests/ -q` using an empty ASCII temp config: 81 passed, 3 failed, exit 1. All 50 facts/formatter/example tests pass; 31 of 34 existing fixture validators pass. Failures: group filename lowercase vs uppercase IDs; B002 outside asserted paise range; A004 .com sender outside asserted Indian TLD list. Tests/fixtures/code/config left untouched. Normal pytest still fails TOML parsing; make absent; no full repository pass.
- Files changed: docs/phase0/DAY2_REASSESSMENT.md added; T00.6_HANDOFF.md, VERIFICATION.md, IMPLEMENTATION_REPORT.md, PROJECT_CONTEXT-proposed-updates.md, architecture-deviation-review.md, ARTIFACT_MANIFEST.md and context.md updated with current evidence. No seed/spec/PDF/ADR/validation-script changes. All 132 existing deliverable files match the follow-up hash baseline; 78 original protected files remain byte-identical.
- Handoff: Jairaj reviews existing fixture test failures and supplies task/capsule/facts contracts; Rehan supplies loader commit/layout and fake reset proof. No team-owned ticket marked complete and no messages/approvals performed.
- Next recommendation: T05.4 after T05.2 and canonical facts/capsule interfaces are available/reviewed. T05.5 awaits T05.2/T03.1/token/calendar interfaces; PWA work awaits approved stack/API/toolchain. Current unblocked work remains Phase 0 human review/proof and read-only inspection of published teammate commits.

### 2026-10-14 IST — Commit/push request

- User explicitly requested commit and push. Created separate local commits: T00.2 1afde8a, T00.6 90eaebb, T00.7 ab54c23, T00.8 eb193aa. A final audit/context commit packages current evidence. No teammate summary edits staged; no backend/frontend/tests/fixture/config/license changes in commits.
- Included existing portable source dataset and the supplied workbook/workload PDFs plus standalone plan so links and content validators are usable from Git. Added scoped .gitattributes to preserve bytes of hashed Markdown sources. Committed source/document hashes verified; content checks remain source-only. No team sign-off, full checks or merge claimed.
- Push to origin/t00-phase0-product-integration rejected by automatic approval review: destination/payload confirmation needed before externally publishing potentially sensitive workbook, seed and project documents. No bypass and no successful push. Exact scope/status in docs/phase0/PUBLICATION_STATUS.md.
- Next action: obtain explicit confirmation that all Phase 0 source/demo/spec/document/context assets may be published to https://github.com/JayDhole16/Chief-of-Staff on this review branch, then retry the same authorized push and verify remote HEAD. Existing human/architecture/dependency blockers remain.

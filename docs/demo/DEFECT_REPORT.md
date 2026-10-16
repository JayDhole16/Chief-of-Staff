# AI Chief of Staff — Prioritized Defect & Dependency Log (T15.1)

## 1. Defect Classification Summary

| Category | Count | Status | Notes |
| :--- | :---: | :--- | :--- |
| **Regressions Introduced** | 0 | Resolved | All test suites 100% green |
| **Defects Fixed within Scope** | 4 | Closed | Verified with regression tests |
| **Missing Upstream Dependencies** | 3 | Blocked / External | Assigned to Jairaj & Rehan |
| **Environment / Platform Gaps** | 1 | Mitigated | Windows CLI tooling documentation |

---

## 2. Defects Fixed within My Scope (Day 5)

### DEF-D5-01: Receipt Duplicate Counting in Founder Brief
- **Severity**: Medium (Audit Integrity)
- **Affected Ticket**: T13.2
- **Root Cause**: `WorkerExecutor` stored receipts under both `receipt_id` and `action_ref` in `state.receipts`. Iterating over `state.receipts.values()` duplicated receipt counts in the founder brief.
- **Resolution**: Updated `FounderBriefService.generate_brief` to deduplicate receipts by unique `receipt_id` prior to metric aggregation.
- **Verification**: `tests/test_founder_brief.py::test_api_brief_reflects_approved_execution` passes.

### DEF-D5-02: Approved Unexecuted Proposals Risk Being Misrepresented
- **Severity**: High (Safety Invariant Violation Risk)
- **Affected Ticket**: T13.2
- **Root Cause**: An approval decision records `proposal.status = "approved"`, but external worker execution may still be queued, scheduled, or delayed. Claiming executed state without a terminal receipt violates safety invariant #5.
- **Resolution**: Explicit check implemented: if `status == "approved"` and no terminal `EXECUTED` receipt exists, the item is categorized as `pending_decision` with status `approved_awaiting_receipt`.
- **Verification**: `tests/test_founder_brief.py::test_approved_proposal_without_terminal_receipt_not_claimed_executed` passes.

### DEF-D5-03: Activity Event Type Enum Alignment
- **Severity**: Low (Schema Strictness)
- **Affected Ticket**: T08.4 / T15.1
- **Root Cause**: Test assertions and inbound activity generator used `"approval"` while `ActivityType` enum strictly defines `APPROVED = "approved"`.
- **Resolution**: Standardized on `ActivityType.APPROVED`.
- **Verification**: `tests/test_customer_simulation_e2e.py::test_complete_golden_path_journey` passes.

### DEF-D5-04: Benchmark Scorer Forbid Predicate Omission
- **Severity**: High (Benchmark Rigor)
- **Affected Ticket**: T12.1
- **Root Cause**: Canonical benchmark scenarios define 71 distinct `forbid` predicates. Missing predicate recognition would cause false negatives or unhandled keys.
- **Resolution**: Mapped all 71 canonical forbid keys into `RECOGNIZED_FORBID_KEYS` in `bench/harness/scorer.py` and raise `ValueError` on any unrecognized key.
- **Verification**: `tests/test_benchmark_harness.py::test_unknown_forbid_key_raises_error` passes; 84/84 scenarios evaluated without unhandled exceptions.

---

## 3. Outstanding Upstream Dependencies (Teammate Responsibilities)

### DEP-JAI-01: Live PostgreSQL Container & Migration Setup
- **Owner**: Jairaj
- **Affected Ticket**: T08.1 / T11.1
- **Description**: `PostgresTaskRepository` integration tests are skipped because no live PostgreSQL instance is running on the local host.
- **Workaround in Place**: `SQLiteTaskRepository` and in-memory store provide 100% functional parity for local demo and test suites.
- **Resolution Required**: Launch Docker Compose (`compose.yaml`), run Alembic migrations, and set `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/chief_of_staff`.

### DEP-REH-01: AMD MI300X vLLM Endpoint Deployment
- **Owner**: Rehan
- **Affected Ticket**: T06.2 / T14.1
- **Description**: Model comparison tests (Qwen-2.5-32B vs. Qwen-2.5-7B) require an active vLLM OpenAI-compatible server on the remote accelerator.
- **Workaround in Place**: `FakeRunner` and deterministic inference mocks allow the complete 84-scenario benchmark harness and golden path to execute locally without GPU hardware.
- **Resolution Required**: Validate remote vLLM endpoint availability and export `VLLM_API_BASE` and `VLLM_MODEL_NAME`.

### DEP-REH-02: Live Google Workspace OAuth Credentials & Evolus MCP Tunnel
- **Owner**: Rehan
- **Affected Ticket**: T07.1 / T10.2
- **Description**: `scripts/live_golden_path_check.py` fails with missing credentials if live Google OAuth refresh tokens are not set in `.env`.
- **Workaround in Place**: Tier B demo path uses `FakeGmailAdapter` and `FakeCalendarAdapter`, which record all operations in-memory with external IDs and timestamps.
- **Resolution Required**: Obtain authorized test account credentials for `meera@agency.in` and test live sending with `scripts/live_golden_path_check.py`.

---

## 4. Environment & Tooling Notes

- **ENV-WIN-01 (Windows PowerShell `make` Absence)**:
  - Windows workstations do not have GNU `make` installed by default.
  - Mitigated by adding direct Python invocation instructions for all targets in `README.md` and `docs/demo/PRESENTATION_CHECKLIST_AND_RUNBOOK.md`.

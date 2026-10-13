# Architecture and source deviation review requests

Date: 2026-10-14 IST. Status: **open; no contract change approved or implemented**. Source: DEVELOPMENT_PLAN §15; workbook PROJECT_CONTEXT §§5,12, TRD §2.4/§10.2, BACKEND_SCHEMA §12.1. All teammate code preserved.

| Request | Observed code / source conflict | Required decision / evidence | Owner |
|---|---|---|---|
| DEV-01 frontend stack | frontend/package.json uses React/Vite; workbook plans Next.js App Router, pnpm/Node22 and apps/web | Supply existing approved ADR, or review a separate stack/hosting/API-routing decision; no rewrite here | YOU + Jairaj + Rehan |
| DEV-02 backend layout | backend/{domain,facts,guards} and root pyproject use Python >=3.10; workbook plans Python3.12/uv/FastAPI at backend/src/founder_os with protected dependency rules | Confirm foundation status, approved deviations, authoritative types/snapshots and import-linter evidence. Module presence does not prove T03.1/T01.1 done. | Jairaj + Rehan |
| DEV-03 guard registry | Existing G01=session, G03=amount, G11=floor, G12=opt-out, G15=grammar; official G01=schema, G03=freshness, G11=cross_context, G12=commitment_check, G15=slot_conflict | Reconcile in separate owner-reviewed work; preserved tests/fixtures cannot establish workbook guard acceptance. T00.7 uses workbook reasons. | Jairaj |
| DEV-04 license | Existing LICENSE is Apache2.0; workbook T00.5 MIT and public event page states MIT compliance | Organizer/contributor review; do not relicense other people's contributions unilaterally | Rehan + all owners + organizers |
| DEV-05 check infrastructure | Makefile and pyproject.toml contain prose; make executable absent; normal pytest fails TOML parsing at line 3 column 14; temporary-config diagnostic has 81 passed / 3 failed; expected architecture/contract snapshots missing | Restore/confirm check tooling and review three existing fixture-test failures; no full make check claim. See DAY2_REASSESSMENT.md for exact diagnostic evidence | Jairaj + Rehan |
| DEV-06 exact workbook sources | Nine canonical Markdown originals absent; PDF extraction contains lossy formatting/glyphs | Supply original files and current ADR/EV decisions. No reconstructed authoritative contracts | Team |
| DEV-07 scenario semantics | SCH-07 catalog reason PROCESS_NOT_IN_MANDATE vs booking-clause reason in schema; conditional alternatives/sequence predicates need harness mapping | Review fixture meaning and scorer conventions; preserve source alternatives until reviewed | Jairaj + YOU/T12.1 |

For any proposed implementation/contract change, provide: exact existing source section, observed discrepancy, proposed decision, effects on API/DB/state/security, required tests/snapshots/migrations, reviewer names and PR. Approved changes belong in a separate ADR/schema/snapshot PR and PROJECT_CONTEXT §16 before feature code. These proposed baseline ADRs do not approve deviations.

Safety sign-off requested from Jairaj: financial facts, conflicted terms, official guard/policy registry, scope and credential/executor invariants. Platform sign-off requested from Rehan: stack/runtime, AMD/Evolus requirements, importer mapping and actual deployment/tool evidence. Names/date/outcome/proof links: **pending**.

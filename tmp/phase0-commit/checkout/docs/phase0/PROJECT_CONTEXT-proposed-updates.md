# Proposed PROJECT_CONTEXT §§14-20 updates

For the human merger after the exact canonical original is supplied. **Not applied; no approval or merge implied.** Date: 2026-10-14 IST. Working branch t00-phase0-product-integration, base HEAD fecad8b, no task commit/PR/push.

Day 2 addendum for §§14/17/20: live remote-head check exposes only main at fecad8b; no new Day 2 implementation available in this checkout. Four Phase 0 validators pass; temporary-config diagnostic tests: 81 passed / 3 failed (existing fixture naming/price-range/domain assertions). Normal repository config remains broken; no full check/ticket completion claim. T03.6/T05.2 and canonical capsule/domain interfaces remain unavailable/unconfirmed. T05.4 is the next recommended implementation only after its dependencies are reviewed. See DAY2_REASSESSMENT.md for exact evidence and owner handoffs; do not replace approved project decisions with this addendum.

## §14 Environments and commands

Observed local content commands: `python scripts/phase0/validate_demo_content.py` and `python bench/validate_scenarios.py` pass. Document validator checks ADR/source/link/beat/gate preparation after all documents exist. No DB/GPU/live URL/time measurements available. `make check` cannot run because make is absent. `python -m pytest tests/ -q` stops before collection because pyproject.toml is invalid at line 3 column 14. Do not substitute source checks for full make check.

## §15 Status and owners

Phase 0 remains in progress; G0 unverified, no phase tag. Proposed owner assignment from corrected workload p.12: YOU T00.2/.6/.7/.8; Jairaj safety/financial/ADR review and T00.4; Rehan platform/AMD/Evolus and T03.6 importer. T00.2 prepared, external proof open. T00.6 prepared/locally validated, content review/importer pending. T00.7 84 specifications locally validated, independent random-ten review and runner mapping pending. T00.8 12 proposed ADRs/product docs/manifest prepared, nine originals missing and team freeze sign-off pending. No ticket marked merged or system-tested.

## §16 Decisions

No new approved architecture decision. ADR-0001..0012 record DEVELOPMENT_PLAN §15 verbatim with proposed/pending status. Do not treat React/Vite, backend layout, current guard registry or license as approved alternatives. Scenario OR/conditional expectations, fixture setup/sequences and forbid predicates are authoring proposals requiring T12.1/Jairaj review, not API changes.

## §17 Known problems

Jairaj/Rehan: React/Vite vs Next.js; backend layout/toolchain differs; existing guard IDs/descriptions conflict with official registry. Rehan/team: Apache license vs MIT source/event requirement. Jairaj/Rehan: Makefile is prose; pyproject.toml contains non-TOML prose; baseline checks cannot run. Team: nine exact canonical Markdown originals missing. YOU/Jairaj: SCH-07 catalog/booking-reason ambiguity and harness alternative semantics. Rehan: T03.6 compatibility/reset and live integration unverified. See architecture-deviation-review.md for review requests; no unrelated code repaired.

## §18 External verification

Keep EV-08/09/10/17/19 open unless the team supplies actual posted-question/organizer-answer evidence. Rehan eligibility decision, enrollment/roster/Discord/workspace access, AMD GPU route, OAuth/mailboxes and submission cutoff need proof. Public event requirements were researched but cannot certify account actions. Copy actual future answers into both this section and TRD §22.2.

## §19 Update procedure

Follow the original human-merger workflow. Insert reviewed status/evidence in the same PR/after merge, record real commit/PR links, and keep decisions/sources authoritative. This proposal does not change that procedure.

## §20 Session log proposal

- 2026-10-14 IST · T00.2/.6/.7/.8 · YOU + Codex · base fecad8b, t00-phase0-product-integration, no commit/PR · preserved teammate files; prepared human verification/questions; repaired verified demo INR encoding and revalidated ten YAML/three PDFs (six pages); authored/linted 84 scenarios with source-preserved alternatives and reviewed 12 across all categories; prepared twelve proposed ADRs, acceptance/beat map, exact standalone plan copy and missing-source manifest · checks: content/spec/document validation; full make check blocked by absent executable and pytest blocked by invalid existing TOML · approvals/live results: none · next: Jairaj financial/safety/independent-scenario review, Rehan importer/platform review, team canonical originals and organizer proof.

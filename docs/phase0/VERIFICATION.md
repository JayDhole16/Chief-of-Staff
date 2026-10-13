# Phase 0 verification evidence

Date: 2026-10-14 IST. No application/system acceptance, benchmark result, external action, human approval or merge is claimed.

## Day 2 follow-up evidence

Read-only remote-head check succeeded: only main at fecad8b; no newer published Day 2 branch available. All four Phase 0 validators pass. Existing tests were executed under a temporary empty ASCII pytest config without changing project files: `python -X utf8 -m pytest -c tmp/phase0-followup/pytest-diagnostic.ini --rootdir=. tests/ -q` returned **81 passed, 3 failed**, exit 1. Failures are existing fixture naming, price-range and domain assertions; exact files and proposed owner actions are in [DAY2_REASSESSMENT.md](DAY2_REASSESSMENT.md). Normal pytest remains blocked by invalid project TOML; this diagnostic run is not a full repository check. No seed/spec/PDF/ADR changes in this follow-up.

The original-session evidence table below records the earlier attempts; its no-application-tests statement applies to that earlier session. The diagnostic run above is new evidence and does not establish system acceptance.

## Original Phase 0 session checks

| Command / review | Observed result | Limit |
|---|---|---|
| python scripts/phase0/validate_demo_content.py | Exit 0 | 10 YAML, inventories/unique refs/relations, currency units, catalog, PDF amounts/pages, hashes, OOO/quiet/trust, relative times and safe placeholders; no importer/DB execution |
| PDFium render + visual review | All six regenerated pages inspected | Actual PR-1 conflict on pages 2/4, rupee glyphs/figures legible; local layout only |
| python bench/validate_scenarios.py | Exit 0 | 84 unique IDs; counts FUP10 SCH10 NEG-IN8 NEG-OVER8 IDN12 INJ10 SEN8 AUT6 KNW6 STL6; founder 41 required / 34 not_required / 9 optional; source fields/shape/status/ref/address checks; no AI run |
| Linter negative probes, in memory | Three invalid examples rejected | Duplicate YAML mapping key; pending_approval/allow mismatch; invalid action status; no scenario mutated |
| Spec source review | 12 specified cases inspected across ten categories | See bench/SCENARIO_CATALOG_VERIFICATION.md; independent random-ten human review still pending |
| python scripts/phase0/validate_phase0_documents.py | Exit 0 | 12 proposed ADRs exactly match source decisions, source hashes/byte-identical plan copy, 10-source inventory (9 missing originals), local links, 7 beats and 5 gates |
| make check | Cannot start, exit 1 | PowerShell CommandNotFoundException: make unavailable; no full checks passed |
| python -m pytest tests/ -q | Exit 1 before collection | Existing pyproject.toml: Expected '=' after a key in a key/value pair, line 3 column 14; no application tests executed |
| git diff --check | Reports preexisting whitespace defects | Only SAFETY_HARNESS_SUMMARY.md and T09.1_SUMMARY.md; both preserved byte for byte |
| python scripts/phase0/verify_preservation.py | Baseline comparison recorded in preservation-report.json | Original file hashes captured before authored changes; only root context and exact T00.6 repair paths authorized |

The existing pyproject.toml and Makefile contain prose. Repair requires teammate foundation scope, not this content task. Frontend builds/tests, DB resets/migrations, models, live Gmail/Calendar, CI and all phase gates were not run/certified. Full check failures do not invalidate the independently observed content checks, and content checks do not establish system acceptance.

Source PDFs, standalone development plan, backend/frontend, safety fixtures/tests and both originally dirty summaries are protected by the baseline. New documents remain unstaged; no commit, PR, push, merge or freeze tag. Generated/render/extraction intermediates under tmp/ are excluded from the handoff manifest.

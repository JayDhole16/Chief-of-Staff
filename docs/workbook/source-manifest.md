# Source manifest

Checked: 2026-10-14 IST. Exact SHA-256 and sizes are in source-manifest.json and are verified by the Phase 0 document checker.

| Source | Present location / state |
|---|---|
| Official combined workbook | Root AI-Chief-of-Staff-Workbook.pdf, 238 pages; local original preserved, ignored and not published |
| Three-person corrected workload | Root AI_Chief_of_Staff_Daily_Workload_Plan_Jayraj_Corrected.pdf, 12 pages; local original preserved, ignored and not published |
| Standalone development plan | Root DEVELOPMENT_PLAN.md; byte-identical copy docs/workbook/DEVELOPMENT_PLAN.md |
| Personal session memory | Root context.md; mutable operator companion, not canonical project authority |
| Phase 0 owner prompt | Supplied in full in user message during this session; read completely; no invented attachment path |

| Required canonical document | Exact individual Markdown present? | Official PDF pages | Human handoff |
|---|---|---|---|
| PROJECT_CONTEXT.md | No | 2-10 | Supply living canonical original, including current decisions/status |
| PRD.md | No | 11-16 | Supply original |
| SRS.md | No | 17-30 | Supply original |
| FRD.md | No | 31-39 | Supply original |
| TRD.md | No | 40-73 | Supply original and verified EV updates |
| ARCHITECTURE.md | No | 74-94 | Supply original diagrams/module map |
| DATABASE_SCHEMA.md | No | 95-130 | Supply exact table/constraint/query source |
| BACKEND_SCHEMA.md | No | 131-167 | Supply exact APIs/tools/states/reasons |
| FEATURE_TICKETS.md | No | 168-202 | Supply original |
| DEVELOPMENT_PLAN.md | **Yes**, supplied standalone copy | 203-238 | Compare standalone/PDF versions at team review; no automatic equivalence claim |

Nine missing originals block complete T00.8 workbook-source acceptance. Copies, ADR drafts and artifacts are uncommitted; no PR/merge exists. Full PDF extraction was generated locally for reference, but only task-relevant sections were reviewed; it was not promoted into docs/workbook. Neither historical workbook test claims nor source transcription prove present system behavior.

Publication update: user requested commit/push with the two workbook source PDFs excluded. Unpublished commits are rebuilt to exclude their blobs from branch history, while local originals remain. The standalone Markdown plan, three demo proposal PDFs, seed/spec/ADR/product/context assets are included. The validator checks local-only PDF hashes when available and explicitly reports their absence in a published checkout; all other required-source/hash/link checks remain enforced. No architecture approval or merge is implied by publication.

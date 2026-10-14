# Exact Phase 0 artifact manifest

Date: 2026-10-14 IST. Paths are relative to the existing repository. No files staged/committed/pushed. Original sources and unchanged portable files remain present but are not listed as new changes. tmp/ contains review/extraction/render intermediates only.

Publication update: the user subsequently authorized commit/push. Four ticket commits are local; push was rejected by automatic approval review pending explicit target/payload confirmation. See PUBLICATION_STATUS.md. The commit payload additionally tracks the existing portable dataset and supplied sources so a fresh checkout is self-contained; those files were not recreated. .gitattributes preserves exact bytes for hashed Markdown sources.

Day 2 follow-up adds `docs/phase0/DAY2_REASSESSMENT.md` and updates `context.md`, `docs/phase0/T00.6_HANDOFF.md`, `VERIFICATION.md`, `IMPLEMENTATION_REPORT.md`, `PROJECT_CONTEXT-proposed-updates.md`, `architecture-deviation-review.md` and this manifest. The existing seed/scenario/ADR files and validation scripts are reused unchanged.

## T00.2 (2 files)

- NEW: `docs/phase0/T00.2-registration-and-questions.md`
- NEW: `docs/team/phase0-verification.md`

## T00.6 (18 files)

- NEW: `docs/phase0/T00.6-content-review.md`
- NEW: `docs/phase0/T00.6_HANDOFF.md`
- NEW: `scripts/phase0/render_demo_proposals.py`
- NEW: `scripts/phase0/repair_demo_encoding.py`
- NEW: `scripts/phase0/validate_demo_content.py`
- MODIFIED: `t00.6-portable/README.md`
- MODIFIED: `t00.6-portable/VERIFICATION.md`
- MODIFIED: `t00.6-portable/knowledge/faq.md`
- MODIFIED: `t00.6-portable/knowledge/pricing.md`
- MODIFIED: `t00.6-portable/knowledge/services.md`
- MODIFIED: `t00.6-portable/seed/demo/documents.yaml`
- MODIFIED: `t00.6-portable/seed/demo/proposals.yaml`
- MODIFIED: `t00.6-portable/seed/demo/proposals/PR-1.md`
- MODIFIED: `t00.6-portable/seed/demo/proposals/PR-1.pdf`
- MODIFIED: `t00.6-portable/seed/demo/proposals/PR-2.md`
- MODIFIED: `t00.6-portable/seed/demo/proposals/PR-2.pdf`
- MODIFIED: `t00.6-portable/seed/demo/proposals/PR-3.md`
- MODIFIED: `t00.6-portable/seed/demo/proposals/PR-3.pdf`

## T00.7 (87 files)

- NEW: `bench/README.md`
- NEW: `bench/SCENARIO_CATALOG_VERIFICATION.md`
- NEW: `bench/scenarios/automation_loops/AUT-01.yaml`
- NEW: `bench/scenarios/automation_loops/AUT-02.yaml`
- NEW: `bench/scenarios/automation_loops/AUT-03.yaml`
- NEW: `bench/scenarios/automation_loops/AUT-04.yaml`
- NEW: `bench/scenarios/automation_loops/AUT-05.yaml`
- NEW: `bench/scenarios/automation_loops/AUT-06.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-01.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-02.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-03.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-04.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-05.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-06.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-07.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-08.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-09.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-10.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-11.yaml`
- NEW: `bench/scenarios/identity_resolution/IDN-12.yaml`
- NEW: `bench/scenarios/knowledge_facts/KNW-01.yaml`
- NEW: `bench/scenarios/knowledge_facts/KNW-02.yaml`
- NEW: `bench/scenarios/knowledge_facts/KNW-03.yaml`
- NEW: `bench/scenarios/knowledge_facts/KNW-04.yaml`
- NEW: `bench/scenarios/knowledge_facts/KNW-05.yaml`
- NEW: `bench/scenarios/knowledge_facts/KNW-06.yaml`
- NEW: `bench/scenarios/negotiation_over_mandate/NEG-OVER-01.yaml`
- NEW: `bench/scenarios/negotiation_over_mandate/NEG-OVER-02.yaml`
- NEW: `bench/scenarios/negotiation_over_mandate/NEG-OVER-03.yaml`
- NEW: `bench/scenarios/negotiation_over_mandate/NEG-OVER-04.yaml`
- NEW: `bench/scenarios/negotiation_over_mandate/NEG-OVER-05.yaml`
- NEW: `bench/scenarios/negotiation_over_mandate/NEG-OVER-06.yaml`
- NEW: `bench/scenarios/negotiation_over_mandate/NEG-OVER-07.yaml`
- NEW: `bench/scenarios/negotiation_over_mandate/NEG-OVER-08.yaml`
- NEW: `bench/scenarios/negotiation_within_mandate/NEG-IN-01.yaml`
- NEW: `bench/scenarios/negotiation_within_mandate/NEG-IN-02.yaml`
- NEW: `bench/scenarios/negotiation_within_mandate/NEG-IN-03.yaml`
- NEW: `bench/scenarios/negotiation_within_mandate/NEG-IN-04.yaml`
- NEW: `bench/scenarios/negotiation_within_mandate/NEG-IN-05.yaml`
- NEW: `bench/scenarios/negotiation_within_mandate/NEG-IN-06.yaml`
- NEW: `bench/scenarios/negotiation_within_mandate/NEG-IN-07.yaml`
- NEW: `bench/scenarios/negotiation_within_mandate/NEG-IN-08.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-01.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-02.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-03.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-04.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-05.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-06.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-07.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-08.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-09.yaml`
- NEW: `bench/scenarios/prompt_injection/INJ-10.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-01.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-02.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-03.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-04.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-05.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-06.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-07.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-08.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-09.yaml`
- NEW: `bench/scenarios/routine_followups/FUP-10.yaml`
- NEW: `bench/scenarios/scheduling/SCH-01.yaml`
- NEW: `bench/scenarios/scheduling/SCH-02.yaml`
- NEW: `bench/scenarios/scheduling/SCH-03.yaml`
- NEW: `bench/scenarios/scheduling/SCH-04.yaml`
- NEW: `bench/scenarios/scheduling/SCH-05.yaml`
- NEW: `bench/scenarios/scheduling/SCH-06.yaml`
- NEW: `bench/scenarios/scheduling/SCH-07.yaml`
- NEW: `bench/scenarios/scheduling/SCH-08.yaml`
- NEW: `bench/scenarios/scheduling/SCH-09.yaml`
- NEW: `bench/scenarios/scheduling/SCH-10.yaml`
- NEW: `bench/scenarios/sensitive_situations/SEN-01.yaml`
- NEW: `bench/scenarios/sensitive_situations/SEN-02.yaml`
- NEW: `bench/scenarios/sensitive_situations/SEN-03.yaml`
- NEW: `bench/scenarios/sensitive_situations/SEN-04.yaml`
- NEW: `bench/scenarios/sensitive_situations/SEN-05.yaml`
- NEW: `bench/scenarios/sensitive_situations/SEN-06.yaml`
- NEW: `bench/scenarios/sensitive_situations/SEN-07.yaml`
- NEW: `bench/scenarios/sensitive_situations/SEN-08.yaml`
- NEW: `bench/scenarios/stale_context_concurrency/STL-01.yaml`
- NEW: `bench/scenarios/stale_context_concurrency/STL-02.yaml`
- NEW: `bench/scenarios/stale_context_concurrency/STL-03.yaml`
- NEW: `bench/scenarios/stale_context_concurrency/STL-04.yaml`
- NEW: `bench/scenarios/stale_context_concurrency/STL-05.yaml`
- NEW: `bench/scenarios/stale_context_concurrency/STL-06.yaml`
- NEW: `bench/validate_scenarios.py`

## T00.8 (22 files)

- NEW: `docs/adr/ADR-0001.md`
- NEW: `docs/adr/ADR-0002.md`
- NEW: `docs/adr/ADR-0003.md`
- NEW: `docs/adr/ADR-0004.md`
- NEW: `docs/adr/ADR-0005.md`
- NEW: `docs/adr/ADR-0006.md`
- NEW: `docs/adr/ADR-0007.md`
- NEW: `docs/adr/ADR-0008.md`
- NEW: `docs/adr/ADR-0009.md`
- NEW: `docs/adr/ADR-0010.md`
- NEW: `docs/adr/ADR-0011.md`
- NEW: `docs/adr/ADR-0012.md`
- NEW: `docs/adr/README.md`
- NEW: `docs/phase0/PROJECT_CONTEXT-proposed-updates.md`
- NEW: `docs/phase0/architecture-deviation-review.md`
- NEW: `docs/product/acceptance-brief.md`
- NEW: `docs/product/demo-beats.md`
- NEW: `docs/workbook/DEVELOPMENT_PLAN.md`
- NEW: `docs/workbook/README.md`
- NEW: `docs/workbook/source-manifest.json`
- NEW: `docs/workbook/source-manifest.md`
- NEW: `scripts/phase0/validate_phase0_documents.py`

## Shared safety/context/report (10 files)

- MODIFIED: `context.md`
- NEW: `docs/phase0/ARTIFACT_MANIFEST.md`
- NEW: `docs/phase0/DAY2_REASSESSMENT.md`
- NEW: `docs/phase0/IMPLEMENTATION_REPORT.md`
- NEW: `docs/phase0/PUBLICATION_STATUS.md`
- NEW: `docs/phase0/VERIFICATION.md`
- NEW: `docs/phase0/preservation-baseline.json`
- NEW: `docs/phase0/preservation-report.json`
- NEW: `docs/phase0/repository-safety-inspection.md`
- NEW: `scripts/phase0/verify_preservation.py`

All 92 preexisting files remain; 78 protected files are byte-identical. The 14 authorized preexisting edits are context.md and the exact T00.6 encoding/document-repair paths. See preservation-report.json and VERIFICATION.md.

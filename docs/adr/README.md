# Architecture decisions awaiting team review

ADR-0001.md through ADR-0012.md transcribe the twelve decision rows in DEVELOPMENT_PLAN §15. Every status is Proposed / pending team review. They record the source plan and do not assert the current implementation complies. No frozen decision was amended.

Jairaj: review architecture, scope, deterministic policy/guard registry, credential/executor boundaries, state/audit integrity and demo financial trust. Rehan: review AMD/vLLM/Evolus runtime, port/adapters, queue/deployment and seed-import assumptions. YOU: review product behavior and evidence. Record reviewer name, date, outcome and PR link before changing an ADR to approved/accepted.

## Branches, PRs and handoffs

- One named owner and ticket per PR; branch `t<id>-<slug>` (for example `t00.7-scenarios`). Squash-merge title `T00.7: <description>` after applicable checks and human review. No force push to main; no sweeping dirty files into a task commit.
- Current session uses `t00-phase0-product-integration` as a review branch in the original checkout, with a preexisting-file hash baseline. Work is separated by ticket paths; no commit/push authorized. A clean worktree was not used because required user-provided sources and portable content were untracked in the original checkout. No teammate changes were stashed or removed.
- Future commit/PR boundaries: T00.2 team ledger/question drafts; T00.6 existing content repairs + validation + handoff; T00.7 scenarios/linter/catalog review; T00.8 ADR/product/workbook manifest/deviation/context proposals. Stage explicit reviewed paths only. Shared context.md session update can follow the final review.
- Contract changes are separate small PRs: reviewed ADR, all affected exact schema sources, migrations/snapshots where required, PROJECT_CONTEXT §16 entry, then feature implementation. Never edit merged migrations.
- Phase tags such as phase-0-freeze require proven gates and merged documents. No tag is created by drafting these files. PROJECT_CONTEXT updates follow its §19 after the human merger reviews them.

The original two-person plan is superseded for human ownership only by the corrected three-person plan: YOU owns T00.2/.6/.7/.8; Jairaj reviews safety; Rehan reviews platform and owns T03.6 importer. Technical contracts remain the official workbook's.

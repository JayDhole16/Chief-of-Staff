# T00.6 portable demo content

Status: authored and locally content-validated; team review and T03.6 import acceptance pending. No application, importer, schema, credentials or live external writes are included.

## Source authority

Read local AI-Chief-of-Staff-Workbook.pdf (238 pages), DEVELOPMENT_PLAN.md, AI_Chief_of_Staff_Daily_Workload_Plan_Jayraj_Corrected.pdf (12 pages), and ../context.md. These are local filename variants of the supplied source list. Exact upload filenames are unavailable. Workload pages 2, 3, 5 and 12 confirm the three-person split; the corrected PDF spells the safety owner Jayraj, while the session calls him Jairaj. No identity change is inferred.

Requirements: workbook FEATURE_TICKETS T00.6/T00.7 (PDF p.171); DEVELOPMENT_PLAN §9.1, 9.3, 10.2-10.3; DATABASE_SCHEMA §4.1-4.4 (PDF pp.97-107); BACKEND_SCHEMA §4.9 (PDF p.138). T00.7 was initially studied for context only; 84 separate specifications are now prepared under ../bench/scenarios, without duplicating seed assets.

## File inventory

- seed/demo/workspace.yaml: founder workspace and documented settings.
- seed/demo/founder.yaml: principal identity; no password or credential.
- seed/demo/companies.yaml: six companies, nullable unspecified domains.
- seed/demo/contacts.yaml: six contacts and primary mailbox mappings.
- seed/demo/deals.yaml: six deals plus primary deal/contact memberships.
- seed/demo/proposals.yaml: five proposals and structured financial terms; two conflicting timeline values.
- seed/demo/catalog.yaml: three SKUs, prices in paise, billing periods and add-on flags.
- seed/demo/calendar.yaml: planned busy blocks, buffers/grid and expected target slot; no seeded Google events.
- seed/demo/threads.yaml: four synthetic threads, 10 messages, OOO behavior, post-seed live replay intents and expected sweep.
- seed/demo/documents.yaml: document metadata, source paths, hashes and byte sizes.
- seed/demo/proposals/PR-1.md and PR-1.pdf: four pages; six weeks on page 2, eight weeks on page 4.
- seed/demo/proposals/PR-2.md and PR-2.pdf: invoice reconciliation, ₹2,40,000.
- seed/demo/proposals/PR-3.md and PR-3.pdf: appointment reminders, ₹3,20,000.
- knowledge/services.md, knowledge/faq.md, knowledge/pricing.md: grounded business knowledge.
- VERIFICATION.md: observed checks and limitations.

## Authoring conventions and T03.6 handoff

This YAML is authoring content, not a new production schema. The table-group names and fields follow DATABASE_SCHEMA where specified. `ref`, `*_ref`, `source_path`, calendar-plan fields, replay intents and sweep expectations are authoring annotations; do not store them blindly as new database columns. UUIDs, sequence refs, normalized addresses, storage paths, login credentials and row defaults are assigned by the real importer after contracts are available.

Resolve `anchor` to one reset instant in Asia/Kolkata. `-Nd` means N calendar days before that instant, preserving local wall time. `anchor_date` means its local date. `next:thu` is strictly the next Thursday after the anchor date; if reset occurs on Thursday, use the next week for these planned blocks. `target_day` is that resolved Thursday. Local block times use their stated timezone. `sent_at+30d` means proposal sent date plus 30 calendar days. Relative date strings must be converted before database insertion. Preserve message list ordering for equal relative dates; derive micro-ordering during import without changing day ages. Do not hard-code Oct 22: Oct 13 reset targets Oct 15, while Oct 16-18 targets Oct 22.

Money: catalog `price_minor` and deal `value_minor` are integer paise; `deal_terms.value_numeric` is a decimal INR amount in major units, as specified by DATABASE_SCHEMA. Do not add monthly and annual charges into an unlabeled total. For the scripted 5% counter, setup is ₹4,56,000; annual support is separately ₹60,000/year and monthly fee separately ₹15,000/month.

PR-1 has `terms_status: conflict`; its setup, monthly, payment and validity terms are verified fixture values, but both timeline entries remain `conflict` (distinct ordinals 0 and 1). Only verified terms may be trusted. The founder verification annotations represent the designed demo state, not evidence that a human reviewed these newly authored files. Preserve the conflict through import/extraction and capsule generation.

All D-1 contacts/proposals exist without a starting Gmail thread. TH-2..TH-5 are synthetic and have seed-prefixed identifiers. The executor must open a real new thread rather than sending into synthetic Gmail identifiers. OOO never updates human inbound activity. Lakshmi Iyer is only a forwarded-body mention, not a contact, deal participant or recipient.

Live mailbox placeholders are DEMO_FOUNDER_EMAIL, DEMO_EMAIL_RAJU, DEMO_EMAIL_PRIYA and DEMO_EMAIL_ARJUN. Resolve them in secured runtime configuration; do not write resolved addresses back to source files. Other addresses end in seed.invalid. Priya's live vacation responder and Arjun's team +arjun alias still need manual configuration. The replay intents are later demo stimuli, not seed messages; no active mandate, approval or external effect is pre-created.

Move this directory's seed/demo/ and knowledge/ into the shared repository when available. Keep this README and VERIFICATION.md with the handoff in a team-agreed documentation location. Rehan maps/imports the content for T03.6; Jairaj reviews domain/schema, verified facts and safety semantics. Recalculate hashes if documents change and preserve PDF page breaks when re-exporting Markdown.

## Assumptions and open questions

- Synthetic conversational wording, the D-2 recent exchange days and the two extra calendar blocks are fixture details, not commercial promises. D-5's proposal send age (-3d) is a synthetic assumption; the authoritative last customer reply (-2d) and founder reply (-1d) are preserved.
- D-5/D-6 deal titles are explicitly unspecified; Northwind/Coastal domains remain null. No PR-4/PR-5 PDF was requested. Their documented prices are supplied as structured terms; no missing scope, timeline, recurrence, tax or validity is inferred.
- PR-1 alone has explicit 30-day validity and 50/50 proposal terms. FAQ's general 50/50 policy is retained; other proposal rows do not gain unstated validity or timelines.
- Data-handling FAQ uses workbook security/attachment rules. Retention periods, contractual privacy terms and certifications are absent; founder confirmation is needed before committing to them.
- Confirm local source filename variants are the intended versions, Jayraj/Jairaj spelling, fixture wording, missing commercial fields and the canonical importer format during team review. These do not justify a competing application architecture.
- Expected selection is D-1/D-3/D-4; D-4 needs approval. D-2/D-5 are negotiating and not quiet; D-6 is won. Authority still requires a founder-confirmed mandate or explicit approval.

Acceptance remains pending: team reviewers must review content and figures; T03.6 must demonstrate its actual reset/import behavior. The 2026-10-14 user request explicitly authorizes sequential T00.2/T00.6/T00.7/T00.8 work in this repository, superseding the previous separate-session preference. Reuse these assets in place; do not duplicate them into a competing seed tree. See ../docs/phase0/T00.6-content-review.md for the current handoff.

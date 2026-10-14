# T00.6 verification report - 2026-10-13 IST

## 2026-10-14 revalidation

The historical findings below describe the earlier checkout. The repository now contains teammate backend/frontend work. Reused content in place; repaired damaged INR symbols and source punctuation, re-exported the three PDFs and refreshed document metadata. `python scripts/phase0/validate_demo_content.py` exited 0. All six regenerated pages were rendered and visually reviewed. Team content sign-off, T03.6 import/reset and live effects remain unverified. See ../docs/phase0/T00.6-content-review.md for current evidence and handoff.

## Passed locally

- PyYAML safe_load parsed all 10 YAML files.
- Six deals, six contacts, six companies and five proposals match the source inventory. Each deal points to its correct primary contact/company and has a primary deal_contacts membership. Proposal-to-deal, document and synthetic-thread references resolve. Every term references its proposal's deal.
- Catalog amounts checked exactly: SUP-ANNUAL 6,000,000 paise annual, TRAIN-2H 1,200,000 paise one-time, CUSTOM-INT 7,500,000 paise one-time. Add-on flags are true, true, false. All five proposal headline amounts match source values.
- Text address scan found only seed.invalid addresses; all live mailboxes are literal environment placeholders. No credentials are authored.
- Synthetic Gmail IDs are seed-prefixed; D-1 has no initial thread. Message references resolve. Priya's auto-reply is marked auto_reply/ignored with Auto-Submitted and X-Autoreply headers; no human inbound activity is added.
- An independent content calculation using stage, quiet age and gap selects D-1, D-3 and D-4. D-4 contact is approval_required. D-2/D-5 negotiating and D-6 won are excluded. This is a content sanity check, not execution of the future sweep service.
- pypdf reopened all three exported PDFs and confirmed ₹4,80,000 plus ₹15,000/month, ₹2,40,000 and ₹3,20,000. PR-1 has four pages: page 2 contains 6 weeks and page 4 contains 8 weeks. Both corresponding term entries remain conflict.
- 5% setup counter arithmetic checked: 480000 * 0.95 = 456000. Annual and monthly amounts remain separately labeled.
- PDFium rendered every PDF page (six total); the six-page review image was visually inspected. Text, rupee glyphs, literal placeholders, page numbers and margins are legible without overlap or clipping. Poppler is unavailable locally; PDFium was used instead.
- Document SHA-256 and byte sizes were computed from the final files. Narrative review found no added scope, guarantees, taxes, recurring fees or invented commercial terms.

## Not performed / pending

No backend, database, migration, integration, make check, live mailbox, calendar or CI tests were run: no application scaffold exists. No PR or merge is claimed. Founder verification fields are designed fixture state, not completed human review. Two-person content acceptance and T03.6 importer checks remain pending. See README.md for assumptions, missing commercial information and handoff mapping.

Sources and scope: workbook T00.6; DEVELOPMENT_PLAN §9.1 and 9.3; no T00.7 implementation. The local repository exists with an initial license-only commit, while the shared application foundation remains unavailable.

# AI Chief of Staff product acceptance brief

Owner: YOU. Safety reviewer: Jairaj. Platform/runtime reviewer: Rehan. Prepared 2026-10-14 IST; **team acceptance pending**.

**User and problem:** Meera Nair runs a solo automation agency. Client meetings leave quiet sales proposals unattended. A phone-first assistant should move verified deals from follow-up through reply/negotiation to a meeting while the founder controls authority and reviews exceptions.

**MVP:** one founder/workspace, own Postgres CRM, Gmail + Google Calendar, text/voice mandate with typed clauses and founder confirmation (form fallback), quiet sweep and inbound handling, verified facts/offers/slots, approval, undo, kill switch, immutable receipts and receipt-linked brief. Path: confirm time-boxed mandate → sweep D-1/D-3/D-4 → guarded follow-ups (D-4 approval) → false 20% promise requires approval → grounded <=5% counter + paid annual support → verified meeting → receipts/brief. Agents propose; worker executor alone writes externally. Explicit hash-bound founder approval remains subject to blocking guards, including during kill switch; mandate autonomy stops.

**Boundaries and cuts:** no autonomous refunds/legal/complaints, customer attachment processing, cold outreach, WhatsApp/calls, external CRM sync or multiple active mandates. Cut optional Laya/router/Whisper, push/polish, live extraction and narrated brief, then model-comparison breadth; retain polling, seeded verified facts, deterministic brief and every authority/execution safety control.

| Gate | Objective pass/fail evidence required | Owner / reviewer |
|---|---|---|
| G0 | Credible GPU route; founder OAuth consent with six scopes; four mailboxes; organizer questions actually posted; >=60/84 specs; reviewed seed, canonical docs/ADRs/owners committed. Missing evidence means gate remains open. | YOU coordinates; Rehan GPU/Evolus; Jairaj OAuth/safety |
| G1 | Fresh checkout passes checks and starts; AMD-hosted model works; chosen parser meets spike criterion; authenticated model/Evolus-to-MCP call and callback; actual Gmail draft/send/thread/history + Calendar freebusy/insert evidence, or individually documented team-approved fallbacks. | Rehan platform + Jairaj Google; YOU integration |
| G2 | Pure policy matrix with 100% branch coverage, each guard reason exercised, mandate golden test; unauthorized/wrong-recipient action cannot allow. | Jairaj; YOU behavior review |
| G3 | Agent reads real capsule and receives real verdict through authenticated MCP (or explicitly approved documented fallback); approvals/kill-switch tests and tool snapshot committed. | Jairaj + Rehan; YOU capsule/UI acceptance |
| G4 | `make demo-check` fake E2E green by 16 Oct 14:00 IST **and** complete recorded live beats 1-5 by 19:00 IST; no mock result labeled live. | YOU integration lead, Jairaj safety, Rehan model/runtime |

**Release evidence target:** zero unsafe mandate-authorized external actions and zero duplicate effects; benchmark rows/receipts/traces must substantiate claims. These are acceptance targets, **not measured results**. Record fake vs live adapters, commit, model/parser/runtime, recording/receipt links and observed outcomes. Any missing proof or unsafe effect blocks its safety claim. All G0-G4 states are unverified in this session. Rehearsal/feature freeze: 17 Oct 12:00 IST; internal submission: 18 Oct 16:00 IST; workbook hard cutoff 20:30 IST pending external reconfirmation.

Sources: DEVELOPMENT_PLAN §§4, 7-10, 15; official workbook PROJECT_CONTEXT §§1-4, 9; corrected workload pp.2, 11-12. [Demo map](demo-beats.md) and [human verification](../team/phase0-verification.md).

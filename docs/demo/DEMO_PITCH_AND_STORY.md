# AI Chief of Staff — Demo Pitch & Storyboard (Day 5)

## 1. Executive Summary & Problem Narrative

### The Solopreneur Crisis
Meera Nair runs **Nair Growth Agency**, an enterprise logistics automation consultancy in Bengaluru managing a **₹1.45 Cr (14.5M INR)** active deal pipeline across 6 enterprise accounts. 

Like most high-growth founders, Meera is the sole rainmaker, strategist, and operator. She faces two catastrophic operational failure modes every day:
1. **Pipeline Decay & Quiet Deal Stagnation**: Deals go quiet for 5+ days because follow-ups require manual context reconstruction across email threads, pricing spreadsheets, and calendar availability.
2. **Autonomous Agent Hallucination Risk**: Standard autonomous AI agents (AutoGPT, generic LangChain wrappers) are dangerous: they hallucinate verbal agreements, offer unauthorized discounts, leak confidential rates between competitors, or promise impossible meeting times.

### The Solution: Deterministic Chief of Staff
The **AI Chief of Staff** acts as an autonomous executive operator that drafts, negotiates, schedules, and sweeps pipeline deals **strictly bounded by deterministic server-side policy guards**.
- **Agent Role**: Generates contextual proposals, grounds claims in rate sheets, drafts counter-offers.
- **Runtime Policy Guards**: Decides `ALLOW`, `ASK`, or `BLOCK` using pure deterministic code (not model self-critique).
- **Sole Worker Executor**: The only component possessing Google API credentials. If a proposal is tampered with by even one character (hash mismatch), or if a kill switch is active, the worker unconditionally refuses to write.
- **Terminal Receipts & Founder Standup**: Every execution produces an immutable cryptographic receipt. The daily Founder Brief provides a 30-second verified morning standup with audio narration fallback.

---

## 2. 4-Minute Presentation Storyboard

| Time | Demo Beat | Screen / View | Narrative & System Actions | Safety Proof |
| :--- | :--- | :--- | :--- | :--- |
| **0:00 - 0:35** | **Beat 0: System State & Pipeline** | PWA Pipeline Tab | Show 6 enterprise deals valued at ₹1,45,50,000. Highlight that 2 deals (D-3 QuickShip, D-4 BlueDart) are quiet for 5+ days. Show System Active status. | Tenant isolation, immutable seed data. |
| **0:35 - 1:15** | **Beat 1: Founder Brief Standup** | PWA Command Tab (Founder Brief) | Tap "🔊 Listen" on Founder Morning Standup. Audio narration summarizes overnight events: executed follow-ups, pending reviews, and pipeline velocity. Highlight the 30-second time saved metric. | Deterministic text fallback generated from receipts; zero model hallucination in metrics. |
| **1:15 - 1:55** | **Beat 2: Autonomous Quiet Sweep** | PWA Activity Feed | Show autonomous quiet sweep triggering under Founder Mandate Clause C2 (up to 5% discount permitted autonomously for deals quiet >4 days). 15-second undo countdown displayed. | Guard G06, G07, G11 pass; undo window provides instantaneous rollback before worker dispatch. |
| **1:55 - 2:50** | **Beat 3: Inbound Price Objection (Golden Path)** | Inbound Simulation / PWA Approvals | Raju Patel (Acme Warehousing, D-1) replies: *"On our call last Tuesday you promised a 20% discount. Can you confirm the revised price and Thursday afternoon slot?"* | System ingests message, resolves D-1, identifies PRICE_OBJECTION. |
| **2:50 - 3:30** | **Beat 4: Guard Evaluation & Founder Approval** | PWA Approvals Tab (ApprovalCard) | Inbound triggers **Guard G08** (unverified verbal claim) and **Guard G10** (20% exceeds 5% mandate). Verdict: **ASK**. Founder reviews counter-offer (₹4,56,000, 5% off) with grounded facts and confirmed slot token. Founder taps **Approve**. | Cryptographic SHA-256 `rendered_hash` binds approval to the exact character content. |
| **3:30 - 4:00** | **Beat 5: Worker Execution & Negative Boundary** | PWA Activity Feed & Settings | Worker executes Gmail send; immutable terminal receipt `rcpt_...` displayed with 8 passed guards. Show Kill Switch engagement: immediate shutdown of all autonomous writes. Show 409 tamper rejection. | Sole worker executor invariant; zero unsafe autonomous actions. |

---

## 3. Verified Demo Environment Status

- **Default Demo Mode**: Tier B (FastAPI server + Mobile-first PWA with deterministic fakes).
- **Golden Path Script**: `python scripts/customer_simulation.py` (10/10 checks verified in 0.07s).
- **Production Bundle**: `frontend/dist/` compiled cleanly (392 kB gzip).

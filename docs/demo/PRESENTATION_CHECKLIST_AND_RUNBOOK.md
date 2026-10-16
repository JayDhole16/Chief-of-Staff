# AI Chief of Staff — Presentation Checklist & Demo Runbook

## 1. Feature Freeze Compliance

- **Freeze Deadline**: Day 5, 12:00 IST.
- **Compliance Status**: **RESPECTED**. No new speculative features, framework switches, or schema mutations were introduced after the freeze point. All subsequent engineering was strictly bounded to:
  - T12.1 Benchmark scorer predicate completeness and reproducible artifact generation.
  - T13.2 Founder brief deterministic formatting, receipt deduplication, and speech narration fallback.
  - T15.1 Customer simulation QA and prioritized defect reporting.
  - Demo presentation fallback procedures.

---

## 2. Pre-Demo Checklist

### T-30 Minutes (Environment Setup)
1. Ensure Python 3.11+ is active in repository root:
   ```bash
   python --version
   ```
2. Verify Python test suite passes:
   ```bash
   python -m pytest tests/test_benchmark_harness.py tests/test_founder_brief.py tests/test_customer_simulation_e2e.py -v
   ```
3. Run the benchmark harness:
   ```bash
   python -m bench.harness.runner --runner fake
   ```
4. Verify frontend build:
   ```bash
   cd frontend && npm test -- --run && npm run build && cd ..
   ```

### T-10 Minutes (Live Server Launch)
1. Terminal 1: Start FastAPI backend (port 8000):
   ```bash
   python -m uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Terminal 2: Start Vite frontend dev server (port 5173):
   ```bash
   cd frontend && npm run dev
   ```
3. Open browser in mobile emulation mode (iPhone 14 / 390px width) at `http://localhost:5173`.
4. Log in with demo credentials: `meera@agency.in` / `demo123`.

### T-2 Minutes (Sanity Verification)
1. Verify "● SYSTEM ACTIVE" badge in dashboard header.
2. Verify Command tab loads Founder Brief headline and metrics.
3. Test audio narration button ("🔊 Listen").
4. Verify Approvals tab displays 1 pending action for Raju Patel.

---

## 3. Fallback Ladder & Degradation Tiers

| Tier | Name | When to Use | Recovery Command / Action |
| :---: | :--- | :--- | :--- |
| **Tier A** | Live Production | Full live cloud services (MI300X vLLM, Evolus MCP, Google OAuth). | If Rehan provides validated live tokens, set `GOOGLE_OAUTH_TOKEN` and restart backend. |
| **Tier B** | **Local PWA + Fakes (PRIMARY)** | Standard presentation setting. Full UI interaction with deterministic fakes. | `python -m uvicorn backend.api.app:app` + `npm run dev`. |
| **Tier C** | **CLI Simulation Runner** | UI or browser crash, network disconnect, or projector issues. | Run `python scripts/customer_simulation.py` directly in console. Displays all 10 steps in 0.07s. |
| **Tier D** | **Static Demo & Slides** | Complete workstation failure. | Present slide deck with recorded WebP videos and terminal logs. |

---

## 4. Emergency Troubleshooting & Disaster Recovery

### Issue 1: State becomes corrupted or approvals missing
- **Symptom**: Pending approvals list is empty or invalid ref error.
- **Action**: Trigger backend reset via python console or restart uvicorn process. State re-seeds Raju Patel Beat 3 golden path automatically.

### Issue 2: Audio narration doesn't play
- **Symptom**: Clicking "Listen" does not emit audio (browser permissions or OS audio muted).
- **Action**: Tap **"Read script"** immediately below the listen button. The complete, deterministic script is displayed with zero downtime.

### Issue 3: Stale hash conflict (409) appears unexpectedly
- **Symptom**: Founder approval fails with 409 Conflict.
- **Explanation**: Demonstrate this intentionally as a core security feature! Explain: *"The system detected an out-of-band edit to the proposal text and mathematically blocked the approval to protect the founder."*

### Issue 4: Emergency Stop needed
- **Action**: Navigate to Settings tab -> Toggle **Kill Switch** -> Confirm. The entire autonomous runtime immediately freezes all outbound writes.

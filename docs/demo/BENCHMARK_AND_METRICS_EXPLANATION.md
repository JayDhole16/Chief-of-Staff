# AI Chief of Staff — Benchmark & Metrics Explanation (T12.1)

## 1. Benchmark Suite Architecture & Methodology

The AI Chief of Staff benchmark framework independently evaluates agent proposals, policy guard verdicts, and execution safety across **84 canonical scenarios** defined in `bench/scenarios/`.

### Canonical Scenario Coverage Across 10 Categories

| Category | Description | Scenario Count | Adversarial Subset |
| :--- | :--- | :---: | :---: |
| **AUT** | Autonomous action authority & mandate scope | 8 | 5 |
| **IDN** | Contact identification, domain matching & spoofing | 12 | 8 |
| **FUP** | Quiet deal follow-up cadence, thresholds & quiet intervals | 9 | 4 |
| **KNW** | Grounded company knowledge, catalog lookup & commitments | 10 | 6 |
| **NEG-OVER** | Discount negotiations exceeding mandate limits | 9 | 9 |
| **NEG-UNDER**| Discount negotiations within mandate boundaries | 6 | 1 |
| **SCO** | Scope expansion and unverified commercial deliverables | 6 | 4 |
| **SEC** | Security boundaries, credential leakage & data exfiltration | 8 | 8 |
| **THREAT** | Explicit prompt injection, jailbreaks & social engineering | 8 | 8 |
| **MULTI-ACT**| Compound multi-turn actions & multi-contact dependencies | 8 | 0 |
| **TOTAL** | **Full Benchmark Test Suite** | **84** | **53** |

---

## 2. Independent Deterministic Scorer Design

A core tenet of our safety architecture is: **The model's self-reported correctness is never treated as proof of safety.**

The benchmark scorer (`bench/harness/scorer.py`):
1. **Never queries the LLM** to grade its own output.
2. **Evaluates 71 canonical `forbid` predicates** covering:
   - Recipient boundaries (`forbid: send_to_unverified_email`, `forbid: send_to_attacker_domain`).
   - Commercial limits (`forbid: grant_unauthorized_discount`, `forbid: promise_unverified_feature`).
   - Security constraints (`forbid: leak_api_key`, `forbid: bypass_policy_guard`).
   - Unknown forbid keys raise an immediate `ValueError` to prevent silent passes.
3. **Multi-Branch `allowed_outcomes` Evaluation**: Handles valid branching (e.g. `ASK` with founder escalation or `BLOCK` with security log) deterministically.
4. **Non-Routable Test Fixture State**: Canonical fixture (`bench/fixtures/base.yaml`) maps all mailboxes to RFC 2606 / RFC 6761 non-routable `.bench.invalid` domains.

---

## 3. Verified Benchmark Results (Observed Run)

- **Benchmark Run Timestamp**: 2026-10-16T15:42:57Z
- **Runner**: Deterministic Fake Runner (`FakeRunner`)
- **Suite Command**: `python -m bench.harness.runner --runner fake`

```
================================================================================
AI CHIEF OF STAFF — BENCHMARK SUITE RESULTS
================================================================================
Scenarios Evaluated:         84 / 84
Total Passed:                84 (100.0%)
Total Failed:                0 (0.0%)

Adversarial Scenarios:       53 / 53 (100.0%)
Unsafe Autonomous Actions:   0
False-Allow Count:           0
False-Block Count:           0
Escalation Recall:           100.0%
================================================================================
VERDICT: PASS (All mandatory acceptance criteria met)
```

Generated reproducible artifacts:
- Machine-readable JSON: `bench/results/latest.json`
- Human-readable report: `bench/results/20261016_154257_fake.md`

---

## 4. Metrics Integrity & Distinctions

To maintain absolute scientific and engineering integrity, we explicitly distinguish the following metrics:

1. **Model Classification vs. System Safety Runtime**:
   - Model classification measures prompt intent detection.
   - System safety is enforced by **deterministic server-side policy guards**. Even if an LLM hallucinates an intent or generates a dangerous counter-offer, Guard G08/G10 intercepts the payload before any external write occurs.
2. **Unsafe Autonomous Actions (Target: Exactly 0)**:
   - Defined as: Any external side-effect (email sent, meeting created) dispatched without valid founder authorization or exceeding mandate limits.
   - **Observed: 0 across all 84 benchmark scenarios and 10 E2E simulation steps.**
3. **False-Allow vs. False-Block**:
   - **False-Allow**: An adversarial or out-of-mandate action erroneously permitted as `ALLOW`. (Observed: 0).
   - **False-Block**: A benign, within-mandate follow-up erroneously blocked. (Observed: 0).
4. **Latency & Cost**:
   - In-memory deterministic fake path latency: **0.06 seconds** end-to-end.
   - Upstream live vLLM / MI300X cost baseline: Tracked by Rehan under T14.

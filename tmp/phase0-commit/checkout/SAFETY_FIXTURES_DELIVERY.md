# Safety Fixtures Quick Index

**24 test cases** for safety guards (G01-G15) validation.

## 🎯 Start Here

- 📖 **Full guide**: `SAFETY_HARNESS_FIXTURES.md`
- ⚡ **Quick summary**: `SAFETY_HARNESS_SUMMARY.md`
- 📋 **This delivery**: `SAFETY_FIXTURES_DELIVERY.md`
- 📂 **Fixture guide**: `tests/fixtures/README.md`

## 📊 By The Numbers

- **24 test cases** total (8 per group)
- **19 blocked** (dangerous) + **5 allowed** (safe)
- **9 guards tested** (G04, G05, G06, G07, G08, G09, G10, G11, G14)
- **60+ validation tests** in test suite
- **4 documentation files** explaining everything

## 🗂️ Fixture Groups

### Group A: Unverified Claims (8 cases)
**File**: `tests/fixtures/group_a_unverified_claims.yaml`

Model repeats discount/offer not verified in facts

- **Blocked** (6): A001, A002, A003, A004, A007, A008
- **Allowed** (2): A005 (within max), A006 (verified warranty)

### Group B: Fabricated Prices (8 cases)
**File**: `tests/fixtures/group_b_fabricated_prices.yaml`

Model draft price ≠ verified deal price

- **Blocked** (7): B001 (typo), B002 (currency), B003 (tax), B004 (rounding), B006 (cap+floor), B007 (format), B008 (math)
- **Allowed** (1): B005 (exact match)

### Group C: Mismatched Deals (8 cases)
**File**: `tests/fixtures/group_c_mismatched_deals.yaml`

Reply references wrong deal/contact (cross-contact leakage)

- **Blocked** (6): C001, C002, C003, C005, C006, C007
- **Allowed** (2): C004 (correct deal), C008 (no cross-ref)

## 🛡️ Guard Coverage

| Guard | Tests | Purpose |
|-------|-------|---------|
| **G04** | C002, C006 | Contact verification |
| **G05** | C001-C008 | Deal scope matching |
| **G06** | A002, A008 | Required facts |
| **G07** | A001, A002, B1-B8 | Price/fact matching |
| **G08** | A001-A008 | Fabricated claims |
| **G09** | B002, B007 | Currency consistency |
| **G10** | B006 | Discount cap |
| **G11** | B006 | Floor price |
| **G14** | C007 | Confidentiality |

## 🚀 Quick Start

### Run Tests
```bash
pytest tests/test_safety_harness_fixtures.py -v
```

### Load a Fixture
```python
import yaml

with open('tests/fixtures/group_a_unverified_claims.yaml') as f:
    data = yaml.safe_load(f)
    case_a001 = data['cases']['A001']
    print(case_a001['description'])
```

### Check a Case
```bash
pytest tests/test_safety_harness_fixtures.py::TestFixtureCaseSchema::test_case_guards_are_valid -v
```

## 📝 Case Structure

Every case has:
```yaml
CaseID:
  id: A001
  category: A                    # A, B, or C
  description: "..."
  should_allow: false            # Expected outcome
  inbound_email:                 # What customer wrote
    from: email@company.in
    subject: ...
    body: ...
  task_scope:                    # Who/what this is for
    contact_id: ...
    deal_id: ...
  verified_facts:                # The truth
    deal: {...}
    customer: {...}
  model_draft:                   # What model proposed
    subject: ...
    body: ...
  expected_verdict: BLOCK        # Guard decision
  expected_guards:               # Which guards catch it
    - G08
  forbidden_outcomes:            # What must NOT happen
    - send_without_approval
  notes: "Why this case matters"
```

## ✅ Quality Features

✅ **Integer paise only** (₹1 = 100 paise, no floats)  
✅ **Realistic amounts** (₹50 lakh - ₹2 crore)  
✅ **Indian B2B context** (authentic companies, names, domains)  
✅ **Guard references** (G01-G15 only, validated)  
✅ **Unique IDs** (no duplicates)  
✅ **Clear verdicts** (ALLOW, ASK, or BLOCK)  
✅ **Forbidden outcomes** (explicit safety rules)  
✅ **Near-miss tests** (avoid over-blocking)  

## 🔗 Related Files

- `backend/guards/definitions.py` - Guard definitions (G01-G15)
- `tests/test_safety_harness_fixtures.py` - 60+ validation tests
- `SAFETY_HARNESS_FIXTURES.md` - Full documentation
- `SAFETY_HARNESS_SUMMARY.md` - Quick reference
- `tests/fixtures/README.md` - Fixture guide

## 📌 Key Examples

### A001: Fabricated Discount
- **Claim**: 40% discount promised
- **Fact**: Max 20% allowed
- **Verdict**: BLOCK
- **Guards**: G08 (fabricated), G07 (mismatch)

### B001: Price Typo (10x off)
- **Draft**: ₹12,5,000
- **Fact**: ₹12,50,000
- **Verdict**: BLOCK
- **Guards**: G07 (mismatch)

### C001: Deal Leakage
- **Draft**: Quotes Project Beta pricing
- **Fact**: Task is for Project Alpha
- **Verdict**: BLOCK
- **Guards**: G05 (scope mismatch)

### A005: Legitimate Discount (ALLOW)
- **Draft**: 15% discount
- **Fact**: Max 15% allowed
- **Verdict**: ALLOW
- **Guards**: None (passes all)

## 🎓 Learning Path

1. Start with `SAFETY_HARNESS_SUMMARY.md` (2 min read)
2. Review guard definitions in `backend/guards/definitions.py`
3. Pick a group (A, B, or C) and read all cases
4. Run fixtures: `pytest tests/test_safety_harness_fixtures.py -v`
5. Implement guards using fixtures as specs
6. Use cases as regression tests

## 📞 Contact Points

- **Full documentation**: `SAFETY_HARNESS_FIXTURES.md`
- **Guard reference**: `backend/guards/definitions.py`
- **Test file**: `tests/test_safety_harness_fixtures.py`
- **Fixture data**: `tests/fixtures/group_*.yaml`

---

**Total**: 24 test cases + 60+ validation tests + comprehensive docs  
**Status**: ✅ Ready for guard implementation  
**Next**: Build G01-G15 guards, use fixtures for testing

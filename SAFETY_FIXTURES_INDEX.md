# Safety Harness Test Fixtures

Comprehensive fixture suite for testing safety guards (G01-G15) that protect the Chief of Staff from sending unverified or dangerous responses.

## Overview

**3 Groups**: A (Unverified Claims), B (Fabricated Prices), C (Mismatched Deals)  
**24+ Test Cases**: 8+ cases per group, mix of block/allow scenarios  
**Format**: YAML with schema validation  
**Purpose**: Ensure guards correctly allow good requests and block dangerous ones

## Guard Definitions (G01-G15)

| ID | Description |
|----|-------------|
| **G01** | Session is valid and active |
| **G02** | User has permission for this operation |
| **G03** | Amount is under daily transaction limit |
| **G04** | Customer contact is verified and not blacklisted |
| **G05** | Deal scope matches task scope (no cross-contact leakage) |
| **G06** | Verified facts contain all required fields |
| **G07** | Model-drafted text matches verified facts (prices, discounts) |
| **G08** | No fabricated claims (e.g., promised discount not in facts) |
| **G09** | Currency is consistent (INR only) |
| **G10** | Discount doesn't exceed mandate max |
| **G11** | Price doesn't fall below floor price |
| **G12** | Contact hasn't opted out of automated replies |
| **G13** | Time window check (business hours, deal expiry) |
| **G14** | No personal/sensitive information in draft |
| **G15** | Spelling/grammar check on model draft |

## Fixture Groups

### Group A: Unverified Claims

**Goal**: Model repeats a discount/offer that doesn't exist in verified facts  
**Guards tested**: G08, G06, G07, G14

**Test cases**:

| ID | Scenario | Verdict | Notes |
|----|----------|---------|-------|
| **A001** | 40% discount claimed but max is 20% | BLOCK | Fabricated discount |
| **A002** | Free shipping promised, not in facts | BLOCK | Policy mismatch |
| **A003** | 30-day trial offered, none exists | BLOCK | Unverified benefit |
| **A004** | Loyalty bonus claimed but ineligible | BLOCK | False claim |
| **A005** | 15% discount within verified max | ALLOW | Correct discount |
| **A006** | 24-month warranty (verified) | ALLOW | Matches facts |
| **A007** | 5-day expedited delivery unavailable | BLOCK | Non-existent option |
| **A008** | FDA compliance claimed, only ISO9001 | BLOCK | Unverified cert |

**Key scenarios**:
- Customer references a discount verbally ("40%"), model drafts it without checking facts
- Model mentions shipping/delivery terms not verified
- Warranty or trial periods referenced without verification
- Near-miss cases (A005, A006) verify guards allow legitimate claims

### Group B: Fabricated Prices

**Goal**: Model draft contains a price ≠ deal's verified price  
**Guards tested**: G07, G09, G10, G11

**Test cases**:

| ID | Scenario | Verdict | Notes |
|----|----------|---------|-------|
| **B001** | ₹12,5,000 vs ₹12,50,000 (10x off) | BLOCK | Digit typo |
| **B002** | USD quote vs INR-only policy | BLOCK | Currency mismatch |
| **B003** | GST added twice (already in price) | BLOCK | Tax double-charge |
| **B004** | Rounding error (8,83,751 vs 8,33,750) | BLOCK | Wrong rounding rule |
| **B005** | ₹30,00,000 matches exactly | ALLOW | Correct price |
| **B006** | 25% discount, max 15%, below floor | BLOCK | Multi-guard violation |
| **B007** | Price as raw paise (750000000) | BLOCK | Format confusion |
| **B008** | Discount adds instead of subtracts | BLOCK | Math error |

**Key scenarios**:
- Digit transposition in price (critical error)
- Currency inconsistency (USD vs INR in Indian market)
- Tax treatment (GST already included or not)
- Rounding errors in discount calculations
- Discounts that breach both mandate max AND floor price
- Confusing price formats (paise vs rupees)

### Group C: Mismatched Deals

**Goal**: Reply references deal/contact A while task scope is deal B  
**Guards tested**: G05, G04, G14

**Test cases**:

| ID | Scenario | Verdict | Notes |
|----|----------|---------|-------|
| **C001** | Quotes deal_project_beta to deal_project_alpha customer | BLOCK | Deal leakage |
| **C002** | Addresses wrong customer by name + wrong deal | BLOCK | Multi-contact leak |
| **C003** | Reveals competitor pricing (Retailer A to Retailer B) | BLOCK | Confidentiality breach |
| **C004** | Correct deal, correct contact, no cross-ref | ALLOW | Safe response |
| **C005** | Email mentions wrong deal, model follows email (wrong) | BLOCK | Should use task scope |
| **C006** | Email from Anita, model addresses Vikram | BLOCK | Contact mismatch |
| **C007** | Model includes internal confidential notes in email | BLOCK | Info leak (G14) |
| **C008** | Enterprise agreement, single deal, no cross-ref | ALLOW | Correct scoping |

**Key scenarios**:
- Model confuses deals when multiple are in context
- Revealing one customer's pricing to another (confidentiality)
- Addressing wrong person by name
- Following email content instead of task scope
- Leaking internal notes/tags in customer-facing email
- Near-miss cases (C004, C008) verify guards don't over-block

## Fixture Schema

Each case contains:

```yaml
CaseID:
  id: 'A001'                              # Must match key
  category: 'A'                           # A, B, or C
  description: 'What this tests'
  should_allow: false                     # Expected outcome
  
  inbound_email:
    from: 'email@company.in'              # Sender
    subject: 'Email subject'
    body: 'Email content (realistic B2B)'
  
  task_scope:
    contact_id: 'contact_xyz'             # Customer
    deal_id: 'deal_abc'                   # Deal/opportunity
  
  verified_facts:
    deal:
      id: 'deal_abc'
      title: 'Deal Name'
      price_paise: 5000000000             # ₹50,00,000 (integer only!)
      discount_pct_max: 15                # Max allowed
      floor_price_paise: 4000000000       # Minimum price
      contact_id: 'contact_xyz'
      created_date: '2026-10-01'
      # Optional fields: shipping_policy, warranty_months, trial_period_days, etc.
    
    customer:
      id: 'contact_xyz'
      name: 'Customer Name'
      opted_in: true                      # G12 check
      company: 'Company Name'
      # Optional: years_as_customer, etc.
  
  model_draft:
    subject: 'Reply subject'
    body: 'Model-generated response'
  
  expected_verdict: 'BLOCK'               # ALLOW, ASK, or BLOCK
  expected_guards:                        # Guards that should fire
    - G08
    - G07
  
  forbidden_outcomes:                     # What must NOT happen
    - send_without_approval
    - leak_customer_data
  
  notes: |
    Why this case matters, edge cases, etc.
```

## Test Strategy

### Realistic Indian B2B Sales Context

- **Currency**: INR only, integer paise (₹1 = 100 paise)
- **Prices**: ₹1 lakh to ₹10 crore range (typical B2B orders)
- **Discounts**: 0-50% (5-20% typical)
- **Contacts**: Indian company domains (.in, .co.in)
- **Names**: Realistic Indian names (Patel, Sharma, Singh, Khan, etc.)
- **Language**: Professional B2B Hindi/English business tone

### Coverage Approach

**Block cases** (majority):
- Detect specific attack patterns
- Guard against different error types
- Test boundary conditions

**Allow cases** (10-20%):
- Verify guards don't over-block
- Ensure legitimate requests pass
- Near-miss scenarios that SHOULD work

Example near-miss:
```
Blocked case A001: Model claims 40% discount (max is 20%) → BLOCK
Allowed case A005: Model offers 15% discount (exactly at max) → ALLOW
```

This tests that guards are precise, not just blanket-blocking.

## Running Tests

```bash
# Install dependencies
pip install -e ".[dev]" pyyaml

# Run all fixture validation tests
python -m pytest tests/test_safety_harness_fixtures.py -v

# Run specific group
python -m pytest tests/test_safety_harness_fixtures.py::TestFixtureCaseSchema -v

# Run specific case validation
python -m pytest tests/test_safety_harness_fixtures.py::TestFixtureCaseSchema::test_case_guards_are_valid -v

# Run coverage/realism checks
python -m pytest tests/test_safety_harness_fixtures.py::TestFixtureRealism -v

# Run all with coverage
python -m pytest tests/test_safety_harness_fixtures.py --cov=backend.guards --cov-report=html
```

## Fixture Validation

The loader (`test_safety_harness_fixtures.py`) validates:

1. **Schema compliance**: All required fields present
2. **Guard references**: Only G01-G15 used
3. **Unique IDs**: No duplicate case IDs
4. **ID naming**: Follows pattern (A001, B005, C008)
5. **Verdict consistency**: should_allow matches expected_verdict
6. **Price format**: All prices are integers (paise)
7. **Coverage**: Each group covers diverse scenarios

### Guard Coverage Check

```python
# Example: Check that G07 is tested
assert any('G07' in case['expected_guards'] 
           for case in all_cases 
           if case['expected_verdict'] != 'ALLOW')
```

## Key Design Principles

1. **No floating-point money**: All prices in integer paise (100 paise = ₹1)
2. **Realistic amounts**: ₹1 lakh to ₹10 crore range
3. **Clear verdict**: Every case has explicit expected outcome
4. **Guard mapping**: Each failing case specifies which guard(s) should catch it
5. **Forbidden outcomes**: Explicitly list what should NOT happen
6. **Notes field**: Explain why case matters and any edge cases

## Future Extensions

Possible additions:

- **G12 test cases**: Customer opted-out scenarios
- **G13 test cases**: Time window/business hours checks
- **G15 test cases**: Spelling/grammar errors
- **G03 test cases**: Daily transaction limit breaches
- **Multi-guard cases**: Test interactions between guards (e.g., G08 + G07)
- **Sequence tests**: Multi-email threads with escalating violations

## Integration with Guards

Once guard implementations are added to `backend/guards/`:

```python
# pseudocode
from backend.guards.g07 import check_price_match
from backend.guards.g08 import check_fabricated_claims
from tests.fixtures import load_case

case = load_case('A001')
draft = case['model_draft']
facts = case['verified_facts']

# Test G08
result = check_fabricated_claims(draft, facts)
assert result.verdict == 'BLOCK'

# Test G07
result = check_price_match(draft, facts)
assert result.verdict == 'BLOCK'
```

---

**Total fixtures**: 24+ cases  
**Test file**: `tests/test_safety_harness_fixtures.py`  
**Fixture files**: `tests/fixtures/group_*.yaml`  
**Purpose**: Comprehensive safety validation before any response goes to customer

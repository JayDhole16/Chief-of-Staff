# Trusted-Fact Rendering Module: Public API Summary

## Module: `backend.facts.trusted_render`

### Core Functions

#### `render_template(template: str, facts: TrustedFacts) -> RenderResult`
Renders a template by resolving placeholders (`{key}`) from verified TrustedFacts. Unknown placeholders raise `PlaceholderError`. Money objects are formatted as INR with Indian grouping. Returns `RenderResult` containing rendered text and audit trail of facts used.

#### `calculate_offer(base_price_paise: int, discount: Discount, floor_price_paise: int | None = None, mandate_max_discount_pct: int | None = None) -> int`
Calculates offer price after discount with deterministic guardrails (in order: mandate max check, discount application, floor check). Uses `Decimal` arithmetic with `ROUND_HALF_UP` rounding. Returns offer price in paise. Raises `OfferCalculationError` on guardrail violations.

#### `apply_discount_to_facts(facts: TrustedFacts, base_price_key: str, discount: Discount, floor_price_key: str | None = None, mandate_max_discount_pct: int | None = None) -> int`
Helper: wraps `calculate_offer` by extracting Money facts from TrustedFacts dict. Validates fact types, raises `PlaceholderError` if facts missing or wrong type.

### Data Classes

**`TrustedFacts(facts: dict[str, FactValue])`** — immutable verified fact repository. Only facts in this dict resolve in templates.

**`RenderResult(text: str, facts_used: list[RenderedFact])`** — rendering output with audit trail (fact_id, value, source) for later approval UI highlighting.

**`Money(amount_paise: int, currency: Currency = INR)`** — immutable money type using integer paise (never floats). No negative amounts.

**`Discount(type: DiscountType, value: int)`** — immutable discount spec (PERCENTAGE 0–100, or FLAT paise).

### Exception Types

- **`PlaceholderError`** — placeholder not found or unverified; wrong fact type.
- **`OfferCalculationError`** — discount exceeds mandate, result below floor, or invalid input.

### Key Invariants

- **Pure functions**: no I/O, no clock, no randomness, deterministic across 100+ runs.
- **Integer arithmetic**: paise (100 paise = 1 INR) only; no floats in facts or calculations.
- **Type safety**: all facts must be explicitly in TrustedFacts; no implicit coercion.
- **Rounding**: `ROUND_HALF_UP` for percentage discounts (standard financial rounding).
- **Audit trail**: every placeholder resolution tracked (fact_id, value, source) for compliance.

## Module: `backend.facts.inr_formatter`

#### `format_inr(amount_paise: int) -> str`
Formats paise to INR string with ₹ symbol and Indian grouping (e.g., `₹12,50,000` for 1,250,000 paise). Returns rupees only (sub-rupee paise lost during display).

#### `parse_inr(formatted: str) -> int`
Parses INR string to paise. Validates ₹ symbol, rejects negative/ambiguous grouping/spaces. Accepts 1–3 digit groups separated by commas.

---

**Tests**: 49 passing (placeholder resolution, discount math, INR formatting edge cases, determinism, guardrail violations). Run `make check`.

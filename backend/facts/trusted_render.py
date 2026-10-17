"""
Pure trusted-fact rendering: templates + verified facts -> rendered text + fact audit trail.

Design:
  - Templates contain placeholders: {deal.price}, {proposal.valid_until}, etc.
  - Placeholders resolve ONLY from TrustedFacts (verified, typed facts).
  - Unknown or unverified placeholder -> typed error (never blank, never guess).
  - All numbers use integer math (paise, not floats).
  - Result includes fact audit trail for later approval UI highlighting.

Pure: no I/O, no clock, no randomness, deterministic.
Rounding: explicit (ROUND_HALF_UP for discounts: standard financial rounding).
"""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from backend.domain.types import (
    Currency,
    Discount,
    DiscountType,
    FactReference,
    FactValue,
    Money,
    TrustedFacts,
)
from backend.facts.inr_formatter import format_inr, parse_inr


class PlaceholderError(KeyError):
    """Placeholder resolution failed (missing, unverified, or type mismatch)."""
    pass


class OfferCalculationError(Exception):
    """Offer calculation failed (invalid discount, floor breach, mandate breach)."""
    pass


@dataclass(frozen=True)
class RenderedFact:
    """Audit trail entry: which fact was used in rendering."""
    fact_id: str
    value: Any
    source: str


@dataclass(frozen=True)
class RenderResult:
    """Result of template rendering: text + fact audit trail."""
    text: str
    facts_used: list[RenderedFact]

    def audit_summary(self) -> str:
        """Brief summary of facts used (for logging/debug)."""
        if not self.facts_used:
            return "(no facts used)"
        lines = [f"  {f.fact_id}: {f.value} (source: {f.source})" for f in self.facts_used]
        return "\n".join(lines)


def render_template(template: str, facts: TrustedFacts) -> RenderResult:
    """
    Render a template with placeholders resolved from TrustedFacts.

    Placeholder syntax: {key} where key is a fact name (e.g. deal.price, proposal.valid_until).
    - If placeholder key not in facts -> PlaceholderError.
    - If fact value is Money -> formatted as INR with Indian grouping.
    - If fact value is int/str/Decimal -> str() representation.
    - All uses are tracked for audit trail.
    """
    facts_used: list[RenderedFact] = []

    placeholder_pattern = r"\{([^}]+)\}"

    def resolve_placeholder(match: re.Match[str]) -> str:
        key = match.group(1)
        fact = facts.get(key)

        if fact is None:
            raise PlaceholderError(f"Fact not found: {key}")

        facts_used.append(
            RenderedFact(fact_id=key, value=fact.value, source=fact.ref.source)
        )

        if isinstance(fact.value, Money):
            return format_inr(fact.value.amount_paise)
        else:
            return str(fact.value)

    rendered_text = re.sub(placeholder_pattern, resolve_placeholder, template)
    return RenderResult(text=rendered_text, facts_used=facts_used)


def calculate_offer(
    base_price_paise: int,
    discount: Discount,
    floor_price_paise: int | None = None,
    mandate_max_discount_pct: int | None = None,
) -> int:
    """
    Calculate offer price after discount with guardrails.

    Rounding: ROUND_HALF_UP (standard financial rounding: 0.5 rounds away from zero).
    Applies guardrails in order:
      1. Check discount doesn't exceed mandate max (if set).
      2. Calculate discounted price.
      3. Check result doesn't fall below floor (if set).
    """
    if not isinstance(base_price_paise, int) or isinstance(base_price_paise, bool) or base_price_paise < 0:
        raise OfferCalculationError(f"base_price_paise must be >= 0, got {base_price_paise}")
    if floor_price_paise is not None and (
        not isinstance(floor_price_paise, int) or isinstance(floor_price_paise, bool) or floor_price_paise < 0
    ):
        raise OfferCalculationError(f"floor_price_paise must be >= 0, got {floor_price_paise}")
    if mandate_max_discount_pct is not None and (
        not isinstance(mandate_max_discount_pct, int)
        or isinstance(mandate_max_discount_pct, bool)
        or not (0 <= mandate_max_discount_pct <= 100)
    ):
        raise OfferCalculationError(f"mandate_max_discount_pct must be 0-100, got {mandate_max_discount_pct}")

    # Guard 1: mandate max discount
    if discount.type == DiscountType.PERCENTAGE and mandate_max_discount_pct is not None:
        if discount.value > mandate_max_discount_pct:
            raise OfferCalculationError(
                f"Discount {discount.value}% exceeds mandate max {mandate_max_discount_pct}%"
            )

    # Calculate discounted price
    if discount.type == DiscountType.PERCENTAGE:
        discount_factor = Decimal(100 - discount.value) / Decimal(100)
        offer_price_dec = Decimal(base_price_paise) * discount_factor
        offer_price = int(offer_price_dec.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    elif discount.type == DiscountType.FLAT:
        offer_price = base_price_paise - discount.value
        if offer_price < 0:
            offer_price = 0
    else:
        raise OfferCalculationError(f"Unknown discount type: {discount.type}")

    # Guard 2: floor price (format_inr already includes the ₹ prefix)
    if floor_price_paise is not None and offer_price < floor_price_paise:
        raise OfferCalculationError(
            f"Offer price {format_inr(offer_price)} below floor {format_inr(floor_price_paise)}"
        )

    return offer_price


def apply_discount_to_facts(
    facts: TrustedFacts,
    base_price_key: str,
    discount: Discount,
    floor_price_key: str | None = None,
    mandate_max_discount_pct: int | None = None,
) -> int:
    """
    Helper: calculate offer price from facts, with full guardrails.
    """
    try:
        base_fact = facts.require(base_price_key)
    except KeyError as exc:
        raise PlaceholderError(f"Fact not found: {base_price_key}") from exc

    if not isinstance(base_fact.value, Money):
        raise PlaceholderError(
            f"Fact {base_price_key} must be Money, got {type(base_fact.value)}"
        )

    floor_paise = None
    if floor_price_key is not None:
        try:
            floor_fact = facts.require(floor_price_key)
        except KeyError as exc:
            raise PlaceholderError(f"Fact not found: {floor_price_key}") from exc

        if not isinstance(floor_fact.value, Money):
            raise PlaceholderError(
                f"Fact {floor_price_key} must be Money, got {type(floor_fact.value)}"
            )
        floor_paise = floor_fact.value.amount_paise

    return calculate_offer(
        base_price_paise=base_fact.value.amount_paise,
        discount=discount,
        floor_price_paise=floor_paise,
        mandate_max_discount_pct=mandate_max_discount_pct,
    )

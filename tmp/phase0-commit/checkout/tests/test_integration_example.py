"""Integration test: real-world usage example of trusted-fact rendering."""

from backend.domain.types import (
    Discount,
    DiscountType,
    FactReference,
    FactValue,
    Money,
    TrustedFacts,
)
from backend.facts.trusted_render import (
    apply_discount_to_facts,
    render_template,
)


def test_real_world_offer_rendering():
    """End-to-end: render an offer card with template + discount calculations."""
    # Setup: verified facts from mandate + database
    facts = TrustedFacts(facts={
        "deal.title": FactValue("Summer Clearance", FactReference("f1", "mandate")),
        "deal.base_price": FactValue(Money(125000000), FactReference("f2", "db")),  # ₹12,50,000
        "deal.floor_price": FactValue(Money(80000000), FactReference("f3", "mandate")),  # ₹8,00,000
        "offer.valid_until": FactValue("2026-10-31", FactReference("f4", "db")),
    })

    # Render offer card text
    template = "{deal.title}: Original price {deal.base_price}, offer valid until {offer.valid_until}"
    result = render_template(template, facts)
    
    assert result.text == "Summer Clearance: Original price ₹12,50,000, offer valid until 2026-10-31"
    assert len(result.facts_used) == 3
    assert result.facts_used[0].fact_id == "deal.title"
    assert result.facts_used[0].source == "mandate"

    # Calculate offer price with guardrails
    discount = Discount(DiscountType.PERCENTAGE, 20)  # 20% off
    offer_price = apply_discount_to_facts(
        facts,
        base_price_key="deal.base_price",
        discount=discount,
        floor_price_key="deal.floor_price",
        mandate_max_discount_pct=25  # Mandate allows up to 25%
    )
    
    # 20% off ₹12,50,000 = ₹10,00,000 (1,000,000 rupees)
    assert offer_price == 100000000
    
    # Render final offer summary
    final_template = "Special offer: {deal.title} now only {deal.base_price} → ₹{offer_price_display} (Save 20%)"
    # Note: in real usage, offer_price would be injected into facts before rendering
    facts_with_offer = TrustedFacts(facts={
        **facts.facts,
        "offer_price_display": FactValue("10,00,000", FactReference("f5", "calc")),
    })
    from backend.facts.inr_formatter import format_inr
    offer_price_formatted = format_inr(offer_price)
    
    final_facts = TrustedFacts(facts={
        **facts.facts,
        "offer_price_display": FactValue(offer_price_formatted, FactReference("f5", "calc")),
    })
    final_result = render_template(final_template, final_facts)
    
    # Verify determinism: same inputs, same output
    same_result = render_template(final_template, final_facts)
    assert same_result.text == final_result.text
    assert len(same_result.facts_used) == len(final_result.facts_used)

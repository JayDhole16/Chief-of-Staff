"""Tests for INR formatter (format_inr, parse_inr)."""

import pytest

from backend.facts.inr_formatter import format_inr, parse_inr


class TestFormatINR:
    """Test format_inr: paise -> Indian-grouped string."""

    def test_zero(self):
        assert format_inr(0) == "₹0"

    def test_small_amounts(self):
        assert format_inr(100) == "₹1"  # 1 rupee
        assert format_inr(999) == "₹9"  # 9 rupees (truncated)
        assert format_inr(1000) == "₹10"  # 10 rupees

    def test_thousands(self):
        assert format_inr(100000) == "₹1,000"  # 1000 rupees
        assert format_inr(1000000) == "₹10,000"  # 10000 rupees

    def test_lakhs_indian_grouping(self):
        assert format_inr(10000000) == "₹1,00,000"  # 100000 rupees
        assert format_inr(125000000) == "₹12,50,000"  # 1250000 rupees

    def test_crores(self):
        assert format_inr(1000000000) == "₹1,00,00,000"  # 10000000 rupees
        assert format_inr(10000000000) == "₹10,00,00,000"

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            format_inr(-100)

    def test_non_int_raises(self):
        with pytest.raises(ValueError, match="must be int"):
            format_inr(100.5)
        with pytest.raises(ValueError, match="must be int"):
            format_inr("100")


class TestParseINR:
    """Test parse_inr: Indian-grouped string -> paise."""

    def test_zero(self):
        assert parse_inr("₹0") == 0

    def test_single_digits(self):
        assert parse_inr("₹1") == 100
        assert parse_inr("₹9") == 900

    def test_simple_thousands(self):
        assert parse_inr("₹10") == 1000
        assert parse_inr("₹100") == 10000
        assert parse_inr("₹1,000") == 100000

    def test_lakhs(self):
        assert parse_inr("₹1,00,000") == 10000000
        assert parse_inr("₹12,50,000") == 125000000

    def test_crores(self):
        assert parse_inr("₹1,00,00,000") == 1000000000  # 1 crore (10 million)
        assert parse_inr("₹10,00,00,000") == 10000000000  # 10 crores

    def test_missing_rupee_symbol_raises(self):
        with pytest.raises(ValueError, match="Must start with ₹"):
            parse_inr("1000")
        with pytest.raises(ValueError, match="Must start with ₹"):
            parse_inr("Rs 1000")

    def test_multiple_rupee_symbols_raises(self):
        with pytest.raises(ValueError, match="Multiple ₹"):
            parse_inr("₹1000₹")

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="Negative amounts"):
            parse_inr("₹-100")

    def test_spaces_invalid(self):
        with pytest.raises(ValueError, match="invalid characters"):
            parse_inr("₹1 000")

    def test_invalid_grouping_raises(self):
        # Test that invalid patterns are caught: numbers > 3 digits without grouping
        with pytest.raises(ValueError, match="Ungrouped number must be 1-3"):
            parse_inr("₹1000")  # 4 digits, no comma grouping

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Empty amount"):
            parse_inr("₹")

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="must be str"):
            parse_inr(1000)

    def test_roundtrip(self):
        """Test format -> parse roundtrip (for rupee-aligned amounts).
        
        Note: Amounts not aligned to 100 paise (1 rupee) lose precision during
        formatting since we only display rupees, not paise. E.g., 999 paise -> ₹9 -> 900 paise.
        """
        # Test only multiples of 100 (whole rupees)
        for paise in [0, 100, 1000, 10000, 100000, 125000000, 1000000000]:
            formatted = format_inr(paise)
            parsed = parse_inr(formatted)
            assert parsed == paise, f"Roundtrip failed for {paise}: {formatted}"

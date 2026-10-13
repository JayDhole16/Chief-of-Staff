"""
Pure INR formatter: integer paise <-> Indian grouping string.
Uses Indian numbering system: 12,50,000 not 1,250,000.
Pure: no I/O, no clock, no randomness, deterministic.
"""

import re
from decimal import Decimal


def format_inr(amount_paise: int) -> str:
    """
    Format paise to Indian-grouped INR string with ₹ symbol.
    
    Examples:
        0 -> "₹0"
        100 -> "₹1"
        125000 -> "₹1,250" (1250 rupees)
        1250000 -> "₹12,500" (12500 rupees)
        125000000 -> "₹12,50,000" (1,250,000 rupees)
        -100 -> raises ValueError (money never negative)
    
    Args:
        amount_paise: Non-negative integer paise.
    
    Returns:
        String formatted with ₹ symbol and Indian grouping.
    
    Raises:
        ValueError: If amount_paise < 0 or not an int.
    """
    if not isinstance(amount_paise, int):
        raise ValueError(f"amount_paise must be int, got {type(amount_paise)}")
    if amount_paise < 0:
        raise ValueError(f"amount_paise must be >= 0, got {amount_paise}")

    # Convert paise to rupees string (integer division)
    rupees = amount_paise // 100
    
    # Apply Indian grouping
    grouped = _apply_indian_grouping(rupees)
    return f"₹{grouped}"


def _apply_indian_grouping(num: int) -> str:
    """
    Apply Indian numbering: first group of 3, then groups of 2 from right.
    
    Examples:
        0 -> "0"
        1 -> "1"
        10 -> "10"
        100 -> "100"
        1000 -> "1,000"
        10000 -> "10,000"
        100000 -> "1,00,000"
        1000000 -> "10,00,000"
        1250000 -> "12,50,000"
    """
    num_str = str(num)
    if len(num_str) <= 3:
        return num_str
    
    # Last 3 digits
    last_three = num_str[-3:]
    remaining = num_str[:-3]
    
    # Group remaining in pairs from right
    groups = []
    while len(remaining) > 0:
        if len(remaining) <= 2:
            groups.insert(0, remaining)
            remaining = ""
        else:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
    
    groups.append(last_three)
    return ",".join(groups)


def parse_inr(formatted: str) -> int:
    """
    Parse Indian-formatted INR string to paise.
    Rejects ambiguous input (e.g., malformed grouping, multiple ₹ symbols).
    
    Accepts standard Indian grouping patterns:
      - Optional: first group of 1-3 digits, then groups of exactly 2 digits, then final group of 1-3 digits
      - Simplified: 1-3 digit groups separated by commas (matching what format_inr produces)
    
    Examples:
        "₹0" -> 0
        "₹1" -> 100
        "₹10" -> 1000
        "₹100" -> 10000
        "₹1,000" -> 100000 (1,000 rupees = 100,000 paise)
        "₹10,000" -> 1000000
        "₹1,00,000" -> 10000000 (1,00,000 rupees)
        "₹12,50,000" -> 125000000
        "₹-100" -> raises ValueError
        "₹1 000" -> raises ValueError (spaces invalid)
        "1000" -> raises ValueError (no ₹ symbol)
    
    Args:
        formatted: String with ₹ symbol and optional Indian grouping.
    
    Returns:
        Amount in paise (non-negative integer).
    
    Raises:
        ValueError: If format is invalid or ambiguous.
    """
    if not isinstance(formatted, str):
        raise ValueError(f"Input must be str, got {type(formatted)}")
    
    # Must start with ₹
    if not formatted.startswith("₹"):
        raise ValueError(f"Must start with ₹ symbol, got: {formatted}")
    
    # Remove ₹ and check for multiple symbols
    rest = formatted[1:]
    if "₹" in rest:
        raise ValueError(f"Multiple ₹ symbols not allowed: {formatted}")
    
    # Check for negative
    if rest.startswith("-"):
        raise ValueError(f"Negative amounts not allowed: {formatted}")
    
    # Empty check early
    if rest == "":
        raise ValueError(f"Empty amount: {formatted}")
    
    # Validate no spaces or other special chars
    if " " in rest or any(c not in "0123456789," for c in rest):
        raise ValueError(f"Contains invalid characters: {formatted}")
    
    # Validate grouping if commas present
    if "," in rest:
        parts = rest.split(",")
        # All parts must be 1-3 digits
        for i, part in enumerate(parts):
            if not (1 <= len(part) <= 3):
                raise ValueError(f"Group {i+1} must be 1-3 digits: {formatted}")
            if not part.isdigit():
                raise ValueError(f"Group {i+1} contains non-digits: {formatted}")
    else:
        # No commas: must be 1-3 digits
        if not rest.isdigit():
            raise ValueError(f"Contains non-digits: {formatted}")
        if len(rest) > 3:
            raise ValueError(f"Ungrouped number must be 1-3 digits: {formatted}")
    
    # Extract digits and convert
    digits_only = rest.replace(",", "")
    rupees = int(digits_only)
    return rupees * 100  # Convert to paise

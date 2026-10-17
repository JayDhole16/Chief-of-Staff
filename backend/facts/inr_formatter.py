"""
Pure INR formatter: integer paise <-> Indian grouping string.
Uses Indian numbering system: 12,50,000 not 1,250,000.
Pure: no I/O, no clock, no randomness, deterministic.
"""


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
    """
    if not isinstance(amount_paise, int) or isinstance(amount_paise, bool):
        raise ValueError(f"amount_paise must be int, got {type(amount_paise)}")
    if amount_paise < 0:
        raise ValueError(f"amount_paise must be >= 0, got {amount_paise}")

    rupees = amount_paise // 100
    grouped = _apply_indian_grouping(rupees)
    return f"₹{grouped}"


def _apply_indian_grouping(num: int) -> str:
    """
    Apply Indian numbering: first group of 3 from right, then groups of 2 from right.
    """
    num_str = str(num)
    if len(num_str) <= 3:
        return num_str

    last_three = num_str[-3:]
    remaining = num_str[:-3]

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
      - First group of 1-2 digits, middle groups of 2 digits, final group of 3 digits
      - Or ungrouped 1-3 digits when < 1,000
    """
    if not isinstance(formatted, str):
        raise ValueError(f"Input must be str, got {type(formatted)}")

    if not formatted.startswith("₹"):
        raise ValueError(f"Must start with ₹ symbol, got: {formatted}")

    rest = formatted[1:]
    if "₹" in rest:
        raise ValueError(f"Multiple ₹ symbols not allowed: {formatted}")

    if rest.startswith("-"):
        raise ValueError(f"Negative amounts not allowed: {formatted}")

    if rest == "":
        raise ValueError(f"Empty amount: {formatted}")

    if " " in rest or any(c not in "0123456789," for c in rest):
        raise ValueError(f"Contains invalid characters: {formatted}")

    if "," in rest:
        parts = rest.split(",")
        if not (1 <= len(parts[0]) <= 2) or not parts[0].isdigit():
            raise ValueError(f"Leading group must be 1-2 digits in Indian grouping: {formatted}")
        for i, part in enumerate(parts[1:-1], start=2):
            if len(part) != 2 or not part.isdigit():
                raise ValueError(f"Middle group {i} must be 2 digits in Indian grouping: {formatted}")
        if len(parts[-1]) != 3 or not parts[-1].isdigit():
            raise ValueError(f"Final group must be 3 digits in Indian grouping: {formatted}")
    else:
        if not rest.isdigit():
            raise ValueError(f"Contains non-digits: {formatted}")
        if len(rest) > 3:
            raise ValueError(f"Ungrouped number must be 1-3 digits: {formatted}")

    digits_only = rest.replace(",", "")
    rupees = int(digits_only)
    return rupees * 100

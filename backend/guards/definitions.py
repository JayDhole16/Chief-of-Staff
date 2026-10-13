"""
Guard definitions (G01-G15): safety policy decision points.
Each guard is a pure function that maps facts to a verdict (ALLOW, ASK, BLOCK).

Pure: no I/O, no clock, no randomness, deterministic.
All state passed as arguments. No exceptions for expected failures.
"""

from dataclasses import dataclass
from typing import Literal

Verdict = Literal['ALLOW', 'ASK', 'BLOCK']


@dataclass(frozen=True)
class GuardResult:
    verdict: Verdict
    reason: str  # Why this verdict was chosen


# Guard definitions (what each guard checks)
GUARD_DESCRIPTIONS = {
    'G01': 'Session is valid and active',
    'G02': 'User has permission for this operation',
    'G03': 'Amount is under daily transaction limit',
    'G04': 'Customer contact is verified and not blacklisted',
    'G05': 'Deal scope matches task scope (no cross-contact leakage)',
    'G06': 'Verified facts contain all required fields',
    'G07': 'Model-drafted text matches verified facts (prices, discounts)',
    'G08': 'No fabricated claims (e.g., promised discount not in facts)',
    'G09': 'Currency is consistent (INR only)',
    'G10': 'Discount doesn\'t exceed mandate max',
    'G11': 'Price doesn\'t fall below floor price',
    'G12': 'Contact hasn\'t opted out of automated replies',
    'G13': 'Time window check (business hours, deal expiry)',
    'G14': 'No personal/sensitive information in draft',
    'G15': 'Spelling/grammar check on model draft',
}


def list_guards() -> dict[str, str]:
    """Return all guard IDs and descriptions."""
    return GUARD_DESCRIPTIONS


def validate_guard_id(guard_id: str) -> bool:
    """Check if guard_id is valid (G01-G15)."""
    return guard_id in GUARD_DESCRIPTIONS

"""
Pure domain types for Chief of Staff.
No I/O, no clock, no randomness. All types are immutable and hashable.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import TypeAlias


class Currency(str, Enum):
    """Supported currencies."""
    INR = "INR"


# Money: integer minor units (paise), never floats
MoneyMinorUnits: TypeAlias = int  # Always paise (1/100 INR)


@dataclass(frozen=True)
class Money:
    """
    Immutable money type: integer minor units (paise).
    Never use floats. Always store as paise (100 paise = 1 rupee).
    """
    amount_paise: int
    currency: Currency = Currency.INR

    def __post_init__(self) -> None:
        if not isinstance(self.amount_paise, int) or isinstance(self.amount_paise, bool):
            raise TypeError(f"amount_paise must be int, got {type(self.amount_paise)}")
        if self.amount_paise < 0:
            raise ValueError(f"amount_paise must be >= 0, got {self.amount_paise}")

    def to_rupees(self) -> Decimal:
        """Convert to rupees as Decimal for display/calc."""
        return Decimal(self.amount_paise) / Decimal(100)

    @staticmethod
    def from_rupees(rupees: int | Decimal) -> "Money":
        """Create Money from rupees (int or Decimal), convert to paise."""
        if isinstance(rupees, bool) or not isinstance(rupees, (int, Decimal)):
            raise TypeError(f"rupees must be int or Decimal, got {type(rupees)}")
        if isinstance(rupees, Decimal):
            paise = int((rupees * Decimal(100)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        else:
            paise = rupees * 100
        return Money(paise)


@dataclass(frozen=True)
class FactReference:
    """Immutable reference to a fact source."""
    fact_id: str
    source: str  # e.g. "mandate", "db", "api"


@dataclass(frozen=True)
class FactValue:
    """A verified fact with its origin."""
    value: int | str | Money | Decimal
    ref: FactReference


@dataclass(frozen=True)
class TrustedFacts:
    """
    Immutable set of verified, typed facts.
    Only facts in this dict are allowed in templates.
    """
    facts: dict[str, FactValue]

    def __post_init__(self) -> None:
        # Defensive shallow copy so external mutation of caller's dict cannot alter TrustedFacts
        object.__setattr__(self, "facts", dict(self.facts))

    def get(self, key: str) -> FactValue | None:
        """Retrieve a fact by key."""
        return self.facts.get(key)

    def require(self, key: str) -> FactValue:
        """Retrieve a fact or raise KeyError if missing."""
        if key not in self.facts:
            raise KeyError(f"Fact not found: {key}")
        return self.facts[key]


class DiscountType(str, Enum):
    """Discount types for offer calculations."""
    PERCENTAGE = "percentage"
    FLAT = "flat"


@dataclass(frozen=True)
class Discount:
    """Immutable discount specification."""
    type: DiscountType
    value: int  # percentage (0-100) or paise

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise TypeError(f"Discount value must be int, got {type(self.value)}")
        if self.type == DiscountType.PERCENTAGE:
            if not (0 <= self.value <= 100):
                raise ValueError(f"Percentage must be 0-100, got {self.value}")
        elif self.value < 0:
            raise ValueError(f"Discount value must be >= 0, got {self.value}")

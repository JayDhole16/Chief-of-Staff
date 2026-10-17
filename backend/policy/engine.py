"""Pure policy evaluator based on the currently checked-in provisional guard registry."""

from dataclasses import dataclass

from backend.guards.definitions import Verdict


@dataclass(frozen=True)
class PolicyInput:
    session_valid: bool
    permission_granted: bool
    amount_paise: int
    daily_limit_paise: int
    contact_verified: bool
    task_scope_matches: bool
    required_facts_present: bool
    draft_grounded: bool
    unverified_commitment: bool
    currency: str
    discount_pct: int
    mandate_max_discount_pct: int
    price_paise: int
    floor_price_paise: int
    opted_out: bool
    within_business_window: bool
    contains_sensitive_data: bool
    grammar_ok: bool
    explicit_founder_approval: bool = False

    def __post_init__(self) -> None:
        numeric = {
            "amount_paise": self.amount_paise,
            "daily_limit_paise": self.daily_limit_paise,
            "discount_pct": self.discount_pct,
            "mandate_max_discount_pct": self.mandate_max_discount_pct,
            "price_paise": self.price_paise,
            "floor_price_paise": self.floor_price_paise,
        }
        for name, value in numeric.items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.discount_pct > 100 or self.mandate_max_discount_pct > 100:
            raise ValueError("Discount percentages must be between 0 and 100")


@dataclass(frozen=True)
class PolicyDecision:
    verdict: Verdict
    guards_triggered: tuple[str, ...]
    reasons: tuple[str, ...]


def evaluate_policy(inputs: PolicyInput) -> PolicyDecision:
    """Evaluate all provisional guards. Blocking checks cannot be overridden by approval."""
    triggered: list[tuple[str, Verdict, str]] = []
    checks: tuple[tuple[str, bool, Verdict, str], ...] = (
        ("G01", inputs.session_valid, "BLOCK", "Session is invalid or inactive."),
        (
            "G02",
            inputs.permission_granted,
            "BLOCK",
            "The caller lacks permission for this operation.",
        ),
        (
            "G03",
            inputs.amount_paise <= inputs.daily_limit_paise,
            "BLOCK",
            "The action exceeds the daily transaction limit.",
        ),
        ("G04", inputs.contact_verified, "BLOCK", "The customer contact is not verified."),
        ("G05", inputs.task_scope_matches, "BLOCK", "The action does not match its task scope."),
        ("G06", inputs.required_facts_present, "BLOCK", "Required verified facts are missing."),
        ("G07", inputs.draft_grounded, "ASK", "The draft is not fully grounded in verified facts."),
        (
            "G08",
            not inputs.unverified_commitment,
            "ASK",
            "The draft depends on an unverified customer commitment claim.",
        ),
        (
            "G09",
            inputs.currency == "INR",
            "BLOCK",
            "Only INR is supported by this provisional policy.",
        ),
        (
            "G10",
            inputs.discount_pct <= inputs.mandate_max_discount_pct,
            "ASK",
            "The discount exceeds the mandate limit.",
        ),
        (
            "G11",
            inputs.price_paise >= inputs.floor_price_paise,
            "BLOCK",
            "The price is below the approved floor.",
        ),
        ("G12", not inputs.opted_out, "BLOCK", "The contact has opted out of automated replies."),
        (
            "G13",
            inputs.within_business_window,
            "ASK",
            "The action is outside the permitted business window.",
        ),
        (
            "G14",
            not inputs.contains_sensitive_data,
            "BLOCK",
            "The draft contains sensitive personal information.",
        ),
        ("G15", inputs.grammar_ok, "ASK", "The draft failed the configured quality check."),
    )
    for guard_id, passed, failure_verdict, reason in checks:
        if not passed:
            triggered.append((guard_id, failure_verdict, reason))

    if any(verdict == "BLOCK" for _, verdict, _ in triggered):
        verdict: Verdict = "BLOCK"
    elif triggered and not inputs.explicit_founder_approval:
        verdict = "ASK"
    else:
        verdict = "ALLOW"
    return PolicyDecision(
        verdict=verdict,
        guards_triggered=tuple(item[0] for item in triggered),
        reasons=tuple(item[2] for item in triggered),
    )

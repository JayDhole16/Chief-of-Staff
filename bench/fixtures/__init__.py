"""Benchmark fixture loading and resolution utilities."""

from copy import deepcopy
from pathlib import Path
from typing import Any
import re
import yaml

FIXTURES_DIR = Path(__file__).resolve().parent
BASE_PATH = FIXTURES_DIR / "base.yaml"

CONTACT_MAP = {
    "CT-1": "raju@malhotralogistics.bench.invalid",
    "CT-2": "raju.iyer@iyertextiles.bench.invalid",
    "CT-3": "priya@brightleafclinics.bench.invalid",
    "CT-4": "arjun@kestrelfoods.bench.invalid",
    "CT-5": "ananya.rao@northwindstudio.bench.invalid",
    "CT-6": "farhan.ali@coastalrealty.bench.invalid",
}

THREAD_MAP = {
    "D-1": "thread_d1_bench_001",
    "D-2": "thread_d2_bench_002",
    "D-3": "thread_d3_bench_003",
    "D-4": "thread_d4_bench_004",
    "D-5": "thread_d5_bench_005",
    "D-6": "thread_d6_bench_006",
}


def load_base_fixture() -> dict[str, Any]:
    """Load canonical bench_base world state."""
    with open(BASE_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_placeholders(text: str, overlay: dict[str, Any] | None = None) -> str:
    """Resolve ${CONTACT_EMAIL:CT-n} and ${THREAD_OF:D-n} placeholders."""
    if not isinstance(text, str):
        return text

    def replace_token(match: re.Match) -> str:
        token = match.group(1)
        if token.startswith("CONTACT_EMAIL:"):
            ref = token.split(":", 1)[1]
            if ref in CONTACT_MAP:
                return CONTACT_MAP[ref]
            if overlay and "contacts" in overlay:
                for c in overlay["contacts"]:
                    if c.get("ref") == ref and "email" in c:
                        return c["email"]
            return f"{ref.lower()}@custom.bench.invalid"
        elif token.startswith("THREAD_OF:"):
            ref = token.split(":", 1)[1]
            if ref in THREAD_MAP:
                return THREAD_MAP[ref]
            return f"thread_{ref.lower()}_bench"
        return match.group(0)

    return re.sub(r"\$\{([^}]+)\}", replace_token, text)


def build_scenario_initial_state(scenario_data: dict[str, Any]) -> dict[str, Any]:
    """Construct initial state by applying scenario overlay to bench_base."""
    state = deepcopy(load_base_fixture())
    initial_spec = scenario_data.get("initial_state", {})
    state["mandate_type"] = initial_spec.get("mandate", "standard")
    overlay = initial_spec.get("overlay", {})

    # Apply deal overlays
    if "deals" in overlay:
        for deal_override in overlay["deals"]:
            d_ref = deal_override.get("ref")
            if d_ref in state["deals"]:
                state["deals"][d_ref].update(deal_override)
            else:
                state["deals"][d_ref] = deal_override

    # Apply contact overlays
    if "contacts" in overlay:
        for contact_override in overlay["contacts"]:
            c_ref = contact_override.get("ref")
            if c_ref in state["contacts"]:
                state["contacts"][c_ref].update(contact_override)
            else:
                state["contacts"][c_ref] = contact_override

    return state

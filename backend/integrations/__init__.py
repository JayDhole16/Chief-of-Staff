"""
Integrations package providing Ports and Adapters for external services.
"""

from dataclasses import dataclass

from .evolus import AdapterTestResult, EvolusPort, FakeEvolusClient
from .google import GooglePort, FakeGoogleClient
from .model import ModelPort, FakeModelClient


@dataclass
class Adapters:
    evolus: EvolusPort
    model: ModelPort
    google: GooglePort


def build_adapters() -> Adapters:
    """Build adapters instance. Single swap point for real adapters in future slices."""
    return Adapters(
        evolus=FakeEvolusClient(),
        model=FakeModelClient(),
        google=FakeGoogleClient(),
    )


__all__ = [
    "AdapterTestResult",
    "Adapters",
    "EvolusPort",
    "FakeEvolusClient",
    "GooglePort",
    "FakeGoogleClient",
    "ModelPort",
    "FakeModelClient",
    "build_adapters",
]

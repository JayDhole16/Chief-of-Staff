"""
Evolus Integration Port and Fake Adapter.
"""

from typing import NamedTuple, Protocol, runtime_checkable


class AdapterTestResult(NamedTuple):
    ok: bool
    message: str


@runtime_checkable
class EvolusPort(Protocol):
    def test_connection(self, api_key: str | None = None) -> AdapterTestResult:
        ...


class FakeEvolusClient:
    def test_connection(self, api_key: str | None = None) -> AdapterTestResult:
        return AdapterTestResult(
            ok=True,
            message="fake evolus adapter: connection ok",
        )

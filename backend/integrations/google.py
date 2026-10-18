"""
Google Integration Port and Fake Adapter.
"""

from typing import Protocol, runtime_checkable

from backend.integrations.evolus import AdapterTestResult


@runtime_checkable
class GooglePort(Protocol):
    def test_connection(self) -> AdapterTestResult:
        ...


class FakeGoogleClient:
    def test_connection(self) -> AdapterTestResult:
        return AdapterTestResult(
            ok=True,
            message="fake google adapter: connection ok",
        )

"""
Model Endpoint Integration Port and Fake Adapter.
"""

from typing import Protocol, runtime_checkable

from backend.integrations.evolus import AdapterTestResult


@runtime_checkable
class ModelPort(Protocol):
    def test_connection(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
    ) -> AdapterTestResult:
        ...


class FakeModelClient:
    def test_connection(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
    ) -> AdapterTestResult:
        return AdapterTestResult(
            ok=True,
            message="fake model adapter: connection ok",
        )

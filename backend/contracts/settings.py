"""
Settings and Integrations Contract Models.

Pure contracts defining request and response schemas for:
- GET /api/settings (SystemSettingsSchema with integrations field)
- PUT /api/integrations/evolus
- PUT /api/integrations/model
- PUT /api/integrations/google
- POST /api/integrations/{name}/test
"""

from datetime import datetime
from typing import Literal

import pydantic
from backend.contracts import CompatBaseModel

PYDANTIC_V2 = pydantic.__version__.startswith("2.")
if PYDANTIC_V2:
    from pydantic import ConfigDict


class EvolusConfigUpdate(CompatBaseModel):
    api_key: str | None = None


class ModelConfigUpdate(CompatBaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="forbid", protected_namespaces=())

    base_url: str | None = None
    model_name: str | None = None
    api_key: str | None = None


class GoogleConnectionUpdate(CompatBaseModel):
    action: Literal["connect", "disconnect"]


class EvolusSettingsView(CompatBaseModel):
    status: Literal["not_configured", "configured", "error"]
    masked_api_key: str | None = None
    last_tested_at: datetime | None = None
    last_test_result: Literal["ok", "failed"] | None = None
    last_test_message: str | None = None


class ModelSettingsView(CompatBaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="forbid", protected_namespaces=())

    status: Literal["not_configured", "configured", "error"]
    base_url: str | None = None
    model_name: str | None = None
    masked_api_key: str | None = None
    last_tested_at: datetime | None = None
    last_test_result: Literal["ok", "failed"] | None = None
    last_test_message: str | None = None


class GoogleSettingsView(CompatBaseModel):
    status: Literal["not_configured", "connected", "error"]
    connected: bool
    last_tested_at: datetime | None = None
    last_test_result: Literal["ok", "failed"] | None = None
    last_test_message: str | None = None


class IntegrationsSection(CompatBaseModel):
    evolus: EvolusSettingsView
    model: ModelSettingsView
    google: GoogleSettingsView


class IntegrationTestResult(CompatBaseModel):
    name: str
    ok: bool
    message: str
    tested_at: datetime


__all__ = [
    "EvolusConfigUpdate",
    "ModelConfigUpdate",
    "GoogleConnectionUpdate",
    "EvolusSettingsView",
    "ModelSettingsView",
    "GoogleSettingsView",
    "IntegrationsSection",
    "IntegrationTestResult",
]

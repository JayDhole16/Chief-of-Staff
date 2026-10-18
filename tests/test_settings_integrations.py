"""
Tests for Settings & Integrations Backend Slice.

Covers:
1. Task 1 Contracts: Model imports, view defaults, and extra="forbid" raising ValidationError.
2. Task 2 Store & Masking:
   - mask_secret unit tests (long key last-4, short key fully masked, empty/None).
   - SettingsStore roundtrip save/load in tmp_path.
   - File created only after save.
   - Corrupt store fallback to defaults without overwrite (test_corrupt_store_file_falls_back_to_defaults).
3. Task 3 Adapters:
   - Each fake returns ok=True and message containing "fake".
   - build_adapters() returns ports.
4. Task 4 Endpoints & Review Focus:
   - Defaults on startup.
   - test_put_evolus_key_never_echoed_and_get_masks_it.
   - test_evolus_put_null_keeps_existing_key.
   - PUT model set / keep / clear.
   - PUT google connect / disconnect.
   - /test 200, 409, 404 paths.
   - 422 on extra / unknown fields.
   - Store persistence across /api/dev/reset-demo.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api.app import app, state
from backend.contracts.settings import (
    EvolusConfigUpdate,
    EvolusSettingsView,
    GoogleConnectionUpdate,
    GoogleSettingsView,
    IntegrationsSection,
    IntegrationTestResult,
    ModelConfigUpdate,
    ModelSettingsView,
)
from backend.integrations import (
    Adapters,
    EvolusPort,
    GooglePort,
    ModelPort,
    build_adapters,
)
from backend.services.settings_store import (
    EvolusConfig,
    ModelConfig,
    SettingsStore,
    load_settings,
    mask_secret,
)


@pytest.fixture(autouse=True)
def isolated_settings_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point SETTINGS_STORE_PATH to a temporary isolated file for every test."""
    temp_file = tmp_path / "settings.local.json"
    monkeypatch.setenv("SETTINGS_STORE_PATH", str(temp_file))
    state.reset()
    yield temp_file
    state.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Task 1: Contracts Module Unit Tests
# ---------------------------------------------------------------------------

def test_contracts_imports_and_view_defaults():
    """Verify contracts import cleanly and have correct default fields."""
    ev_view = EvolusSettingsView(status="not_configured")
    assert ev_view.status == "not_configured"
    assert ev_view.masked_api_key is None
    assert ev_view.last_tested_at is None
    assert ev_view.last_test_result is None
    assert ev_view.last_test_message is None

    mo_view = ModelSettingsView(status="not_configured")
    assert mo_view.status == "not_configured"
    assert mo_view.base_url is None
    assert mo_view.model_name is None
    assert mo_view.masked_api_key is None

    g_view = GoogleSettingsView(status="connected", connected=True)
    assert g_view.connected is True
    assert g_view.status == "connected"

    sec = IntegrationsSection(evolus=ev_view, model=mo_view, google=g_view)
    assert sec.evolus.status == "not_configured"

    res = IntegrationTestResult(
        name="evolus",
        ok=True,
        message="ok",
        tested_at=datetime.now(timezone.utc),
    )
    assert res.name == "evolus"


def test_contracts_extra_fields_forbidden_validation_error():
    """extra='forbid' raises ValidationError on an unknown field."""
    with pytest.raises(ValidationError):
        EvolusConfigUpdate.model_validate({"api_key": "x", "unknown_field": "bad"})

    with pytest.raises(ValidationError):
        ModelConfigUpdate.model_validate({"base_url": "http://x", "extra_param": 123})

    with pytest.raises(ValidationError):
        GoogleConnectionUpdate.model_validate({"action": "connect", "foo": "bar"})


# ---------------------------------------------------------------------------
# Task 2: Settings Store + Masking Unit Tests
# ---------------------------------------------------------------------------

def test_mask_secret_unit_cases():
    """mask_secret unit cases (long key last-4, short key fully masked, empty/None)."""
    assert mask_secret("12345678") == "••••5678"
    assert mask_secret("token-dummy-123456") == "••••3456"
    assert mask_secret("a" * 50 + "wxyz") == "••••wxyz"

    assert mask_secret("1234567") == "••••"
    assert mask_secret("1234") == "••••"
    assert mask_secret("x") == "••••"

    assert mask_secret("") is None
    assert mask_secret(None) is None


def test_settings_store_file_created_only_after_save(tmp_path: Path):
    """Store file is NOT created on read; it is created only after save."""
    store_file = tmp_path / "custom_settings.json"
    store = SettingsStore(store_file)

    # File does not exist yet; reading returns defaults and does NOT touch disk
    ev_default = store.load_evolus()
    assert ev_default.api_key is None
    assert not store_file.exists()

    mo_default = store.load_model()
    assert mo_default.base_url is None
    assert not store_file.exists()

    # Saving creates the file
    store.save_evolus(EvolusConfig(api_key="stored-test-token-1111"))
    assert store_file.exists()

    loaded = store.load_evolus()
    assert loaded.api_key == "stored-test-token-1111"


def test_settings_store_roundtrip_save_load(tmp_path: Path):
    """SettingsStore roundtrip save/load in tmp_path."""
    store_file = tmp_path / "roundtrip.json"
    store = SettingsStore(store_file)

    store.save_evolus(EvolusConfig(api_key="token-a-1234", last_test_result="ok"))
    store.save_model(ModelConfig(base_url="https://api.example.com", model_name="gpt-4o"))

    ev = store.load_evolus()
    assert ev.api_key == "token-a-1234"
    assert ev.last_test_result == "ok"

    mo = store.load_model()
    assert mo.base_url == "https://api.example.com"
    assert mo.model_name == "gpt-4o"


def test_corrupt_store_file_falls_back_to_defaults(client: TestClient, isolated_settings_store: Path):
    """Corrupt store file -> defaults, endpoint still 200, no overwrite until PUT."""
    corrupted_content = "{ invalid json syntax: true, missing_braces"
    isolated_settings_store.write_text(corrupted_content, encoding="utf-8")

    # Endpoint must not crash (returns defaults)
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["integrations"]["evolus"]["status"] == "not_configured"
    assert data["integrations"]["model"]["status"] == "not_configured"

    # Must NOT overwrite corrupted file on read
    assert isolated_settings_store.read_text(encoding="utf-8") == corrupted_content

    # Next successful PUT successfully overwrites with valid JSON
    put_res = client.put("/api/integrations/evolus", json={"api_key": "recovered-valid-token"})
    assert put_res.status_code == 200
    assert put_res.json()["status"] == "configured"

    new_content = isolated_settings_store.read_text(encoding="utf-8")
    parsed = json.loads(new_content)
    assert parsed["evolus"]["api_key"] == "recovered-valid-token"


# ---------------------------------------------------------------------------
# Task 3: Adapter Ports and Fakes Unit Tests
# ---------------------------------------------------------------------------

def test_fake_adapters_and_ports():
    """Each fake returns ok=True and message containing 'fake'; build_adapters() returns ports."""
    adapters: Adapters = build_adapters()

    assert isinstance(adapters.evolus, EvolusPort)
    assert isinstance(adapters.model, ModelPort)
    assert isinstance(adapters.google, GooglePort)

    ev_res = adapters.evolus.test_connection(api_key="token-123")
    assert ev_res.ok is True
    assert ev_res.message.startswith("fake evolus adapter:")

    mo_res = adapters.model.test_connection(base_url="http://localhost:8000")
    assert mo_res.ok is True
    assert mo_res.message.startswith("fake model adapter:")

    g_res = adapters.google.test_connection()
    assert g_res.ok is True
    assert g_res.message.startswith("fake google adapter:")


# ---------------------------------------------------------------------------
# Task 4 & Review Focus: Endpoints and Lifecycle Integration Tests
# ---------------------------------------------------------------------------

def test_defaults_on_fresh_startup(client: TestClient):
    """Defaults: GET shows evolus/model not_configured, google connected (seeded state)."""
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()

    # Legacy sections intact
    assert data["founder"]["name"] == "Meera Nair"
    assert data["google_account"]["connected"] is True
    assert data["kill_switch"]["active"] is False

    # Integrations section verified
    integrations = data["integrations"]
    assert integrations["evolus"]["status"] == "not_configured"
    assert integrations["evolus"]["masked_api_key"] is None
    assert integrations["evolus"]["last_tested_at"] is None
    assert integrations["evolus"]["last_test_result"] is None
    assert integrations["evolus"]["last_test_message"] is None

    assert integrations["model"]["status"] == "not_configured"
    assert integrations["model"]["base_url"] is None
    assert integrations["model"]["model_name"] is None
    assert integrations["model"]["masked_api_key"] is None
    assert integrations["model"]["last_tested_at"] is None

    assert integrations["google"]["status"] == "connected"
    assert integrations["google"]["connected"] is True
    assert integrations["google"]["last_tested_at"] is None


def test_put_evolus_key_never_echoed_and_get_masks_it(client: TestClient, isolated_settings_store: Path):
    """
    Review Focus: Raw key leakage.
    Assert raw value is absent from both PUT and GET response texts.
    """
    secret_key = "evolus-dummy-token-12345678"
    res = client.put("/api/integrations/evolus", json={"api_key": secret_key})
    assert res.status_code == 200
    put_data = res.json()

    assert put_data["status"] == "configured"
    assert put_data["masked_api_key"] == "••••5678"

    # Security Invariant: Raw key NEVER returned in PUT body
    assert secret_key not in res.text

    # Security Invariant: Raw key NEVER returned in GET /api/settings
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    assert secret_key not in get_res.text
    assert get_res.json()["integrations"]["evolus"]["masked_api_key"] == "••••5678"

    # Persistence proven by reading store file directly from disk
    assert isolated_settings_store.exists()
    file_content = isolated_settings_store.read_text(encoding="utf-8")
    assert secret_key in file_content

    fresh_store = load_settings(isolated_settings_store)
    assert fresh_store.evolus.api_key == secret_key


def test_evolus_put_null_keeps_existing_key(client: TestClient, isolated_settings_store: Path):
    """
    Review Focus: Merge-rule correctness.
    PUT null / omitted keeps existing key; "" clears.
    """
    # 1. Set key
    client.put("/api/integrations/evolus", json={"api_key": "my-dummy-token-9999"})
    res = client.get("/api/settings")
    assert res.json()["integrations"]["evolus"]["masked_api_key"] == "••••9999"

    # 2. PUT null -> keeps existing key
    res_keep_null = client.put("/api/integrations/evolus", json={"api_key": None})
    assert res_keep_null.status_code == 200
    assert res_keep_null.json()["status"] == "configured"
    assert res_keep_null.json()["masked_api_key"] == "••••9999"

    # 3. PUT omitted ({}) -> keeps existing key
    res_keep_empty = client.put("/api/integrations/evolus", json={})
    assert res_keep_empty.status_code == 200
    assert res_keep_empty.json()["masked_api_key"] == "••••9999"

    # 4. PUT "" -> clears
    res_clear = client.put("/api/integrations/evolus", json={"api_key": ""})
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "not_configured"
    assert res_clear.json()["masked_api_key"] is None

    fresh_store = load_settings(isolated_settings_store)
    assert fresh_store.evolus.api_key is None

    # 5. Non-empty string with surrounding spaces -> trimmed and set
    res_trimmed = client.put("/api/integrations/evolus", json={"api_key": "   new-trimmed-token-8888   "})
    assert res_trimmed.status_code == 200
    assert res_trimmed.json()["masked_api_key"] == "••••8888"
    assert load_settings(isolated_settings_store).evolus.api_key == "new-trimmed-token-8888"


def test_put_model_and_merge_semantics(client: TestClient, isolated_settings_store: Path):
    """PUT null keeps, \"\" clears — for model endpoint fields."""
    secret_model_key = "model-dummy-token-4321"

    # 1. Initial configuration
    res = client.put(
        "/api/integrations/model",
        json={
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o",
            "api_key": secret_model_key,
        },
    )
    assert res.status_code == 200
    view = res.json()
    assert view["status"] == "configured"
    assert view["base_url"] == "https://api.openai.com/v1"
    assert view["model_name"] == "gpt-4o"
    assert view["masked_api_key"] == "••••4321"

    # Raw secret leak check
    assert secret_model_key not in res.text
    assert secret_model_key not in client.get("/api/settings").text
    assert secret_model_key in isolated_settings_store.read_text(encoding="utf-8")

    # 2. Partial PUT with nulls: change model_name, keep base_url and api_key
    res_partial = client.put(
        "/api/integrations/model",
        json={"model_name": "gpt-4o-mini", "base_url": None, "api_key": None},
    )
    assert res_partial.status_code == 200
    pview = res_partial.json()
    assert pview["base_url"] == "https://api.openai.com/v1"
    assert pview["model_name"] == "gpt-4o-mini"
    assert pview["masked_api_key"] == "••••4321"

    # 3. Clear api_key: "" clears api_key; model remains configured because base_url is present
    res_clear_key = client.put("/api/integrations/model", json={"api_key": ""})
    assert res_clear_key.status_code == 200
    ck_view = res_clear_key.json()
    assert ck_view["status"] == "configured"  # local vLLM / keyless endpoint
    assert ck_view["masked_api_key"] is None
    assert ck_view["base_url"] == "https://api.openai.com/v1"

    # 4. Clear base_url: "" clears base_url -> becomes not_configured
    res_clear_url = client.put("/api/integrations/model", json={"base_url": ""})
    assert res_clear_url.status_code == 200
    assert res_clear_url.json()["status"] == "not_configured"
    assert res_clear_url.json()["base_url"] is None


def test_put_google_connect_disconnect_toggles(client: TestClient):
    """PUT google connect/disconnect toggles the view; /test reflects it."""
    # Seeded state is connected
    res0 = client.get("/api/settings")
    assert res0.json()["integrations"]["google"]["connected"] is True
    assert res0.json()["integrations"]["google"]["status"] == "connected"
    assert res0.json()["google_account"]["connected"] is True

    # Disconnect
    res_disc = client.put("/api/integrations/google", json={"action": "disconnect"})
    assert res_disc.status_code == 200
    assert res_disc.json()["connected"] is False
    assert res_disc.json()["status"] == "not_configured"

    # GET /api/settings matches
    res_get_disc = client.get("/api/settings")
    assert res_get_disc.json()["integrations"]["google"]["connected"] is False
    assert res_get_disc.json()["integrations"]["google"]["status"] == "not_configured"
    assert res_get_disc.json()["google_account"]["connected"] is False

    # Connect again
    res_conn = client.put("/api/integrations/google", json={"action": "connect"})
    assert res_conn.status_code == 200
    assert res_conn.json()["connected"] is True
    assert res_conn.json()["status"] == "connected"


def test_test_integration_endpoint_rules_and_lifecycle(client: TestClient):
    """
    /test:
    - 200 + recorded last_tested_at when configured
    - 409 unconfigured
    - 404 unknown integration name
    """
    # 1. 404 on unknown name
    res_404 = client.post("/api/integrations/nonexistent_service/test")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()

    # 2. 409 when unconfigured (Evolus)
    res_ev_409 = client.post("/api/integrations/evolus/test")
    assert res_ev_409.status_code == 409
    assert "evolus is not configured" in res_ev_409.json()["detail"]

    # 3. 409 when unconfigured (Model)
    res_model_409 = client.post("/api/integrations/model/test")
    assert res_model_409.status_code == 409
    assert "model is not configured" in res_model_409.json()["detail"]

    # 4. 409 when Google disconnected
    client.put("/api/integrations/google", json={"action": "disconnect"})
    res_goog_409 = client.post("/api/integrations/google/test")
    assert res_goog_409.status_code == 409
    assert "google is not connected" in res_goog_409.json()["detail"]

    # 5. Test Google when connected -> 200
    client.put("/api/integrations/google", json={"action": "connect"})
    res_goog_200 = client.post("/api/integrations/google/test")
    assert res_goog_200.status_code == 200
    gdata = res_goog_200.json()
    assert gdata["name"] == "google"
    assert gdata["ok"] is True
    assert "fake google adapter: connection ok" in gdata["message"]
    assert gdata["tested_at"] is not None

    # Check GET /api/settings records Google test metadata
    goog_view = client.get("/api/settings").json()["integrations"]["google"]
    assert goog_view["last_tested_at"] is not None
    assert goog_view["last_test_result"] == "ok"
    assert goog_view["last_test_message"] == "fake google adapter: connection ok"

    # 6. Test Evolus when configured -> 200
    client.put("/api/integrations/evolus", json={"api_key": "evolus-test-token-5555"})
    res_ev_200 = client.post("/api/integrations/evolus/test")
    assert res_ev_200.status_code == 200
    ev_data = res_ev_200.json()
    assert ev_data["name"] == "evolus"
    assert ev_data["ok"] is True
    assert "fake evolus adapter: connection ok" in ev_data["message"]

    # Check GET /api/settings records Evolus test metadata from store
    ev_view = client.get("/api/settings").json()["integrations"]["evolus"]
    assert ev_view["last_tested_at"] is not None
    assert ev_view["last_test_result"] == "ok"
    assert ev_view["last_test_message"] == "fake evolus adapter: connection ok"

    # 7. Test Model when configured (keyless endpoint) -> 200
    client.put("/api/integrations/model", json={"base_url": "http://localhost:8000/v1"})
    res_model_200 = client.post("/api/integrations/model/test")
    assert res_model_200.status_code == 200
    mdata = res_model_200.json()
    assert mdata["name"] == "model"
    assert mdata["ok"] is True
    assert "fake model adapter: connection ok" in mdata["message"]

    mview = client.get("/api/settings").json()["integrations"]["model"]
    assert mview["last_tested_at"] is not None
    assert mview["last_test_result"] == "ok"
    assert mview["last_test_message"] == "fake model adapter: connection ok"


def test_extra_fields_forbidden_422(client: TestClient):
    """extra=\"forbid\" -> 422 on an unknown field."""
    res1 = client.put("/api/integrations/evolus", json={"api_key": "key", "unknown_field": "bad"})
    assert res1.status_code == 422

    res2 = client.put(
        "/api/integrations/model",
        json={"base_url": "https://api.example.com", "extra_param": 123},
    )
    assert res2.status_code == 422

    res3 = client.put(
        "/api/integrations/google",
        json={"action": "connect", "foo": "bar"},
    )
    assert res3.status_code == 422

    res4 = client.put("/api/integrations/google", json={"action": "unsupported_action"})
    assert res4.status_code == 422


def test_store_survives_demo_reset(client: TestClient):
    """Settings store survives /api/dev/reset-demo."""
    # 1. Configure integration
    dummy_key = "saved-token-1234"
    client.put("/api/integrations/evolus", json={"api_key": dummy_key})
    assert client.get("/api/settings").json()["integrations"]["evolus"]["status"] == "configured"

    # 2. Trigger demo reset
    res_reset = client.post("/api/dev/reset-demo")
    assert res_reset.status_code == 200

    # 3. Settings still configured!
    res_after = client.get("/api/settings")
    assert res_after.status_code == 200
    assert res_after.json()["integrations"]["evolus"]["status"] == "configured"
    assert res_after.json()["integrations"]["evolus"]["masked_api_key"] == "••••1234"

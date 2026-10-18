"""
Settings Store Service (Persistence, Merge Semantics, and Masking).

Loads and saves git-ignored `settings.local.json`.
Provides atomic file writes, raw secret isolation, and masking helpers.
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Literal

from backend.contracts.settings import (
    EvolusConfigUpdate,
    EvolusSettingsView,
    GoogleSettingsView,
    IntegrationsSection,
    ModelConfigUpdate,
    ModelSettingsView,
)


def mask_secret(v: str | None) -> str | None:
    """
    Mask a secret value.

    Returns "••••" + last 4 characters if length >= 8, else "••••".
    Returns None if value is None or empty string.
    """
    if not v:
        return None
    if len(v) >= 8:
        return "••••" + v[-4:]
    return "••••"


def get_settings_store_path() -> Path:
    """Return configured settings store path or default to settings.local.json at repo root."""
    env_path = os.getenv("SETTINGS_STORE_PATH")
    if env_path and env_path.strip():
        return Path(env_path.strip())
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "settings.local.json"


@dataclass
class EvolusStoreRecord:
    api_key: str | None = None
    last_tested_at: str | None = None
    last_test_result: str | None = None
    last_test_message: str | None = None


@dataclass
class ModelStoreRecord:
    base_url: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    last_tested_at: str | None = None
    last_test_result: str | None = None
    last_test_message: str | None = None


@dataclass
class SettingsStoreData:
    evolus: EvolusStoreRecord = field(default_factory=EvolusStoreRecord)
    model: ModelStoreRecord = field(default_factory=ModelStoreRecord)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evolus": {
                "api_key": self.evolus.api_key,
                "last_tested_at": self.evolus.last_tested_at,
                "last_test_result": self.evolus.last_test_result,
                "last_test_message": self.evolus.last_test_message,
            },
            "model": {
                "base_url": self.model.base_url,
                "model_name": self.model.model_name,
                "api_key": self.model.api_key,
                "last_tested_at": self.model.last_tested_at,
                "last_test_result": self.model.last_test_result,
                "last_test_message": self.model.last_test_message,
            },
        }

    @classmethod
    def from_dict(cls, data: Any) -> "SettingsStoreData":
        if not isinstance(data, dict):
            return cls()

        evolus_raw = data.get("evolus")
        model_raw = data.get("model")

        evolus = EvolusStoreRecord(
            api_key=evolus_raw.get("api_key") if isinstance(evolus_raw, dict) else None,
            last_tested_at=evolus_raw.get("last_tested_at") if isinstance(evolus_raw, dict) else None,
            last_test_result=evolus_raw.get("last_test_result") if isinstance(evolus_raw, dict) else None,
            last_test_message=evolus_raw.get("last_test_message") if isinstance(evolus_raw, dict) else None,
        )

        model = ModelStoreRecord(
            base_url=model_raw.get("base_url") if isinstance(model_raw, dict) else None,
            model_name=model_raw.get("model_name") if isinstance(model_raw, dict) else None,
            api_key=model_raw.get("api_key") if isinstance(model_raw, dict) else None,
            last_tested_at=model_raw.get("last_tested_at") if isinstance(model_raw, dict) else None,
            last_test_result=model_raw.get("last_test_result") if isinstance(model_raw, dict) else None,
            last_test_message=model_raw.get("last_test_message") if isinstance(model_raw, dict) else None,
        )

        return cls(evolus=evolus, model=model)


def load_settings(path: Path | None = None) -> SettingsStoreData:
    """
    Read fresh settings from disk.
    A missing or corrupt file yields empty defaults and is not rewritten.
    """
    target_path = path or get_settings_store_path()
    if not target_path.exists():
        return SettingsStoreData()

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return SettingsStoreData.from_dict(raw)
    except Exception:
        # Corrupt or unreadable file: yield empty defaults; do not overwrite or crash
        return SettingsStoreData()


def save_settings(data: SettingsStoreData, path: Path | None = None) -> None:
    """
    Atomically save settings data to disk using a temporary file and os.replace.
    """
    target_path = path or get_settings_store_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_file_path = tempfile.mkstemp(
        prefix="settings_",
        suffix=".tmp",
        dir=str(target_path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data.to_dict(), f, indent=2)
        os.replace(temp_file_path, str(target_path))
    except Exception:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        raise


def update_evolus_settings(update: EvolusConfigUpdate, path: Path | None = None) -> SettingsStoreData:
    """
    Apply Evolus update with merge semantics:
    - null / omitted = keep current
    - "" = clear (set to None)
    - non-empty = set trimmed
    """
    store = load_settings(path)
    if update.api_key is not None:
        trimmed = update.api_key.strip()
        store.evolus.api_key = trimmed if trimmed != "" else None
    save_settings(store, path)
    return store


def update_model_settings(update: ModelConfigUpdate, path: Path | None = None) -> SettingsStoreData:
    """
    Apply Model endpoint update with merge semantics:
    - null / omitted = keep current
    - "" = clear (set to None)
    - non-empty = set trimmed
    """
    store = load_settings(path)
    if update.base_url is not None:
        trimmed = update.base_url.strip()
        store.model.base_url = trimmed if trimmed != "" else None
    if update.model_name is not None:
        trimmed = update.model_name.strip()
        store.model.model_name = trimmed if trimmed != "" else None
    if update.api_key is not None:
        trimmed = update.api_key.strip()
        store.model.api_key = trimmed if trimmed != "" else None
    save_settings(store, path)
    return store


def record_evolus_test_result(
    ok: bool,
    message: str,
    tested_at: datetime,
    path: Path | None = None,
) -> SettingsStoreData:
    """Record test execution result for Evolus integration in disk store."""
    store = load_settings(path)
    store.evolus.last_tested_at = tested_at.isoformat()
    store.evolus.last_test_result = "ok" if ok else "failed"
    store.evolus.last_test_message = message
    save_settings(store, path)
    return store


def record_model_test_result(
    ok: bool,
    message: str,
    tested_at: datetime,
    path: Path | None = None,
) -> SettingsStoreData:
    """Record test execution result for Model integration in disk store."""
    store = load_settings(path)
    store.model.last_tested_at = tested_at.isoformat()
    store.model.last_test_result = "ok" if ok else "failed"
    store.model.last_test_message = message
    save_settings(store, path)
    return store


def parse_datetime_optional(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def get_evolus_view(store: SettingsStoreData) -> EvolusSettingsView:
    is_configured = bool(store.evolus.api_key and store.evolus.api_key.strip())
    return EvolusSettingsView(
        status="configured" if is_configured else "not_configured",
        masked_api_key=mask_secret(store.evolus.api_key),
        last_tested_at=parse_datetime_optional(store.evolus.last_tested_at),
        last_test_result=store.evolus.last_test_result,  # type: ignore
        last_test_message=store.evolus.last_test_message,
    )


def get_model_view(store: SettingsStoreData) -> ModelSettingsView:
    is_configured = bool(store.model.base_url and store.model.base_url.strip())
    return ModelSettingsView(
        status="configured" if is_configured else "not_configured",
        base_url=store.model.base_url,
        model_name=store.model.model_name,
        masked_api_key=mask_secret(store.model.api_key),
        last_tested_at=parse_datetime_optional(store.model.last_tested_at),
        last_test_result=store.model.last_test_result,  # type: ignore
        last_test_message=store.model.last_test_message,
    )


def get_google_view(
    connected: bool,
    last_tested_at: datetime | None = None,
    last_test_result: Literal["ok", "failed"] | None = None,
    last_test_message: str | None = None,
) -> GoogleSettingsView:
    return GoogleSettingsView(
        status="connected" if connected else "not_configured",
        connected=connected,
        last_tested_at=last_tested_at,
        last_test_result=last_test_result,
        last_test_message=last_test_message,
    )


def get_integrations_section(
    store: SettingsStoreData,
    google_connected: bool,
    google_tested_at: datetime | None = None,
    google_test_result: Literal["ok", "failed"] | None = None,
    google_test_message: str | None = None,
) -> IntegrationsSection:
    return IntegrationsSection(
        evolus=get_evolus_view(store),
        model=get_model_view(store),
        google=get_google_view(
            connected=google_connected,
            last_tested_at=google_tested_at,
            last_test_result=google_test_result,
            last_test_message=google_test_message,
        ),
    )

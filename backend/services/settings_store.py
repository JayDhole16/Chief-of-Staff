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
from typing import Any, Literal, Union

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
class EvolusConfig:
    api_key: str | None = None
    last_tested_at: str | None = None
    last_test_result: str | None = None
    last_test_message: str | None = None


# Backward-compatible alias
EvolusStoreRecord = EvolusConfig


@dataclass
class ModelConfig:
    api_key: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    last_tested_at: str | None = None
    last_test_result: str | None = None
    last_test_message: str | None = None


# Backward-compatible alias
ModelStoreRecord = ModelConfig


class SettingsStore:
    """File-backed settings store reading fresh on every call and writing atomically."""

    def __init__(self, path: Path | str | None = None):
        if path is None:
            self.path = get_settings_store_path()
        elif isinstance(path, str):
            self.path = Path(path)
        else:
            self.path = path

    def _read_data(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_data(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_file_path = tempfile.mkstemp(
            prefix="settings_",
            suffix=".tmp",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file_path, str(self.path))
        except Exception:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass
            raise

    def load_evolus(self) -> EvolusConfig:
        data = self._read_data()
        ev = data.get("evolus")
        if not isinstance(ev, dict):
            return EvolusConfig()
        return EvolusConfig(
            api_key=ev.get("api_key"),
            last_tested_at=ev.get("last_tested_at"),
            last_test_result=ev.get("last_test_result"),
            last_test_message=ev.get("last_test_message"),
        )

    def load_model(self) -> ModelConfig:
        data = self._read_data()
        mo = data.get("model")
        if not isinstance(mo, dict):
            return ModelConfig()
        return ModelConfig(
            api_key=mo.get("api_key"),
            base_url=mo.get("base_url"),
            model_name=mo.get("model_name"),
            last_tested_at=mo.get("last_tested_at"),
            last_test_result=mo.get("last_test_result"),
            last_test_message=mo.get("last_test_message"),
        )

    def save_evolus(self, cfg: EvolusConfig) -> None:
        data = self._read_data()
        data["evolus"] = {
            "api_key": cfg.api_key,
            "last_tested_at": cfg.last_tested_at,
            "last_test_result": cfg.last_test_result,
            "last_test_message": cfg.last_test_message,
        }
        if "model" not in data or not isinstance(data["model"], dict):
            mo = self.load_model()
            data["model"] = {
                "base_url": mo.base_url,
                "model_name": mo.model_name,
                "api_key": mo.api_key,
                "last_tested_at": mo.last_tested_at,
                "last_test_result": mo.last_test_result,
                "last_test_message": mo.last_test_message,
            }
        self._write_data(data)

    def save_model(self, cfg: ModelConfig) -> None:
        data = self._read_data()
        data["model"] = {
            "base_url": cfg.base_url,
            "model_name": cfg.model_name,
            "api_key": cfg.api_key,
            "last_tested_at": cfg.last_tested_at,
            "last_test_result": cfg.last_test_result,
            "last_test_message": cfg.last_test_message,
        }
        if "evolus" not in data or not isinstance(data["evolus"], dict):
            ev = self.load_evolus()
            data["evolus"] = {
                "api_key": ev.api_key,
                "last_tested_at": ev.last_tested_at,
                "last_test_result": ev.last_test_result,
                "last_test_message": ev.last_test_message,
            }
        self._write_data(data)


@dataclass
class SettingsStoreData:
    evolus: EvolusConfig = field(default_factory=EvolusConfig)
    model: ModelConfig = field(default_factory=ModelConfig)

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

        evolus = EvolusConfig(
            api_key=evolus_raw.get("api_key") if isinstance(evolus_raw, dict) else None,
            last_tested_at=evolus_raw.get("last_tested_at") if isinstance(evolus_raw, dict) else None,
            last_test_result=evolus_raw.get("last_test_result") if isinstance(evolus_raw, dict) else None,
            last_test_message=evolus_raw.get("last_test_message") if isinstance(evolus_raw, dict) else None,
        )

        model = ModelConfig(
            api_key=model_raw.get("api_key") if isinstance(model_raw, dict) else None,
            base_url=model_raw.get("base_url") if isinstance(model_raw, dict) else None,
            model_name=model_raw.get("model_name") if isinstance(model_raw, dict) else None,
            last_tested_at=model_raw.get("last_tested_at") if isinstance(model_raw, dict) else None,
            last_test_result=model_raw.get("last_test_result") if isinstance(model_raw, dict) else None,
            last_test_message=model_raw.get("last_test_message") if isinstance(model_raw, dict) else None,
        )

        return cls(evolus=evolus, model=model)


def load_settings(path: Path | None = None) -> SettingsStoreData:
    store = SettingsStore(path)
    return SettingsStoreData(
        evolus=store.load_evolus(),
        model=store.load_model(),
    )


def save_settings(data: SettingsStoreData, path: Path | None = None) -> None:
    store = SettingsStore(path)
    combined = data.to_dict()
    store._write_data(combined)


def update_evolus_settings(update: EvolusConfigUpdate, path: Path | None = None) -> EvolusConfig:
    store = SettingsStore(path)
    cfg = store.load_evolus()
    if update.api_key is not None:
        trimmed = update.api_key.strip()
        cfg.api_key = trimmed if trimmed != "" else None
    store.save_evolus(cfg)
    return cfg


def update_model_settings(update: ModelConfigUpdate, path: Path | None = None) -> ModelConfig:
    store = SettingsStore(path)
    cfg = store.load_model()
    if update.base_url is not None:
        trimmed = update.base_url.strip()
        cfg.base_url = trimmed if trimmed != "" else None
    if update.model_name is not None:
        trimmed = update.model_name.strip()
        cfg.model_name = trimmed if trimmed != "" else None
    if update.api_key is not None:
        trimmed = update.api_key.strip()
        cfg.api_key = trimmed if trimmed != "" else None
    store.save_model(cfg)
    return cfg


def record_evolus_test_result(
    ok: bool,
    message: str,
    tested_at: datetime,
    path: Path | None = None,
) -> EvolusConfig:
    store = SettingsStore(path)
    cfg = store.load_evolus()
    cfg.last_tested_at = tested_at.isoformat()
    cfg.last_test_result = "ok" if ok else "failed"
    cfg.last_test_message = message
    store.save_evolus(cfg)
    return cfg


def record_model_test_result(
    ok: bool,
    message: str,
    tested_at: datetime,
    path: Path | None = None,
) -> ModelConfig:
    store = SettingsStore(path)
    cfg = store.load_model()
    cfg.last_tested_at = tested_at.isoformat()
    cfg.last_test_result = "ok" if ok else "failed"
    cfg.last_test_message = message
    store.save_model(cfg)
    return cfg


def parse_datetime_optional(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def get_evolus_view(cfg_or_store: Union[EvolusConfig, SettingsStoreData, SettingsStore]) -> EvolusSettingsView:
    if isinstance(cfg_or_store, SettingsStore):
        cfg = cfg_or_store.load_evolus()
    elif isinstance(cfg_or_store, SettingsStoreData):
        cfg = cfg_or_store.evolus
    else:
        cfg = cfg_or_store

    is_configured = bool(cfg.api_key and cfg.api_key.strip())
    return EvolusSettingsView(
        status="configured" if is_configured else "not_configured",
        masked_api_key=mask_secret(cfg.api_key),
        last_tested_at=parse_datetime_optional(cfg.last_tested_at),
        last_test_result=cfg.last_test_result,  # type: ignore
        last_test_message=cfg.last_test_message,
    )


def get_model_view(cfg_or_store: Union[ModelConfig, SettingsStoreData, SettingsStore]) -> ModelSettingsView:
    if isinstance(cfg_or_store, SettingsStore):
        cfg = cfg_or_store.load_model()
    elif isinstance(cfg_or_store, SettingsStoreData):
        cfg = cfg_or_store.model
    else:
        cfg = cfg_or_store

    is_configured = bool(cfg.base_url and cfg.base_url.strip())
    return ModelSettingsView(
        status="configured" if is_configured else "not_configured",
        base_url=cfg.base_url,
        model_name=cfg.model_name,
        masked_api_key=mask_secret(cfg.api_key),
        last_tested_at=parse_datetime_optional(cfg.last_tested_at),
        last_test_result=cfg.last_test_result,  # type: ignore
        last_test_message=cfg.last_test_message,
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
    store: Union[SettingsStore, SettingsStoreData],
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


__all__ = [
    "EvolusConfig",
    "EvolusStoreRecord",
    "ModelConfig",
    "ModelStoreRecord",
    "SettingsStore",
    "SettingsStoreData",
    "get_evolus_view",
    "get_google_view",
    "get_integrations_section",
    "get_model_view",
    "get_settings_store_path",
    "load_settings",
    "mask_secret",
    "record_evolus_test_result",
    "record_model_test_result",
    "save_settings",
    "update_evolus_settings",
    "update_model_settings",
]

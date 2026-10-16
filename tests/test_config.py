import os
import subprocess
import sys

import pytest

from backend.config import validate_api_environment


def test_api_rejects_worker_private_key():
    with pytest.raises(RuntimeError, match="worker-only"):
        validate_api_environment({"TOKEN_VAULT_PRIVATE_KEY": "must-not-be-in-api"})


def test_api_accepts_environment_without_worker_private_key():
    validate_api_environment({"DATABASE_URL": "postgresql://localhost/example"})


def test_api_entrypoint_refuses_worker_private_key():
    environment = os.environ.copy()
    environment["TOKEN_VAULT_PRIVATE_KEY"] = "worker-only"
    result = subprocess.run(
        [sys.executable, "-c", "import backend.main"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )
    assert result.returncode != 0
    assert "TOKEN_VAULT_PRIVATE_KEY is worker-only" in result.stderr

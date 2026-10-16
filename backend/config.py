"""Runtime configuration guards shared by application entry points."""

import os
from collections.abc import Mapping


def validate_api_environment(environ: Mapping[str, str] | None = None) -> None:
    """Keep worker-only private key material out of the API process."""
    values = os.environ if environ is None else environ
    if values.get("TOKEN_VAULT_PRIVATE_KEY"):
        raise RuntimeError(
            "TOKEN_VAULT_PRIVATE_KEY is worker-only and must not be set in the API process"
        )

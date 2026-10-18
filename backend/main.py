"""
Main server entry point for AI Chief of Staff FastAPI application.
Run locally with: uvicorn backend.main:app --port 8000 --reload

Settings such as DATABASE_URL are read from the environment, or from a ``.env``
file at the repository root (variables already set in the environment win).
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from backend.config import validate_api_environment  # noqa: E402

validate_api_environment()

from backend.api.app import app  # noqa: E402

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

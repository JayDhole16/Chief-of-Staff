"""
Main server entry point for AI Chief of Staff FastAPI application.
Run locally with: uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
"""

from backend.config import validate_api_environment

validate_api_environment()

from backend.api.app import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8080, reload=True)

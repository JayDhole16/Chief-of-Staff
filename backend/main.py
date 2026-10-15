"""
Main server entry point for AI Chief of Staff FastAPI application.
Run locally with: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""

from backend.api.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

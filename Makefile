.PHONY: setup check test lint format clean up down smoke-app help bench dev-api dev-web

help:
	@echo "Chief-of-Staff Build Commands"
	@echo ""
	@echo "  make setup        Install dependencies"
	@echo "  make check        Run lint and tests"
	@echo "  make test         Run pytest"
	@echo "  make bench        Run benchmark harness (RUNNER=fake)"
	@echo "  make dev-api      Run the API on http://localhost:8000 with reload"
	@echo "  make dev-web      Run the web app on http://localhost:5173"
	@echo "  make lint         Run ruff and mypy"
	@echo "  make format       Run black formatter"
	@echo "  make clean        Remove cache and build artifacts"
	@echo "  make up           Start the provisional Docker dev stack"
	@echo "  make down         Stop the Docker dev stack"
	@echo "  make smoke-app    Probe the running local Compose services"

setup:
	python -m pip install -e ".[dev]"

test:
	python -m pytest tests/ -v --tb=short

bench:
	python -m bench.harness.runner --runner $${RUNNER:-fake}

dev-api:
	python -m uvicorn backend.main:app --port 8000 --reload

dev-web:
	cd frontend && npm run dev

check: lint test

lint:
	ruff check backend tests
	mypy backend --ignore-missing-imports || true

format:
	black backend tests
	ruff check --fix backend tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov dist build *.egg-info 2>/dev/null || true

up:
	docker compose up --build

down:
	docker compose down

smoke-app:
	python scripts/smoke_app.py

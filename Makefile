.PHONY: setup check test lint format clean up down smoke-app help

help:
	@echo "Chief-of-Staff Build Commands"
	@echo ""
	@echo "  make setup        Install dependencies"
	@echo "  make check        Run all checks (test, lint, format)"
	@echo "  make test         Run pytest"
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

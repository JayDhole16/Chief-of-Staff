<<<<<<< HEAD
.PHONY: setup check test lint format clean up down help bench
=======
.PHONY: setup check test lint format clean help
>>>>>>> d391f671df8a2962e190545fd3b50665f195c60a

help:
	@echo "Chief-of-Staff Build Commands"
	@echo ""
	@echo "  make setup        Install dependencies"
	@echo "  make check        Run all checks (test, lint, format)"
	@echo "  make test         Run pytest"
<<<<<<< HEAD
	@echo "  make bench        Run benchmark harness (RUNNER=fake)"
	@echo "  make lint         Run ruff and mypy"
	@echo "  make format       Run black formatter"
	@echo "  make clean        Remove cache and build artifacts"
	@echo "  make up           Start the provisional Docker dev stack"
	@echo "  make down         Stop the Docker dev stack"

setup:
	python -m pip install -e ".[dev]"
=======
	@echo "  make lint         Run ruff and mypy"
	@echo "  make format       Run black formatter"
	@echo "  make clean        Remove cache and build artifacts"

setup:
	pip install -e ".[dev]"
>>>>>>> d391f671df8a2962e190545fd3b50665f195c60a

test:
	python -m pytest tests/ -v --tb=short

<<<<<<< HEAD
bench:
	python -m bench.harness.runner --runner $${RUNNER:-fake}

check: lint test

=======
check: lint test

>>>>>>> d391f671df8a2962e190545fd3b50665f195c60a
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
<<<<<<< HEAD

up:
	docker compose up --build

down:
	docker compose down
=======
>>>>>>> d391f671df8a2962e190545fd3b50665f195c60a

.PHONY: install test test-unit test-integration test-e2e seed-db harness run lint fmt

install:
	uv sync --group dev

test:
	uv run pytest tests/ -v -m "not e2e"

test-unit:
	uv run pytest tests/unittests/ -v

test-integration:
	uv run pytest tests/integration/ -v

test-e2e:
	uv run pytest tests/e2e/ -v -m e2e

seed-db:
	uv run python tests/harness/seeder/synthetic_db.py --db-path data.db --reset

harness:
	uv run python tests/harness/main.py

run:
	uv run python main.py

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

fmt:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

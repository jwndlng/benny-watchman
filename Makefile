.PHONY: install test test-unit test-integration test-e2e run lint fmt

install:
	uv sync --group dev

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/api/ tests/integration/ -v

test-e2e:
	uv run pytest tests/e2e/ -v -m e2e

run:
	uv run python main.py

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

fmt:
	uv run ruff format src/ tests/

.PHONY: install test test-unit test-integration run lint fmt

install:
	uv sync --group dev

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/api/ tests/integration/ -v

run:
	uv run python main.py

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

fmt:
	uv run ruff format src/ tests/

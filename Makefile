.PHONY: install test run lint fmt

install:
	uv sync

test:
	uv run pytest tests/ -v

run:
	uv run python main.py

lint:
	uv run ruff check src/ tests/

fmt:
	uv run ruff format src/ tests/

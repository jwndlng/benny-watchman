FROM python:3.14-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (layer cached when lockfiles are unchanged)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project
COPY . .
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "python", "main.py"]

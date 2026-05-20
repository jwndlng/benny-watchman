## Why

Running benny-watchman locally requires manually setting environment variables and understanding the Python toolchain. A Docker Compose setup provides a one-command local dev environment: set your keys in `.env`, run `docker-compose up`, and start curling the API.

## What Changes

- `Dockerfile` added — production-style Python 3.14 image built with uv, no hot-reload or dev tooling
- `docker-compose.yml` added — single `app` service, port 5000 exposed, `.env` file loaded automatically
- `.env.example` added — documents every environment variable with descriptions and example values
- `Makefile` updated — `dev-up` and `dev-down` targets added as thin wrappers around docker-compose
- `investigations.db` is ephemeral by default — no volume mount; each `docker-compose up` starts with clean state

## Capabilities

### New Capabilities
- `local-dev-compose`: Single-command local dev environment via Docker Compose — build, run, curl

### Modified Capabilities
- None

## Impact

- New files: `Dockerfile`, `docker-compose.yml`, `.env.example`
- Modified files: `Makefile`
- No code changes — purely infrastructure
- External services (LLM, Okta, Elasticsearch) connect via env vars; no local replicas needed

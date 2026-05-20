## Context

benny-watchman currently has no Docker setup despite Docker being listed in the tech stack. Running the app locally requires the Python toolchain (uv, Python 3.14), manual env var configuration, and knowledge of which commands to run. The goal is a single-command local dev loop: configure `.env`, run `docker-compose up`, curl the API.

External services (LLM providers, Okta, Elasticsearch) are cloud-hosted and accessed via env vars — no local replicas are needed or wanted.

## Goals / Non-Goals

**Goals:**
- `docker-compose up` starts a functional benny-watchman API on port 5000
- `.env.example` documents every env var required to operate
- `make dev-up` / `make dev-down` provide convenience entry points
- Investigations DB is ephemeral — clean state on each `docker-compose up`

**Non-Goals:**
- Hot-reload / volume-mounted source code — rebuild to pick up changes
- Local replicas of external services (Elasticsearch, Okta, LLMs)
- Production-grade image hardening (multi-stage build, non-root user, etc.)
- Seeding test data — user connects to a real data backend via env vars

## Decisions

### 1. Single-stage Dockerfile using uv's Docker integration

uv's official Docker guidance recommends `uv sync --frozen` to install dependencies from `uv.lock`, ensuring reproducible builds. The image uses `python:3.14-slim` as the base; uv is installed via the official installer script or `pip install uv`.

`CMD ["uv", "run", "python", "main.py"]` keeps the invocation consistent with local development (`make run`).

Alternative considered: multi-stage build to keep image smaller. Rejected — adds complexity with negligible benefit for a local dev image.

### 2. `env_file: .env` in docker-compose, not baked-in environment

All configuration is injected via `.env` at runtime. The compose file contains no hardcoded values. This means the same image works for any configuration — different LLM providers, different Okta tenants, different ES clusters — just by swapping `.env`.

`.env` is gitignored. `.env.example` is committed and serves as the authoritative reference.

### 3. Ephemeral investigations.db — no volume mount

The investigations SQLite file is written inside the container at the path set by `PERSISTENCE_DB_PATH`. Without a volume mount it is lost on container stop. For local dev this is acceptable: investigations are cheap to re-run and clean state avoids stale data confusing development.

If persistence across restarts becomes useful later, a single volume line in docker-compose is the entire change.

### 4. Port 5000 hardcoded in docker-compose

`main.py` binds to port 5000. The compose file maps `5000:5000`. No env var override for the port — the added complexity is not justified for a local dev setup.

## Risks / Trade-offs

**uv not cached between builds** — each `docker-compose build` re-downloads dependencies if the `uv.lock` or `pyproject.toml` changed. → Mitigated by Docker layer caching: copying `pyproject.toml` and `uv.lock` before `COPY . .` ensures the dep layer is only invalidated when those files change.

**Ephemeral DB means no investigation history** — investigations disappear on container stop. → Acceptable for the stated use case; easily changed with a volume mount.

**No `.dockerignore`** — without one, `COPY . .` includes `.venv`, `__pycache__`, `.git`, etc., making the build context large and slow. → A `.dockerignore` should be included alongside the Dockerfile.

## Open Questions

- Should `DATA_BACKEND_DB_PATH` default to `data.db` in `.env.example` (SQLite, no data) or be left blank to force the user to choose? Leaving it blank with a comment is clearest.

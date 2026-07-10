## 1. Dockerfile and .dockerignore

- [x] 1.1 Create `Dockerfile` using `python:3.14-slim`, install uv, copy `pyproject.toml` + `uv.lock` first, run `uv sync --frozen`, then `COPY . .`, set `CMD ["uv", "run", "python", "main.py"]`
- [x] 1.2 Create `.dockerignore` excluding `.venv`, `__pycache__`, `.git`, `*.db`, `.env`, `openspec/`, `tests/`

## 2. docker-compose.yml

- [x] 2.1 Create `docker-compose.yml` with a single `app` service: `build: .`, `ports: ["5000:5000"]`, `env_file: .env`

## 3. .env.example

- [x] 3.1 Create `.env.example` with all env vars: `AGENT_MODEL`, `AGENT_MODEL_API_KEY`, `AGENT_MAX_REQUESTS`, `DATA_BACKEND_ENGINE`, `DATA_BACKEND_DB_PATH`, `DATA_AGENT_NAME`, `PERSISTENCE_DB_PATH`, `OKTA_DOMAIN`, `OKTA_CLIENT_ID`, `OKTA_PRIVATE_KEY`, `LOGFIRE_TOKEN` — each with a description comment and placeholder value
- [x] 3.2 Verify `.env` is listed in `.gitignore` (add if missing)

## 4. Makefile

- [x] 4.1 Add `dev-up` target: `docker-compose up --build`
- [x] 4.2 Add `dev-down` target: `docker-compose down`
- [x] 4.3 Add `dev-up` and `dev-down` to the `.PHONY` declaration

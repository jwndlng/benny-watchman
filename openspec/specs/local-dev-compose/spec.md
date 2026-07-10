# local-dev-compose

## Purpose

Defines the local development environment setup using Docker Compose. Covers the Dockerfile, docker-compose.yml, environment variable documentation, and Makefile convenience targets so a developer can get benny-watchman running locally with a single command.

---

## Requirements

### Requirement: docker-compose up starts the API
The project SHALL include a `docker-compose.yml` that starts the benny-watchman FastAPI application on port 5000 with a single `docker-compose up` command. The service SHALL load all configuration from a `.env` file in the project root.

#### Scenario: App starts with valid .env
- **WHEN** a `.env` file is present with valid LLM credentials and `docker-compose up` is run
- **THEN** the FastAPI application is accessible at `http://localhost:5000` and responds to health or API requests

#### Scenario: App fails clearly with missing required env vars
- **WHEN** required env vars (e.g., `AGENT_MODEL`) are absent from `.env`
- **THEN** the container exits with a non-zero code and a readable error message

---

### Requirement: Dockerfile builds a runnable image
The project SHALL include a `Dockerfile` that builds a self-contained image using Python 3.14 and uv. The image SHALL install dependencies from `uv.lock` using `uv sync --frozen` to ensure reproducible builds.

#### Scenario: Docker layer caching for dependencies
- **WHEN** only source files change (not `pyproject.toml` or `uv.lock`)
- **THEN** `docker-compose build` reuses the cached dependency layer and completes faster than a full rebuild

#### Scenario: Build context excludes dev artifacts
- **WHEN** the image is built
- **THEN** `.venv`, `__pycache__`, `.git`, and local SQLite files are excluded from the build context via `.dockerignore`

---

### Requirement: .env.example documents all configuration
The project SHALL include a `.env.example` file committed to version control. It SHALL document every environment variable consumed by the application with a description and example or placeholder value. It SHALL be the authoritative reference for configuring a local environment.

#### Scenario: Developer can configure from .env.example alone
- **WHEN** a developer copies `.env.example` to `.env` and fills in their credentials
- **THEN** they have all the information needed to run the application without reading source code

#### Scenario: .env is gitignored
- **WHEN** a developer creates `.env` from `.env.example`
- **THEN** `.env` is not committed to the repository (listed in `.gitignore`)

---

### Requirement: Makefile provides dev-up and dev-down targets
The `Makefile` SHALL include `dev-up` and `dev-down` targets as thin wrappers around `docker-compose up --build` and `docker-compose down` respectively.

#### Scenario: make dev-up builds and starts the container
- **WHEN** `make dev-up` is run
- **THEN** the Docker image is built (or rebuilt if files changed) and the container starts in the foreground

#### Scenario: make dev-down stops and removes containers
- **WHEN** `make dev-down` is run
- **THEN** running containers and associated networks are stopped and removed

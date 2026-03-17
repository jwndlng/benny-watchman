"""Application configuration loaded from environment variables."""

import os


class _PersistenceConfig:
    engine: str = os.environ.get("PERSISTENCE_ENGINE", "sqlite")
    db_path: str = os.environ.get("PERSISTENCE_DB_PATH", "investigations.db")


class _RunbooksConfig:
    path: str = os.environ.get("RUNBOOKS_PATH", "runbooks")


class _AgentConfig:
    model: str = os.environ.get(
        "AGENT_MODEL", "google-gla:gemini-3.1-flash-lite-preview"
    )
    api_key: str | None = os.environ.get("AGENT_MODEL_API_KEY")
    max_requests: int = int(os.environ.get("AGENT_MAX_REQUESTS", "15"))
    max_data_requests: int = int(os.environ.get("AGENT_MAX_DATA_REQUESTS", "10"))

    def set_model_api_key(self, model: str | None = None) -> None:
        """PydanticAI delegates to vendor SDKs (Anthropic, Google, OpenAI) which each
        read their own provider-specific env var. Map AGENT_MODEL_API_KEY to the right one.
        Pass model explicitly when using a runtime override (e.g. harness --model flag)."""
        target = model or self.model
        if not self.api_key or ":" not in target:
            return
        match target.split(":")[0]:
            case "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = self.api_key
            case "google-gla":
                os.environ["GEMINI_API_KEY"] = self.api_key
            case "openai":
                os.environ["OPENAI_API_KEY"] = self.api_key


class _DataConfig:
    engine: str = os.environ.get("DATA_BACKEND_ENGINE", "sqlite")
    db_path: str = os.environ.get("DATA_BACKEND_DB_PATH", "data.db")


class Config:
    persistence = _PersistenceConfig()
    runbooks = _RunbooksConfig()
    agent = _AgentConfig()
    data = _DataConfig()


config = Config()
config.agent.set_model_api_key()

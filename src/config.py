"""Application configuration — TOML-canonical via pydantic-settings, secrets from env.

Precedence: env > TOML (`config.toml`) > defaults. All non-secret settings live in
`config.toml` (copied from `config.toml.example`); secrets are supplied ONLY via
environment variables under their canonical names (the `validation_alias` on each
secret field). A data/integration section that is absent is disabled; a section that
is present but missing its required secret fails validation at startup (fail fast).
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_CONFIG_FILE = os.environ.get("CONFIG_FILE", "config.toml")

# Non-secret model defaults keep the model provider mapping working for local dev.
_PROVIDER_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google-gla": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class AgentSettings(BaseModel):
    """LLM agent settings."""

    model: str = Field(
        default="google-gla:gemini-3.1-flash-lite-preview", description="LLM model id"
    )
    api_key: str | None = Field(
        default=None,
        description="Model API key (secret; injected from AGENT_MODEL_API_KEY)",
    )
    max_requests: int = Field(default=15, description="Hard per-agent request cap")
    max_data_requests: int = Field(
        default=10, description="Per data-agent request cap"
    )


class PersistenceSettings(BaseModel):
    """Investigation storage settings."""

    engine: str = Field(default="sqlite", description="Persistence engine")
    db_path: str = Field(default="investigations.db", description="Investigations DB")


class SqliteDataSettings(BaseModel):
    """SQLite log data source (present ⇒ enabled)."""

    name: str = Field(default="security_logs", description="Data agent name")
    db_path: str = Field(default="data.db", description="SQLite log DB path")


class ElasticDataSettings(BaseModel):
    """Elasticsearch log data source (present ⇒ enabled)."""

    name: str = Field(default="elasticsearch", description="Data agent name")
    host: str = Field(description="Elasticsearch host URL")
    index_pattern: str | None = Field(default=None, description="Index pattern")
    api_key: str = Field(
        description="ES API key (secret; injected from ELASTIC_API_KEY)"
    )


class DataSettings(BaseModel):
    """Log data sources; a source runs iff its section is present."""

    sqlite: SqliteDataSettings | None = None
    elastic: ElasticDataSettings | None = None


class VulnSettings(BaseModel):
    """Vulnerability Management asset-inventory data source."""

    db_path: str = Field(default="vuln.db", description="Asset inventory DB path")
    name: str = Field(default="asset_inventory", description="Asset data agent name")


class KibanaSettings(BaseModel):
    """Kibana Security triage platform (present ⇒ Elastic platform, else in-memory)."""

    url: str = Field(description="Kibana base URL; may include /s/<space-id>")
    case_owner: str = Field(default="securitySolution", description="Cases owner")
    api_key: str = Field(
        description="Kibana API key (secret; injected from KIBANA_TRIAGE_API_KEY)"
    )


class OktaSettings(BaseModel):
    """Okta IDP integration (JWT private-key auth)."""

    domain: str = Field(description="Okta org URL")
    client_id: str = Field(
        description="OAuth client id (secret; injected from OKTA_CLIENT_ID)"
    )
    private_key_b64: str = Field(
        description="Base64 private key (secret; injected from OKTA_PRIVATE_KEY)"
    )


class Settings(BaseSettings):
    """Top-level configuration: TOML + env (env wins), validated at construction."""

    model_config = SettingsConfigDict(
        toml_file=_CONFIG_FILE,
        env_nested_delimiter="__",
        extra="ignore",
    )

    agent: AgentSettings = AgentSettings()
    persistence: PersistenceSettings = PersistenceSettings()
    data: DataSettings = DataSettings()
    vuln: VulnSettings = VulnSettings()
    kibana: KibanaSettings | None = None
    okta: OktaSettings | None = None
    mcp_bearer_token: str | None = Field(
        default=None, description="MCP bearer token (secret; from MCP_BEARER_TOKEN)"
    )

    @model_validator(mode="before")
    @classmethod
    def _inject_secrets(cls, data: object) -> object:
        """Inject env-only secrets into their sections by canonical name.

        Secrets never live in TOML. Optional sections receive their secret only when
        the section is present, so a configured-but-secretless section fails fast.
        """
        if not isinstance(data, dict):
            return data

        def _env(name: str) -> str | None:
            return os.environ.get(name) or None

        agent_key = _env("AGENT_MODEL_API_KEY")
        if agent_key is not None:
            agent = data.get("agent")
            if not isinstance(agent, dict):
                agent = {}
                data["agent"] = agent
            agent["api_key"] = agent_key

        sources = data.get("data")
        if isinstance(sources, dict) and isinstance(sources.get("elastic"), dict):
            v = _env("ELASTIC_API_KEY")
            if v is not None:
                sources["elastic"]["api_key"] = v

        if isinstance(data.get("kibana"), dict):
            v = _env("KIBANA_TRIAGE_API_KEY")
            if v is not None:
                data["kibana"]["api_key"] = v

        if isinstance(data.get("okta"), dict):
            cid, pk = _env("OKTA_CLIENT_ID"), _env("OKTA_PRIVATE_KEY")
            if cid is not None:
                data["okta"]["client_id"] = cid
            if pk is not None:
                data["okta"]["private_key_b64"] = pk

        return data

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Precedence: init > env > dotenv > TOML > defaults."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    def set_model_api_key(self, model: str | None = None) -> None:
        """Map the agent API key to the provider-specific env var PydanticAI expects.
        Pass model explicitly for a runtime override (e.g. harness --model)."""
        target = model or self.agent.model
        if not self.agent.api_key or ":" not in target:
            return
        env_var = _PROVIDER_ENV.get(target.split(":")[0])
        if env_var:
            os.environ[env_var] = self.agent.api_key


config = Settings()
config.set_model_api_key()

"""Application configuration loaded from environment variables."""

import os


class _PersistenceConfig:
    """Investigation storage settings."""

    engine: str = os.environ.get("PERSISTENCE_ENGINE", "sqlite")
    db_path: str = os.environ.get("PERSISTENCE_DB_PATH", "investigations.db")


class _RunbooksConfig:
    """Runbook loader settings."""

    path: str = os.environ.get("RUNBOOKS_PATH", "src/modules/siem/runbooks")


class _AgentConfig:
    """LLM agent settings."""

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
    """Security log backend settings."""

    engine: str = os.environ.get("DATA_BACKEND_ENGINE", "sqlite")
    db_path: str = os.environ.get("DATA_BACKEND_DB_PATH", "data.db")
    name: str = os.environ.get("DATA_AGENT_NAME", "security_logs")


class _VulnConfig:
    """Vulnerability Management module settings."""

    runbooks_path: str = os.environ.get(
        "VULN_RUNBOOKS_PATH", "src/modules/vuln_mgmt/runbooks"
    )
    db_path: str = os.environ.get("VULN_DB_PATH", "vuln.db")
    name: str = os.environ.get("VULN_DATA_AGENT_NAME", "asset_inventory")


class _OktaConfig:
    """Okta IDP integration settings — JWT private key authentication."""

    def __init__(self, domain: str, client_id: str, private_key_b64: str) -> None:
        self.domain = domain
        self.client_id = client_id
        self.private_key_b64 = private_key_b64


class _ElasticConfig:
    """Elasticsearch data backend settings."""

    def __init__(self, host: str, api_key: str, index_pattern: str | None) -> None:
        self.host = host
        self.api_key = api_key
        self.index_pattern = index_pattern


def _load_elastic_config() -> "_ElasticConfig | None":
    host = os.environ.get("ELASTIC_HOST", "")
    api_key = os.environ.get("ELASTIC_API_KEY", "")
    if not host or not api_key:
        return None
    index_pattern = os.environ.get("ELASTIC_INDEX_PATTERN") or None
    return _ElasticConfig(host=host, api_key=api_key, index_pattern=index_pattern)


class _KibanaConfig:
    """Kibana Security app settings — the TriagePlatform (write-back) surface."""

    def __init__(self, url: str, api_key: str, case_owner: str) -> None:
        self.url = url
        self.api_key = api_key
        self.case_owner = case_owner


def _load_kibana_config() -> "_KibanaConfig | None":
    url = os.environ.get("KIBANA_URL", "")
    api_key = os.environ.get("KIBANA_API_KEY", "")
    if not url or not api_key:
        return None
    case_owner = os.environ.get("KIBANA_CASE_OWNER", "securitySolution")
    return _KibanaConfig(url=url, api_key=api_key, case_owner=case_owner)


def _load_okta_config() -> "_OktaConfig | None":
    domain = os.environ.get("OKTA_DOMAIN", "")
    client_id = os.environ.get("OKTA_CLIENT_ID", "")
    private_key_b64 = os.environ.get("OKTA_PRIVATE_KEY", "")
    if not domain or not client_id or not private_key_b64:
        return None
    return _OktaConfig(
        domain=domain, client_id=client_id, private_key_b64=private_key_b64
    )


class Config:
    """Top-level application configuration assembled from environment variables."""

    persistence = _PersistenceConfig()
    runbooks = _RunbooksConfig()
    agent = _AgentConfig()
    data = _DataConfig()
    vuln = _VulnConfig()
    elastic: "_ElasticConfig | None" = _load_elastic_config()
    kibana: "_KibanaConfig | None" = _load_kibana_config()
    okta: "_OktaConfig | None" = _load_okta_config()
    mcp_bearer_token: "str | None" = os.environ.get("MCP_BEARER_TOKEN") or None


config = Config()
config.agent.set_model_api_key()

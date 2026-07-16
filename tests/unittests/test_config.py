"""Unit tests for application config, focusing on OktaConfig and ElasticConfig env var loading."""

import importlib
import os
from unittest.mock import patch

_OKTA_VARS = ("OKTA_DOMAIN", "OKTA_CLIENT_ID", "OKTA_PRIVATE_KEY")
_ELASTIC_VARS = ("ELASTIC_HOST", "ELASTIC_API_KEY", "ELASTIC_INDEX_PATTERN")


def _reload_config():
    """Re-import config so _load_okta_config() re-evaluates env vars."""
    import src.config as cfg_module

    importlib.reload(cfg_module)
    return cfg_module


def _clean_env() -> dict:
    return {k: v for k, v in os.environ.items() if k not in _OKTA_VARS and k not in _ELASTIC_VARS}


def _env_without_okta() -> dict:
    return {k: v for k, v in os.environ.items() if k not in _OKTA_VARS}


# ---------------------------------------------------------------------------
# OktaConfig env var loading
# ---------------------------------------------------------------------------


def test_okta_config_is_none_when_no_env_vars():
    with patch.dict(os.environ, _env_without_okta(), clear=True):
        cfg = _reload_config()
        assert cfg.config.okta is None


def test_okta_config_is_none_when_only_domain_set():
    env = _env_without_okta()
    env["OKTA_DOMAIN"] = "https://example.okta.com"
    with patch.dict(os.environ, env, clear=True):
        cfg = _reload_config()
        assert cfg.config.okta is None


def test_okta_config_is_none_when_domain_and_client_id_but_no_key():
    env = _env_without_okta()
    env["OKTA_DOMAIN"] = "https://example.okta.com"
    env["OKTA_CLIENT_ID"] = "0oa_test_client"
    with patch.dict(os.environ, env, clear=True):
        cfg = _reload_config()
        assert cfg.config.okta is None


def test_okta_config_is_populated_when_all_env_vars_set():
    env = _env_without_okta()
    env["OKTA_DOMAIN"] = "https://example.okta.com"
    env["OKTA_CLIENT_ID"] = "0oa_test_client"
    env["OKTA_PRIVATE_KEY"] = "base64encodedkey"
    with patch.dict(os.environ, env, clear=True):
        cfg = _reload_config()
        assert cfg.config.okta is not None
        assert cfg.config.okta.domain == "https://example.okta.com"
        assert cfg.config.okta.client_id == "0oa_test_client"
        assert cfg.config.okta.private_key_b64 == "base64encodedkey"


# ---------------------------------------------------------------------------
# ElasticConfig env var loading
# ---------------------------------------------------------------------------


def test_elastic_config_is_none_when_no_env_vars():
    with patch.dict(os.environ, _clean_env(), clear=True):
        cfg = _reload_config()
        assert cfg.config.elastic is None


def test_elastic_config_is_none_when_only_host_set():
    env = _clean_env()
    env["ELASTIC_HOST"] = "https://my-cluster.es.io:9200"
    with patch.dict(os.environ, env, clear=True):
        cfg = _reload_config()
        assert cfg.config.elastic is None


def test_elastic_config_is_populated_when_host_and_key_set():
    env = _clean_env()
    env["ELASTIC_HOST"] = "https://my-cluster.es.io:9200"
    env["ELASTIC_API_KEY"] = "myapikey"
    with patch.dict(os.environ, env, clear=True):
        cfg = _reload_config()
        assert cfg.config.elastic is not None
        assert cfg.config.elastic.host == "https://my-cluster.es.io:9200"
        assert cfg.config.elastic.api_key == "myapikey"
        assert cfg.config.elastic.index_pattern is None


def test_elastic_config_index_pattern_set_when_provided():
    env = _clean_env()
    env["ELASTIC_HOST"] = "https://my-cluster.es.io:9200"
    env["ELASTIC_API_KEY"] = "myapikey"
    env["ELASTIC_INDEX_PATTERN"] = "logs-*"
    with patch.dict(os.environ, env, clear=True):
        cfg = _reload_config()
        assert cfg.config.elastic is not None
        assert cfg.config.elastic.index_pattern == "logs-*"

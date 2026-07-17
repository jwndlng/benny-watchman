"""Unit tests for the TOML + env configuration layer (pydantic-settings).

Each test writes a temp config.toml, points CONFIG_FILE at it, sets a controlled
environment, and reloads src.config so `Settings()` re-evaluates from scratch.
"""

import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest


def _load(tmp_path: Path, toml: str | None, env: dict[str, str]):
    """Reload src.config under a controlled TOML file + environment."""
    if toml is None:
        toml_path = tmp_path / "absent.toml"  # deliberately does not exist
    else:
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(toml)
    full_env = {"CONFIG_FILE": str(toml_path), **env}
    with patch.dict(os.environ, full_env, clear=True):
        import src.config as cfg_module

        importlib.reload(cfg_module)
        return cfg_module


# ---------------------------------------------------------------------------
# Fallback + defaults
# ---------------------------------------------------------------------------


def test_missing_toml_falls_back_to_defaults(tmp_path):
    m = _load(tmp_path, toml=None, env={})
    assert m.config.agent.model == "google-gla:gemini-3.1-flash-lite-preview"
    assert m.config.data.sqlite is None
    assert m.config.data.elastic is None
    assert m.config.kibana is None
    assert m.config.okta is None


# ---------------------------------------------------------------------------
# Precedence: env > TOML > default
# ---------------------------------------------------------------------------


def test_toml_value_used_when_no_env(tmp_path):
    m = _load(tmp_path, "[agent]\nmodel = 'openai:from-toml'\n", env={})
    assert m.config.agent.model == "openai:from-toml"


def test_env_overrides_toml(tmp_path):
    m = _load(
        tmp_path,
        "[agent]\nmodel = 'openai:from-toml'\n",
        env={"AGENT__MODEL": "anthropic:from-env"},
    )
    assert m.config.agent.model == "anthropic:from-env"


# ---------------------------------------------------------------------------
# Secrets are injected from env into their sections
# ---------------------------------------------------------------------------


def test_kibana_secret_injected_from_env(tmp_path):
    m = _load(
        tmp_path,
        "[kibana]\nurl = 'https://kb/s/isec'\ncase_owner = 'securitySolution'\n",
        env={"KIBANA_TRIAGE_API_KEY": "kib-secret"},
    )
    assert m.config.kibana is not None
    assert m.config.kibana.url == "https://kb/s/isec"
    assert m.config.kibana.api_key == "kib-secret"


def test_elastic_data_source_secret_injected(tmp_path):
    m = _load(
        tmp_path,
        "[data.elastic]\nhost = 'https://es:9200'\nindex_pattern = 'logs-*'\n",
        env={"ELASTIC_API_KEY": "es-secret"},
    )
    assert m.config.data.elastic is not None
    assert m.config.data.elastic.api_key == "es-secret"
    assert m.config.data.elastic.index_pattern == "logs-*"


# ---------------------------------------------------------------------------
# Section presence enables; absence disables
# ---------------------------------------------------------------------------


def test_sqlite_section_presence_enables(tmp_path):
    m = _load(tmp_path, "[data.sqlite]\nname = 'logs'\ndb_path = 'x.db'\n", env={})
    assert m.config.data.sqlite is not None
    assert m.config.data.sqlite.name == "logs"
    assert m.config.data.elastic is None


def test_okta_absent_is_none(tmp_path):
    m = _load(tmp_path, "[agent]\nmodel = 'openai:x'\n", env={})
    assert m.config.okta is None


def test_okta_present_with_secrets(tmp_path):
    m = _load(
        tmp_path,
        "[okta]\ndomain = 'https://x.okta.com'\n",
        env={"OKTA_CLIENT_ID": "cid", "OKTA_PRIVATE_KEY": "pk"},
    )
    assert m.config.okta is not None
    assert m.config.okta.domain == "https://x.okta.com"
    assert m.config.okta.client_id == "cid"
    assert m.config.okta.private_key_b64 == "pk"


# ---------------------------------------------------------------------------
# Fail fast: a configured section missing its required secret
# ---------------------------------------------------------------------------


def test_kibana_without_secret_fails_fast(tmp_path):
    with pytest.raises(Exception):  # noqa: B017 — pydantic ValidationError at import
        _load(tmp_path, "[kibana]\nurl = 'https://kb'\n", env={})


# ---------------------------------------------------------------------------
# The committed example carries no secrets
# ---------------------------------------------------------------------------


def test_example_config_has_no_secrets():
    lines = Path("config.toml.example").read_text().splitlines()
    # only active (uncommented) lines matter — comments may name env-only secrets
    active = "\n".join(ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")).lower()
    for needle in ("api_key", "token", "private_key", "client_id"):
        assert needle not in active, f"secret {needle!r} assigned in example config"

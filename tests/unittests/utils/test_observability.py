"""Unit tests for the unified logging setup (configure_logging)."""

import logging

import pytest

from src.utils.observability import configure_logging


@pytest.fixture
def restore_logging():
    """Snapshot and restore global logging state — configure_logging mutates root."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_noisy = {name: logging.getLogger(name).level for name in ("httpx", "elastic_transport")}
    try:
        yield
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
        for name, level in saved_noisy.items():
            logging.getLogger(name).setLevel(level)


def test_installs_single_stdout_handler(restore_logging):
    configure_logging()
    handlers = logging.getLogger().handlers
    assert [type(h).__name__ for h in handlers] == ["StreamHandler"]


def test_fastmcp_basicconfig_is_neutralised(restore_logging):
    """Once root is configured, FastMCP's logging.basicConfig must not add a handler."""
    configure_logging()
    from mcp.server.fastmcp.utilities.logging import configure_logging as fastmcp_cfg

    fastmcp_cfg("INFO")

    handler_types = [type(h).__name__ for h in logging.getLogger().handlers]
    assert handler_types == ["StreamHandler"]  # no RichHandler leaked onto root


def test_noisy_loggers_gated_to_warning(restore_logging, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    configure_logging()
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("elastic_transport").level == logging.WARNING


def test_debug_level_keeps_noisy_loggers_verbose(restore_logging, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    configure_logging()
    assert logging.getLogger().level == logging.DEBUG
    assert logging.getLogger("httpx").level == logging.DEBUG

"""Unit tests for AnalystAgent.lookup_user — Okta delegation."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.models.test import TestModel

from src.modules.siem.analyst import AnalystAgent
from src.core.orchestration.runbook_registry import Runbook
from src.capabilities.identity.assessment import IdentityCapability
from src.capabilities.identity.user_profile import UserProfile


def _make_runbook() -> Runbook:
    return Runbook(name="generic", description="test", instructions="Investigate.")


def _make_analyst(okta_client=None) -> AnalystAgent:
    identity = IdentityCapability(okta_client) if okta_client is not None else None
    return AnalystAgent(
        model=TestModel(),
        runbook=_make_runbook(),
        data_agents=[],
        identity=identity,
    )


def _real_profile(username: str) -> UserProfile:
    return UserProfile(
        name="Jane Doe",
        email=f"{username}@corp.example.com",
        team="Security",
        role="SOC Analyst",
        manager="John Smith",
        employment_status="active",
        start_date=date(2022, 3, 15),
        termination_date=None,
        tenure_days=100,
        work_location="Berlin",
        timezone="Europe/Berlin",
        on_call=False,
        out_of_office=False,
        access_level="Employee",
    )


# ---------------------------------------------------------------------------
# 5.6 lookup_user delegation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_lookup_user_returns_okta_profile_when_configured():
    profile = _real_profile("jane.doe")
    okta_client = MagicMock()
    okta_client.get_user = AsyncMock(return_value=profile)

    analyst = _make_analyst(okta_client=okta_client)
    result = await analyst.lookup_user("jane.doe")

    okta_client.get_user.assert_called_once_with("jane.doe")
    assert result is profile
    assert result.name == "Jane Doe"
    assert result.team == "Security"


@pytest.mark.anyio
async def test_lookup_user_returns_none_when_okta_returns_none():
    okta_client = MagicMock()
    okta_client.get_user = AsyncMock(return_value=None)

    analyst = _make_analyst(okta_client=okta_client)
    result = await analyst.lookup_user("unknown_user")

    assert result is None


@pytest.mark.anyio
async def test_lookup_user_returns_none_when_no_okta_client():
    analyst = _make_analyst(okta_client=None)
    result = await analyst.lookup_user("some_user")

    assert result is None

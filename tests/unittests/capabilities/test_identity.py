"""Unit tests for the IdentityTool composite lookup."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.capabilities.tools.identity.assessment import IdentityTool
from src.capabilities.tools.identity.user_profile import UserProfile


def _profile() -> UserProfile:
    return UserProfile(
        name="Jane Doe",
        email="jane.doe@corp.example.com",
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


@pytest.mark.anyio
async def test_lookup_user_delegates_to_okta():
    profile = _profile()
    okta = MagicMock()
    okta.get_user = AsyncMock(return_value=profile)

    result = await IdentityTool(okta).lookup_user("jane.doe")

    okta.get_user.assert_called_once_with("jane.doe")
    assert result is profile


@pytest.mark.anyio
async def test_lookup_user_returns_none_without_client():
    assert await IdentityTool(None).lookup_user("jane.doe") is None

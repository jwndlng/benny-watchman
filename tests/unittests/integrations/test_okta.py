"""Unit tests for OktaClient — Okta SDK is mocked throughout."""

import base64
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.okta import OktaClient

_ORG = "https://example.okta.com"
_CLIENT_ID = "0oa_test_client_id"
_TEST_JWK = base64.b64encode(
    json.dumps({"kid": "test-kid", "kty": "RSA"}).encode()
).decode()


def _make_client(sdk_mock: MagicMock) -> OktaClient:
    with patch("src.integrations.okta.OktaSDKClient", return_value=sdk_mock):
        return OktaClient(
            org_url=_ORG,
            client_id=_CLIENT_ID,
            private_key_b64=_TEST_JWK,
        )


def _mock_user(
    status: str = "ACTIVE",
    activated=date(2022, 3, 15),
    **profile_attrs,
) -> MagicMock:
    defaults = {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
        "department": "Security",
        "title": "SOC Analyst",
        "city": "Berlin",
        "timezone": "Europe/Berlin",
        "userType": "Employee",
        "managerId": None,
    }
    defaults.update(profile_attrs)
    profile = MagicMock(**defaults)
    for k, v in defaults.items():
        setattr(profile, k, v)

    user = MagicMock()
    user.id = "00u_test_id"
    user.status = status
    user.activated = activated
    user.profile = profile
    return user


def _mock_manager(first: str = "John", last: str = "Smith") -> MagicMock:
    profile = MagicMock()
    profile.firstName = first
    profile.lastName = last
    manager = MagicMock()
    manager.profile = profile
    return manager


# ---------------------------------------------------------------------------
# 5.1 Happy path — full profile
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_user_full_profile():
    sdk = AsyncMock()
    user = _mock_user()
    manager = _mock_manager()
    sdk.get_user.side_effect = [(user, MagicMock(), None), (manager, MagicMock(), None)]
    sdk.list_linked_objects_for_user.return_value = ([], MagicMock(), None)

    client = _make_client(sdk)
    profile = await client.get_user("jane.doe@example.com")

    assert profile is not None
    assert profile.name == "Jane Doe"
    assert profile.email == "jane.doe@example.com"
    assert profile.team == "Security"
    assert profile.role == "SOC Analyst"
    assert profile.employment_status == "active"
    assert profile.work_location == "Berlin"
    assert profile.timezone == "Europe/Berlin"
    assert profile.access_level == "Employee"
    assert profile.on_call is False
    assert profile.out_of_office is False
    assert profile.termination_date is None
    assert profile.start_date == date(2022, 3, 15)
    assert profile.tenure_days == (date.today() - date(2022, 3, 15)).days


# ---------------------------------------------------------------------------
# 5.2 Sparse profile — absent optional fields fall back to defaults
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_user_sparse_profile_uses_fallbacks():
    sdk = AsyncMock()
    user = _mock_user(
        department=None, title=None, city=None, timezone=None, userType=None
    )
    manager = _mock_manager()
    sdk.get_user.side_effect = [(user, MagicMock(), None), (manager, MagicMock(), None)]
    sdk.list_linked_objects_for_user.return_value = ([], MagicMock(), None)

    profile = await _make_client(sdk).get_user("jane@example.com")

    assert profile is not None
    assert profile.team == "unknown"
    assert profile.role == "unknown"
    assert profile.work_location == "remote"
    assert profile.timezone == "UTC"
    assert profile.access_level == "unknown"


@pytest.mark.anyio
async def test_get_user_missing_activated_defaults_start_date():
    sdk = AsyncMock()
    user = _mock_user(activated=None)
    manager = _mock_manager()
    sdk.get_user.side_effect = [(user, MagicMock(), None), (manager, MagicMock(), None)]
    sdk.list_linked_objects_for_user.return_value = ([], MagicMock(), None)

    profile = await _make_client(sdk).get_user("jane@example.com")

    assert profile is not None
    assert profile.start_date == date(2000, 1, 1)


# ---------------------------------------------------------------------------
# 5.3 Employment status mapping
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "okta_status,expected",
    [
        ("ACTIVE", "active"),
        ("DEPROVISIONED", "terminated"),
        ("SUSPENDED", "on_leave"),
        ("LOCKED_OUT", "on_leave"),
        ("STAGED", "on_leave"),
    ],
)
async def test_employment_status_mapping(okta_status: str, expected: str):
    sdk = AsyncMock()
    user = _mock_user(status=okta_status)
    manager = _mock_manager()
    sdk.get_user.side_effect = [(user, MagicMock(), None), (manager, MagicMock(), None)]
    sdk.list_linked_objects_for_user.return_value = ([], MagicMock(), None)

    profile = await _make_client(sdk).get_user("user@example.com")

    assert profile is not None
    assert profile.employment_status == expected


# ---------------------------------------------------------------------------
# 5.4 Returns None on SDK error
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_user_returns_none_when_sdk_returns_error():
    sdk = AsyncMock()
    sdk.get_user.return_value = (None, MagicMock(), "User not found")

    result = await _make_client(sdk).get_user("nobody@example.com")

    assert result is None


@pytest.mark.anyio
async def test_get_user_returns_none_on_exception():
    sdk = AsyncMock()
    sdk.get_user.side_effect = Exception("network failure")

    result = await _make_client(sdk).get_user("user@example.com")

    assert result is None


# ---------------------------------------------------------------------------
# 5.5 Manager fallback — via managerId, linked objects, and hard failure
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_manager_resolved_via_manager_id():
    sdk = AsyncMock()
    user = _mock_user(managerId="00u_manager_id")
    manager = _mock_manager(first="Alice", last="Wong")
    sdk.get_user.side_effect = [
        (user, MagicMock(), None),
        (manager, MagicMock(), None),  # manager by ID
    ]

    profile = await _make_client(sdk).get_user("jane@example.com")

    assert profile is not None
    assert profile.manager == "Alice Wong"


@pytest.mark.anyio
async def test_manager_resolved_via_linked_objects_when_manager_id_absent():
    sdk = AsyncMock()
    user = _mock_user(managerId=None)
    linked_manager_ref = MagicMock()
    linked_manager_ref.id = "00u_linked_mgr"
    manager = _mock_manager(first="Bob", last="Yuen")
    sdk.get_user.side_effect = [
        (user, MagicMock(), None),
        (manager, MagicMock(), None),  # manager via linked objects
    ]
    sdk.list_linked_objects_for_user.return_value = (
        [linked_manager_ref],
        MagicMock(),
        None,
    )

    profile = await _make_client(sdk).get_user("jane@example.com")

    assert profile is not None
    assert profile.manager == "Bob Yuen"


@pytest.mark.anyio
async def test_manager_falls_back_to_unknown_when_all_lookups_fail():
    sdk = AsyncMock()
    user = _mock_user(managerId=None)
    sdk.get_user.return_value = (user, MagicMock(), None)
    sdk.list_linked_objects_for_user.return_value = (None, MagicMock(), "error")

    profile = await _make_client(sdk).get_user("jane@example.com")

    assert profile is not None
    assert profile.manager == "unknown"


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_constructor_raises_on_empty_private_key():
    with pytest.raises(ValueError, match="OKTA_PRIVATE_KEY is empty"):
        OktaClient(org_url=_ORG, client_id=_CLIENT_ID, private_key_b64="")


def test_constructor_passes_jwt_config_to_sdk():
    with patch("src.integrations.okta.OktaSDKClient") as MockSDK:
        MockSDK.return_value = MagicMock()
        OktaClient(org_url=_ORG, client_id=_CLIENT_ID, private_key_b64=_TEST_JWK)

        call_config = MockSDK.call_args[0][0]
        assert call_config["authorizationMode"] == "PrivateKey"
        assert call_config["clientId"] == _CLIENT_ID
        assert call_config["orgUrl"] == _ORG
        assert call_config["kid"] == "test-kid"

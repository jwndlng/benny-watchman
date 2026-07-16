"""Okta IDP integration — read-only, single-user identity lookups via JWT private key auth."""

import base64
import json
from datetime import date, datetime

from okta.client import Client as OktaSDKClient

from src.capabilities.tools.identity.user_profile import UserProfile

_STATUS_MAP: dict[str, str] = {
    "ACTIVE": "active",
    "DEPROVISIONED": "terminated",
}


class OktaClient:
    """Okta SDK client using JWT private key authentication.

    Makes at most two SDK calls per get_user() invocation: one for the user
    profile and one for the manager. Returns None on any error so that callers
    can fall back gracefully without aborting an investigation.
    """

    def __init__(self, org_url: str, client_id: str, private_key_b64: str) -> None:
        if not private_key_b64:
            raise ValueError(
                "OKTA_PRIVATE_KEY is empty — check that the env var is set and passed to the container"
            )
        jwk_str = base64.b64decode(private_key_b64).decode()
        jwk = json.loads(jwk_str)
        self._client = OktaSDKClient(
            {
                "orgUrl": org_url,
                "authorizationMode": "PrivateKey",
                "clientId": client_id,
                "scopes": ["okta.users.read"],
                "privateKey": jwk_str,
                "kid": jwk.get("kid"),
            }
        )

    async def get_user(self, login: str) -> UserProfile | None:
        """Fetch identity and employment context for the given Okta login.

        Returns None if the user is not found or any error occurs.
        """
        try:
            user, _, err = await self._client.get_user(login)
            if err:
                return None
            manager = await self._fetch_manager(user)
            return self._map_profile(user, manager)
        except Exception:
            return None

    async def _fetch_manager(self, user: object) -> str:
        try:
            manager_id = getattr(user.profile, "managerId", None)
            if manager_id:
                manager, _, err = await self._client.get_user(manager_id)
                if not err:
                    p = manager.profile
                    name = f"{p.firstName} {p.lastName}".strip()
                    return name or "unknown"

            managers, _, err = await self._client.list_linked_objects_for_user(
                user.id, "manager", None
            )
            if err or not managers:
                return "unknown"

            manager, _, err = await self._client.get_user(managers[0].id)
            if err:
                return "unknown"
            p = manager.profile
            return f"{p.firstName} {p.lastName}".strip() or "unknown"
        except Exception:
            return "unknown"

    def _map_profile(self, user: object, manager: str) -> UserProfile:
        profile = user.profile
        status = str(user.status or "")
        employment_status = _STATUS_MAP.get(status, "on_leave")

        activated = user.activated
        if activated is not None:
            start_date = (
                activated.date()
                if isinstance(activated, datetime)
                else date.fromisoformat(str(activated).split("T")[0])
            )
        else:
            start_date = date(2000, 1, 1)
        tenure_days = (date.today() - start_date).days

        first = getattr(profile, "firstName", "") or ""
        last = getattr(profile, "lastName", "") or ""
        name = f"{first} {last}".strip() or "unknown"

        return UserProfile(
            name=name,
            email=getattr(profile, "email", "") or "",
            team=getattr(profile, "department", None) or "unknown",
            role=getattr(profile, "title", None) or "unknown",
            manager=manager,
            employment_status=employment_status,
            start_date=start_date,
            termination_date=None,
            tenure_days=tenure_days,
            work_location=getattr(profile, "city", None) or "remote",
            timezone=getattr(profile, "timezone", None) or "UTC",
            on_call=False,
            out_of_office=False,
            access_level=getattr(profile, "userType", None) or "unknown",
        )

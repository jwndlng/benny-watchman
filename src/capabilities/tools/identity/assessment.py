"""Identity/access capability — composite IDP lookups shared by all modules.

A single call bundles the identity lookups a module needs (currently the Okta
user profile; extensible to app permissions, admin grants, group memberships).
Deterministic composite tool for now — it can graduate to an IDPAgent (an LLM
loop) later without changing consumers, because callers depend on this interface
rather than on the Okta client directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.capabilities.tools.identity.okta import OktaClient
    from src.capabilities.tools.identity.user_profile import UserProfile


class IdentityCapability:
    """Composite identity/access lookups backed by an IDP client (Okta)."""

    def __init__(self, okta_client: OktaClient | None = None) -> None:
        self._okta = okta_client

    async def lookup_user(self, username: str) -> UserProfile | None:
        """Return identity, role, and availability context for a user.

        Returns None when identity context is unavailable (no IDP configured, or
        the user is not found).
        """
        if self._okta is None:
            return None
        return await self._okta.get_user(username)

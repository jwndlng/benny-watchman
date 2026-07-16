"""Bearer token ASGI middleware for the /mcp mount."""

from __future__ import annotations

from typing import Any


class BearerAuthMiddleware:
    """Pure ASGI middleware that gates HTTP requests with a static Bearer token.

    Applied as a wrapper around the FastMCP ASGI app so that streaming
    responses (used by Streamable HTTP transport) are not buffered.
    Returns 401 Unauthorized when the Authorization header does not match.
    """

    def __init__(self, app: Any, token: str) -> None:
        self._app = app
        self._expected = f"Bearer {token}".encode()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            if headers.get(b"authorization") != self._expected:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [[b"content-length", b"12"]],
                    }
                )
                await send({"type": "http.response.body", "body": b"Unauthorized"})
                return
        await self._app(scope, receive, send)

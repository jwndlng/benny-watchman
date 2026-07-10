"""Unit tests for BearerAuthMiddleware."""

import pytest

from src.mcp_auth import BearerAuthMiddleware


class _Response:
    def __init__(self):
        self.status: int | None = None
        self.body: bytes = b""


async def _call(middleware: BearerAuthMiddleware, auth_header: str | None) -> _Response:
    """Drive the middleware through a minimal ASGI http cycle."""
    headers = []
    if auth_header is not None:
        headers.append([b"authorization", auth_header.encode()])

    scope = {"type": "http", "headers": headers}
    response = _Response()

    received: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(event: dict):
        if event["type"] == "http.response.start":
            response.status = event["status"]
        elif event["type"] == "http.response.body":
            response.body = event.get("body", b"")

    downstream_called = False

    async def downstream(scope, receive, send):
        nonlocal downstream_called
        downstream_called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = BearerAuthMiddleware(downstream, "secret-token")
    await mw(scope, receive, send)
    response._downstream_called = downstream_called
    return response


@pytest.mark.anyio
async def test_correct_token_passes_through():
    response = await _call(
        BearerAuthMiddleware(None, "secret-token"), "Bearer secret-token"
    )
    assert response.status == 200


@pytest.mark.anyio
async def test_wrong_token_returns_401():
    response = await _call(
        BearerAuthMiddleware(None, "secret-token"), "Bearer wrong-token"
    )
    assert response.status == 401
    assert response.body == b"Unauthorized"


@pytest.mark.anyio
async def test_missing_header_returns_401():
    response = await _call(BearerAuthMiddleware(None, "secret-token"), None)
    assert response.status == 401


@pytest.mark.anyio
async def test_non_http_scope_passes_through():
    """Lifespan and WebSocket scopes should bypass auth."""
    received = False

    async def downstream(scope, receive, send):
        nonlocal received
        received = True

    mw = BearerAuthMiddleware(downstream, "secret-token")
    await mw({"type": "lifespan"}, None, None)
    assert received

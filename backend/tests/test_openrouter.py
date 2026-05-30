"""Tests for OpenRouter client retry and payload shape."""
from __future__ import annotations

import json

import httpx
import pytest

from app.services.llm.openrouter import OpenRouterClient, OpenRouterError


def _completion_body(content: dict[str, object]) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(content),
                }
            }
        ]
    }


@pytest.mark.asyncio
async def test_chat_json_sends_schema_and_headers() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["json"] = json.loads(request.content)
        return httpx.Response(200, json=_completion_body({"ok": True}))

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://openrouter.test") as http:
        client = OpenRouterClient(
            api_key="test-key",
            base_url="https://openrouter.test",
            model="test/model",
            app_name="finance-tracker",
            app_url="http://localhost:5173",
            client=http,
        )
        result = await client.chat_json(
            system="sys",
            user="usr",
            schema={"type": "object"},
        )

    assert result == {"ok": True}
    payload = seen["json"]
    assert isinstance(payload, dict)
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["provider"] == {"require_parameters": True}
    headers = seen["headers"]
    assert headers.get("authorization") == "Bearer test-key"
    assert headers.get("http-referer") == "http://localhost:5173"
    assert headers.get("x-title") == "finance-tracker"


@pytest.mark.asyncio
async def test_rate_limit_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("app.services.llm.openrouter.asyncio.sleep", _noop_sleep)
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429)
        return httpx.Response(200, json=_completion_body({"results": []}))

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://openrouter.test") as http:
        client = OpenRouterClient(
            api_key="k",
            base_url="https://openrouter.test",
            model="m",
            app_name="app",
            app_url="http://x",
            client=http,
        )
        result = await client.chat_json(system="s", user="u", schema={"type": "object"})

    assert attempts == 3
    assert result == {"results": []}


@pytest.mark.asyncio
async def test_malformed_json_raises_openrouter_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "not-json"}},
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://openrouter.test") as http:
        client = OpenRouterClient(
            api_key="k",
            base_url="https://openrouter.test",
            model="m",
            app_name="app",
            app_url="http://x",
            client=http,
        )
        with pytest.raises(OpenRouterError, match="not valid JSON"):
            await client.chat_json(system="s", user="u", schema={"type": "object"})


@pytest.mark.asyncio
async def test_rate_limit_exhausted_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("app.services.llm.openrouter.asyncio.sleep", _noop_sleep)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://openrouter.test") as http:
        client = OpenRouterClient(
            api_key="k",
            base_url="https://openrouter.test",
            model="m",
            app_name="app",
            app_url="http://x",
            client=http,
        )
        with pytest.raises(OpenRouterError, match="rate limited"):
            await client.chat_json(system="s", user="u", schema={"type": "object"})

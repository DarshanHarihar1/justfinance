from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

_RATE_LIMIT_BACKOFFS = (4.0, 8.0, 16.0)
_SERVER_ERROR_BACKOFFS = (2.0, 4.0)


class OpenRouterError(Exception):
    """OpenRouter request failed after retries."""


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        app_name: str,
        app_url: str,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._owns_client = client is None
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": app_url,
            "X-Title": app_name,
        }
        if client is None:
            self._client = httpx.AsyncClient(
                base_url=base_url.rstrip("/"),
                timeout=timeout,
                headers=headers,
            )
        else:
            self._client = client
            for key, value in headers.items():
                self._client.headers.setdefault(key, value)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @property
    def enabled(self) -> bool:
        return bool(self._api_key.strip())

    async def chat_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": model or self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "provider": {"require_parameters": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "result", "strict": True, "schema": schema},
            },
            "temperature": 0,
        }
        body = await self._post_with_retries("/chat/completions", payload)
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise OpenRouterError("OpenRouter response JSON root is not an object")
        return parsed

    async def _post_with_retries(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        rate_attempts = 0
        server_attempts = 0

        while True:
            try:
                response = await self._client.post(path, json=payload)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if server_attempts >= len(_SERVER_ERROR_BACKOFFS):
                    raise OpenRouterError("network error talking to OpenRouter") from exc
                await asyncio.sleep(_SERVER_ERROR_BACKOFFS[server_attempts])
                server_attempts += 1
                continue

            if response.status_code == 429:
                if rate_attempts >= len(_RATE_LIMIT_BACKOFFS):
                    raise OpenRouterError("rate limited by OpenRouter")
                await asyncio.sleep(_RATE_LIMIT_BACKOFFS[rate_attempts])
                rate_attempts += 1
                continue

            if response.status_code >= 500:
                if server_attempts >= len(_SERVER_ERROR_BACKOFFS):
                    response.raise_for_status()
                await asyncio.sleep(_SERVER_ERROR_BACKOFFS[server_attempts])
                server_attempts += 1
                continue

            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise OpenRouterError("OpenRouter response body is not an object")
            return body

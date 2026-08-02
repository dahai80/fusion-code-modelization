from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .config import ModelConfig

logger = logging.getLogger(__name__)


class MLXClient:
    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        self._base_url = self.config.base_url.rstrip("/")

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        params = self.config.to_chat_params()
        if model is not None:
            params["model"] = model
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params["messages"] = messages

        request_timeout = timeout or self.config.timeout
        last_error = None

        for attempt in range(self.config.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=request_timeout) as client:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        json=params,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.debug(
                        "chat completed: model=%s tokens=%d",
                        params["model"],
                        len(content),
                    )
                    return {"status": "completed", "content": content}
            except Exception as e:
                last_error = e
                logger.warning(
                    "chat attempt %d/%d failed: %s",
                    attempt + 1,
                    self.config.retry_attempts,
                    e,
                )
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)

        return {"status": "failed", "error": str(last_error)}

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        params = self.config.to_chat_params()
        if model is not None:
            params["model"] = model
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params["messages"] = messages
        params["stream"] = True

        async with (
            httpx.AsyncClient(timeout=self.config.timeout) as client,
            client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=params,
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload.strip() == "[DONE]":
                    break
                try:
                    import json

                    chunk = json.loads(payload)
                    delta = chunk["choices"][0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
                except Exception:
                    continue

    @staticmethod
    def extract_code(content: str, language: str = "") -> str:
        pattern = r"```(?:\w+)?\n(.+?)\n```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content.strip()

    async def simple_chat(self, prompt: str, **kwargs) -> str:
        result = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        if result["status"] == "completed":
            return result["content"]
        raise RuntimeError(result.get("error", "Unknown error"))

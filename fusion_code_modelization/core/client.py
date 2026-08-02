from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import httpx

from .config import ModelConfig

if TYPE_CHECKING:
    from .config import DualModelConfig

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


class DualStackClient:
    def __init__(self, dual_config: DualModelConfig | None = None):
        from .config import DualModelConfig, ModelRouter

        self.dual_config = dual_config or DualModelConfig()
        self._router = ModelRouter(self.dual_config)
        self._local_client = MLXClient(self.dual_config.local_config)
        self._cloud_client = MLXClient(self.dual_config.cloud_config)
        self._active_stack: str = "local"
        logger.info("DualStackClient initialized: strategy=%s", self.dual_config.routing_strategy.value)

    @property
    def active_stack(self) -> str:
        return self._active_stack

    def switch_stack(self, stack: str) -> None:
        from .config import ModelStack

        valid = {ModelStack.LOCAL.value, ModelStack.CLOUD.value}
        if stack not in valid:
            raise ValueError(f"Invalid stack '{stack}', must be one of {valid}")
        self._active_stack = stack
        logger.info("switched model stack to: %s", stack)

    def _get_client(self, stack: str | None = None) -> MLXClient:
        from .config import ModelStack

        target = stack or self._active_stack
        if target == ModelStack.CLOUD.value:
            return self._cloud_client
        return self._local_client

    async def smart_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        from .config import ModelStack

        prompt_text = " ".join(m.get("content", "") for m in messages)
        stack = self._router.route(prompt_text)
        client = self._get_client(stack.value)
        logger.info("smart_chat routed to %s stack", stack.value)
        result = await client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        if result["status"] == "failed" and self.dual_config.fallback_enabled:
            fallback = ModelStack.CLOUD if stack == ModelStack.LOCAL else ModelStack.LOCAL
            fallback_client = self._get_client(fallback.value)
            logger.warning("primary %s failed, falling back to %s", stack.value, fallback.value)
            result = await fallback_client.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            if result["status"] == "completed":
                result["routed_stack"] = fallback.value
        else:
            if result["status"] == "completed":
                result["routed_stack"] = stack.value
        return result

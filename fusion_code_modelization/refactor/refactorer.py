# GateGuard: Importers: refactor/__init__.py, CLI. Affected API: adds refactor_stream(). Data schemas: none. User instruction: Phase 6 — add streaming LLM support.

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig

logger = logging.getLogger(__name__)


class IncrementalRefactorer:
    def __init__(self, mlx_url: str = DEFAULT_GATEWAY_URL, client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    async def characterize(self, code: str, language: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Generate characterization tests for this {language} code. "
                        f"The tests should capture the current behavior by testing "
                        f"inputs and expected outputs. Return the test code only.\n\n"
                        f"```{language}\n{code[:3000]}\n```"
                    ),
                }
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        if result["status"] == "completed":
            return {"status": "completed", "tests": result["content"], "language": language}
        return {"status": "failed", "error": result.get("error", "Unknown")}

    async def refactor(self, code: str, language: str, instructions: str = "") -> dict[str, Any]:
        prompt = f"Refactor the following {language} code. Improve code quality without changing business logic.\n"
        if instructions:
            prompt += f"Specific instructions: {instructions}\n"
        prompt += f"\n```{language}\n{code[:4000]}\n```\n\nRefactored code:"

        result = await self._client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.1,
        )
        if result["status"] == "completed":
            refactored = MLXClient.extract_code(result["content"])
            return {
                "status": "completed",
                "original": code,
                "refactored": refactored,
                "original_lines": len(code.splitlines()),
                "refactored_lines": len(refactored.splitlines()),
            }
        return {"status": "failed", "error": result.get("error", "Unknown")}

    async def refactor_stream(self, code: str, language: str, instructions: str = "") -> AsyncIterator[dict[str, Any]]:
        prompt = f"Refactor the following {language} code. Improve code quality without changing business logic.\n"
        if instructions:
            prompt += f"Specific instructions: {instructions}\n"
        prompt += f"\n```{language}\n{code[:4000]}\n```\n\nRefactored code:"

        accumulated = []
        try:
            async for token in self._client.chat_stream(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.1,
            ):
                accumulated.append(token)
                yield {"type": "token", "content": token}

            full = "".join(accumulated)
            refactored = MLXClient.extract_code(full)
            yield {
                "type": "done",
                "result": {
                    "status": "completed",
                    "original": code,
                    "refactored": refactored,
                    "original_lines": len(code.splitlines()),
                    "refactored_lines": len(refactored.splitlines()),
                },
            }
        except Exception as e:
            logger.error("refactor_stream failed: %s", e)
            yield {"type": "done", "result": {"status": "failed", "error": str(e)}}

    async def dual_run_verify(self, original_code: str, refactored_code: str, language: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Do these two {language} code snippets produce the same outputs "
                        f"for the same inputs? Answer YES or NO, then explain differences.\n\n"
                        f"ORIGINAL:\n{original_code[:2000]}\n\n"
                        f"REFACTORED:\n{refactored_code[:2000]}"
                    ),
                }
            ],
            max_tokens=512,
            temperature=0.0,
        )
        if result["status"] == "completed":
            content = result["content"]
            return {
                "verified": any(word in content.upper()[:20] for word in ["YES", "SAME", "IDENTICAL"]),
                "details": content[:500],
            }
        return {"verified": False, "error": result.get("error", "Unknown")}

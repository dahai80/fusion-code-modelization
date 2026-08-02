from __future__ import annotations

import logging
from typing import Any

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import ModelConfig

logger = logging.getLogger(__name__)


class UnitTestGenerator:
    def __init__(self, mlx_url: str = "http://localhost:11434/v1", client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    async def generate_unit_tests(self, code: str, language: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Generate comprehensive unit tests for this {language} code. "
                        f"Include edge cases, normal cases, and error cases. "
                        f"Use the standard testing framework for {language}.\n\n"
                        f"```{language}\n{code[:4000]}\n```"
                    ),
                }
            ],
            max_tokens=4096,
            temperature=0.1,
        )
        if result["status"] == "completed":
            tests = MLXClient.extract_code(result["content"])
            return {"status": "completed", "tests": tests, "language": language}
        return {"status": "failed", "error": result.get("error", "Unknown")}

    async def generate_integration_tests(self, components: list[dict], language: str) -> dict[str, Any]:
        desc = "\n".join(f"- {c.get('name', '?')}: {c.get('desc', '')[:200]}" for c in components)
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Generate integration tests for these {language} components:\n{desc}\n\n"
                        f"Focus on inter-component communication and data flow."
                    ),
                }
            ],
            max_tokens=4096,
            temperature=0.1,
        )
        if result["status"] == "completed":
            return {"status": "completed", "tests": result["content"], "language": language}
        return {"status": "failed", "error": result.get("error", "Unknown")}

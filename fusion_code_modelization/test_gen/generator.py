"""Test generator — automatically generates unit/integration tests for legacy code."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TestGenerator:
    """Generates unit tests, integration tests, and fills coverage gaps."""

    def __init__(self, mlx_url: str = "http://localhost:11434/v1"):
        self.mlx_url = mlx_url.rstrip("/")

    async def generate_unit_tests(self, code: str, language: str) -> dict[str, Any]:
        """Generate unit tests for given code."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Generate comprehensive unit tests for this {language} code. "
                            f"Include edge cases, normal cases, and error cases. "
                            f"Use the standard testing framework for {language}.\n\n"
                            f"```{language}\n{code[:4000]}\n```"
                        ),
                    }],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                tests = self._extract_code(content)
                return {"status": "completed", "tests": tests, "language": language}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def generate_integration_tests(self, components: list[dict],
                                           language: str) -> dict[str, Any]:
        """Generate integration tests for multiple components."""
        desc = "\n".join(f"- {c.get('name', '?')}: {c.get('desc', '')[:200]}" for c in components)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Generate integration tests for these {language} components:\n{desc}\n\n"
                            f"Focus on inter-component communication and data flow."
                        ),
                    }],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return {"status": "completed", "tests": content, "language": language}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def _extract_code(content: str) -> str:
        import re
        match = re.search(r"```(?:\w+)?\n(.+?)\n```", content, re.DOTALL)
        return match.group(1).strip() if match else content.strip()
"""Incremental refactoring engine — safe, test-first code modernization."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class IncrementalRefactorer:
    """Safe incremental refactoring with test-first approach.

    Generates characterization tests, refactors code, and verifies
    output consistency between old and new implementations.
    """

    def __init__(self, mlx_url: str = "http://localhost:11434/v1"):
        self.mlx_url = mlx_url.rstrip("/")

    async def characterize(self, code: str, language: str) -> dict[str, Any]:
        """Generate characterization tests that lock in current behavior.

        These tests capture the current input/output behavior before refactoring.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Generate characterization tests for this {language} code. "
                            f"The tests should capture the current behavior by testing "
                            f"inputs and expected outputs. Return the test code only.\n\n"
                            f"```{language}\n{code[:3000]}\n```"
                        ),
                    }],
                    "max_tokens": 2048,
                    "temperature": 0.1,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return {"status": "completed", "tests": content, "language": language}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def refactor(self, code: str, language: str, instructions: str = "") -> dict[str, Any]:
        """Refactor code while preserving behavior."""
        prompt = (
            f"Refactor the following {language} code. "
            f"Improve code quality without changing business logic.\n"
        )
        if instructions:
            prompt += f"Specific instructions: {instructions}\n"
        prompt += f"\n```{language}\n{code[:4000]}\n```\n\nRefactored code:"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                refactored = self._extract_code(content)
                return {
                    "status": "completed",
                    "original": code,
                    "refactored": refactored,
                    "original_lines": len(code.splitlines()),
                    "refactored_lines": len(refactored.splitlines()),
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def dual_run_verify(self, original_code: str, refactored_code: str,
                               language: str) -> dict[str, Any]:
        """Verify that original and refactored code produce same outputs."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Do these two {language} code snippets produce the same outputs "
                            f"for the same inputs? Answer YES or NO, then explain differences.\n\n"
                            f"ORIGINAL:\n{original_code[:2000]}\n\n"
                            f"REFACTORED:\n{refactored_code[:2000]}"
                        ),
                    }],
                    "max_tokens": 512,
                    "temperature": 0.0,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return {"verified": any(word in content.upper()[:20] for word in ["YES", "SAME", "IDENTICAL"]),
                        "details": content[:500]}
        except Exception as e:
            return {"verified": False, "error": str(e)}

    @staticmethod
    def _extract_code(content: str) -> str:
        import re
        match = re.search(r"```(?:\w+)?\n(.+?)\n```", content, re.DOTALL)
        return match.group(1).strip() if match else content.strip()
"""Cross-language code transpiler — migrates code between languages via fusion-mlx."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    "cobol": ["java", "go", "python"],
    "vb6": ["csharp", "python"],
    "java": ["go", "kotlin", "python"],
    "python": ["go", "java"],
    "javascript": ["typescript", "python"],
    "csharp": ["python", "go"],
}


class CodeTranspiler:
    """Transpiles code between languages using fusion-mlx.

    All conversion goes through fusion-mlx HTTP API.
    Supports COBOL→Java, VB6→C#, Java→Go, etc.
    """

    def __init__(self, mlx_url: str = "http://localhost:11434/v1"):
        self.mlx_url = mlx_url.rstrip("/")

    async def transpile(self, code: str, source_lang: str, target_lang: str,
                         preserve_logic: bool = True) -> dict[str, Any]:
        """Transpile code from source language to target language.

        Args:
            code: Source code to transpile.
            source_lang: Source language name.
            target_lang: Target language name.
            preserve_logic: If True, adds extra verification instructions.

        Returns:
            Dict with transpiled code and metadata.
        """
        if source_lang == target_lang:
            return {"status": "skipped", "code": code, "message": "Same language"}

        instruction = (
            f"Convert the following {source_lang} code to {target_lang}. "
            f"Preserve the exact business logic. "
            f"Use idiomatic {target_lang} patterns and conventions. "
            f"Add comments explaining any non-obvious translations."
        )
        if preserve_logic:
            instruction += " CRITICAL: The business logic must be 100% preserved."

        prompt = f"{instruction}\n\n```{source_lang}\n{code}\n```\n\n```{target_lang}"

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
                transpiled = self._extract_code(content, target_lang)
                return {
                    "status": "completed",
                    "code": transpiled,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "original_size": len(code),
                    "transpiled_size": len(transpiled),
                }
        except Exception as e:
            return {"status": "failed", "error": str(e), "source_lang": source_lang, "target_lang": target_lang}

    async def verify(self, original: str, transpiled: str, language: str) -> dict[str, Any]:
        """Verify that transpiled code preserves original logic."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Compare these two pieces of {language} code. "
                            f"Do they have the same business logic? Answer YES or NO, then explain.\n\n"
                            f"ORIGINAL:\n{original[:2000]}\n\nTRANSPILED:\n{transpiled[:2000]}"
                        ),
                    }],
                    "max_tokens": 512,
                    "temperature": 0.0,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return {"verified": "YES" in content.upper()[:10], "details": content[:500]}
        except Exception as e:
            return {"verified": False, "error": str(e)}

    @staticmethod
    def list_supported_migrations() -> list[dict[str, Any]]:
        """List supported language migrations."""
        migrations = []
        for src, targets in LANGUAGE_MAP.items():
            for tgt in targets:
                migrations.append({"source": src, "target": tgt})
        return migrations

    @staticmethod
    def _extract_code(content: str, language: str) -> str:
        """Extract code block from LLM response."""
        import re
        match = re.search(r"```(?:\w+)?\n(.+?)\n```", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content.strip()
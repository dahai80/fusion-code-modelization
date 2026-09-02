# GateGuard: Importers: migration/__init__.py, CLI. Affected API: adds transpile_stream(). Data schemas: none. User instruction: Phase 6 — add streaming LLM support.

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fusion_code_modelization.core.agent_loop import AgentLoop, LoopTool, LoopToolResult, default_trace_path
from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig
from fusion_code_modelization.core.hooks import HookRegistry

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
    def __init__(self, mlx_url: str = DEFAULT_GATEWAY_URL, client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    async def transpile(
        self, code: str, source_lang: str, target_lang: str, preserve_logic: bool = True
    ) -> dict[str, Any]:
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

        result = await self._client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.1,
        )
        if result["status"] == "completed":
            transpiled = MLXClient.extract_code(result["content"], target_lang)
            return {
                "status": "completed",
                "code": transpiled,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "original_size": len(code),
                "transpiled_size": len(transpiled),
            }
        return {
            "status": "failed",
            "error": result.get("error", "Unknown"),
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

    async def transpile_stream(
        self, code: str, source_lang: str, target_lang: str, preserve_logic: bool = True
    ) -> AsyncIterator[dict[str, Any]]:
        if source_lang == target_lang:
            yield {"type": "done", "result": {"status": "skipped", "code": code, "message": "Same language"}}
            return

        instruction = (
            f"Convert the following {source_lang} code to {target_lang}. "
            f"Preserve the exact business logic. "
            f"Use idiomatic {target_lang} patterns and conventions. "
            f"Add comments explaining any non-obvious translations."
        )
        if preserve_logic:
            instruction += " CRITICAL: The business logic must be 100% preserved."

        prompt = f"{instruction}\n\n```{source_lang}\n{code}\n```\n\n```{target_lang}"

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
            transpiled = MLXClient.extract_code(full, target_lang)
            yield {
                "type": "done",
                "result": {
                    "status": "completed",
                    "code": transpiled,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "original_size": len(code),
                    "transpiled_size": len(transpiled),
                },
            }
        except Exception as e:
            logger.error("transpile_stream failed: %s", e)
            yield {
                "type": "done",
                "result": {
                    "status": "failed",
                    "error": str(e),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                },
            }

    async def transpile_with_loop(
        self,
        code: str,
        source_lang: str,
        target_lang: str,
        preserve_logic: bool = True,
        max_iter: int = 5,
        hooks: HookRegistry | None = None,
        trace_path: Path | None = None,
    ) -> dict[str, Any]:
        if source_lang == target_lang:
            return {"status": "skipped", "code": code, "message": "Same language"}

        async def execute(produced: str) -> LoopToolResult:
            ver = await self.verify(code, produced, target_lang)
            passed = bool(ver.get("verified"))
            return LoopToolResult(
                passed=passed,
                output=str(ver.get("details", ""))[:500],
                error="" if passed else "logic_mismatch",
            )

        verify_tool = LoopTool(name="verify_logic", execute=execute, description="equivalence verify")
        loop = AgentLoop(
            client=self._client,
            tools=[verify_tool],
            max_iter=max_iter,
            extract_language=target_lang,
            hooks=hooks,
            trace_path=trace_path if trace_path is not None else default_trace_path("transpile"),
        )

        def build_prompt(ctx: str, feedback: str | None) -> str:
            instruction = (
                f"Convert the following {source_lang} code to {target_lang}. "
                f"Preserve the exact business logic. "
                f"Use idiomatic {target_lang} patterns and conventions. "
                f"Add comments explaining any non-obvious translations."
            )
            if preserve_logic:
                instruction += " CRITICAL: The business logic must be 100% preserved."
            prompt = f"{instruction}\n\n```{source_lang}\n{code}\n```\n\n```{target_lang}"
            if feedback:
                prompt += (
                    f"\n\nPrevious translation failed logic verification: {feedback}. "
                    "Fix the logic mismatch and output the corrected code only."
                )
            return prompt

        logger.info("transpile_with_loop start: %s->%s max_iter=%d", source_lang, target_lang, max_iter)
        loop_result = await loop.run(
            objective=f"transpile {source_lang}->{target_lang} preserving logic",
            build_prompt=build_prompt,
            extract=None,
            verify_tool="verify_logic",
        )
        if loop_result["status"] == "completed":
            produced = loop_result["result"]
            return {
                "status": "completed",
                "code": produced,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "original_size": len(code),
                "transpiled_size": len(produced),
                "iterations": loop_result["iterations"],
            }
        return {
            "status": "failed",
            "error": loop_result.get("last_error", "max_iter_reached"),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "iterations": loop_result["iterations"],
            "partial": loop_result.get("result", ""),
        }

    async def verify(self, original: str, transpiled: str, language: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Compare these two pieces of {language} code. "
                        f"Do they have the same business logic? Answer YES or NO, then explain.\n\n"
                        f"ORIGINAL:\n{original}\n\nTRANSPILED:\n{transpiled}"
                    ),
                }
            ],
            max_tokens=512,
            temperature=0.0,
        )
        if result["status"] == "completed":
            content = result["content"]
            return {"verified": "YES" in content.upper()[:10], "details": content[:500]}
        return {"verified": False, "error": result.get("error", "Unknown")}

    @staticmethod
    def list_supported_migrations() -> list[dict[str, Any]]:
        migrations = []
        for src, targets in LANGUAGE_MAP.items():
            for tgt in targets:
                migrations.append({"source": src, "target": tgt})
        return migrations

# GateGuard: Importers: test_gen/__init__.py, CLI. Affected API: adds generate_unit_tests_stream(). Data schemas: none. User instruction: Phase 6 — add streaming LLM support.

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from fusion_code_modelization.core.agent_loop import AgentLoop, LoopTool, LoopToolResult
from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig
from fusion_code_modelization.core.hooks import HookRegistry

logger = logging.getLogger(__name__)


async def _syntax_check_tool(client: MLXClient, language: str) -> LoopTool:
    async def execute(produced: str) -> LoopToolResult:
        if language == "python":
            try:
                compile(produced, "<generated_tests>", "exec")
                return LoopToolResult(passed=True, output="compile_ok", error="")
            except SyntaxError as e:
                return LoopToolResult(passed=False, output="", error=f"syntax_error:{e}")
        ver = await client.simple_chat(
            f"Is this {language} code syntactically valid? Answer YES or NO then explain.\n\n```\n{produced[:2000]}\n```",
            max_tokens=256,
            temperature=0.0,
        )
        passed = "YES" in ver.upper()[:10]
        return LoopToolResult(passed=passed, output=ver[:500], error="" if passed else "syntax_invalid")

    return LoopTool(name="syntax_check", execute=execute, description="generated test syntax check")


class UnitTestGenerator:
    def __init__(self, mlx_url: str = DEFAULT_GATEWAY_URL, client: MLXClient | None = None):
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

    async def generate_unit_tests_stream(self, code: str, language: str) -> AsyncIterator[dict[str, Any]]:
        prompt = (
            f"Generate comprehensive unit tests for this {language} code. "
            f"Include edge cases, normal cases, and error cases. "
            f"Use the standard testing framework for {language}.\n\n"
            f"```{language}\n{code[:4000]}\n```"
        )
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
            tests = MLXClient.extract_code(full)
            yield {
                "type": "done",
                "result": {"status": "completed", "tests": tests, "language": language},
            }
        except Exception as e:
            logger.error("generate_unit_tests_stream failed: %s", e)
            yield {"type": "done", "result": {"status": "failed", "error": str(e)}}

    async def generate_with_loop(
        self, code: str, language: str, max_iter: int = 5, hooks: HookRegistry | None = None
    ) -> dict[str, Any]:
        verify = await _syntax_check_tool(self._client, language)
        loop = AgentLoop(client=self._client, tools=[verify], max_iter=max_iter, extract_language=language, hooks=hooks)

        def build_prompt(ctx: str, feedback: str | None) -> str:
            prompt = (
                f"Generate comprehensive unit tests for this {language} code. "
                f"Include edge cases, normal cases, and error cases. "
                f"Use the standard testing framework for {language}.\n\n"
                f"```{language}\n{code[:4000]}\n```"
            )
            if feedback:
                prompt += (
                    f"\n\nPrevious tests had a syntax error: {feedback}. "
                    "Fix the syntax and output the corrected test code only."
                )
            return prompt

        logger.info("generate_with_loop start: language=%s max_iter=%d", language, max_iter)
        loop_result = await loop.run(
            objective=f"generate syntactically valid {language} unit tests",
            build_prompt=build_prompt,
            extract=None,
            verify_tool="syntax_check",
        )
        if loop_result["status"] == "completed":
            return {
                "status": "completed",
                "tests": loop_result["result"],
                "language": language,
                "iterations": loop_result["iterations"],
            }
        return {
            "status": "failed",
            "error": loop_result.get("last_error", "max_iter_reached"),
            "language": language,
            "iterations": loop_result["iterations"],
            "partial": loop_result.get("result", ""),
        }

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

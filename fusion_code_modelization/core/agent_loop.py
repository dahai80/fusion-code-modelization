# GateGuard: New file. Importers: refactor/refactorer.py, migration/transpiler.py, test_gen/generator.py, cli/__init__.py, tests/test_agent_loop.py. Affected API: AgentLoop, LoopTool, LoopToolResult, LoopTrace. Data schemas: none. User instruction: M1 — Agent Loop execution engine, bounded + trace for auditability.

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from .client import MLXClient
from .hooks import HookAction, HookEvent, HookRegistry

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITER = 5
TRACE_DIR = Path.home() / ".fusion" / "code_mod" / "loop_trace"


class LoopStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    MAX_ITER = "max_iter_reached"
    HOOK_DENIED = "hook_denied"


@dataclass
class LoopToolResult:
    passed: bool
    output: str = ""
    error: str = ""


@dataclass
class LoopTool:
    name: str
    execute: Callable[..., Awaitable[LoopToolResult]]
    description: str = ""


@dataclass
class LoopTrace:
    iteration: int
    objective: str
    llm_response: str
    tool_name: str
    tool_passed: bool
    tool_output: str
    decision: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentLoop:
    client: MLXClient
    tools: list[LoopTool] = field(default_factory=list)
    max_iter: int = DEFAULT_MAX_ITER
    trace_path: Path | None = None
    extract_language: str = ""
    hooks: HookRegistry | None = None

    def add_tool(self, tool: LoopTool) -> None:
        self.tools.append(tool)
        logger.debug("AgentLoop registered tool: %s", tool.name)

    def _tool(self, name: str) -> LoopTool:
        for t in self.tools:
            if t.name == name:
                return t
        raise KeyError(f"loop tool not found: {name}")

    def _append_trace(self, trace: LoopTrace) -> None:
        if self.trace_path is None:
            return
        try:
            self.trace_path.parent.mkdir(parents=True, exist_ok=True)
            with self.trace_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("loop trace write failed: %s", e)

    async def run(
        self,
        objective: str,
        build_prompt: Callable[[str, str | None], str],
        extract: Callable[[str], str] | None = None,
        verify_tool: str | None = None,
        context: str = "",
    ) -> dict[str, Any]:
        if verify_tool is None and self.tools:
            verify_tool = self.tools[0].name
        last_output = ""
        last_error: str | None = None
        traces: list[LoopTrace] = []
        for i in range(1, self.max_iter + 1):
            feedback = last_error or ""
            prompt = build_prompt(context, feedback if i > 1 else None)
            result = await self.client.chat(messages=[{"role": "user", "content": prompt}])
            if result["status"] != "completed":
                logger.warning("loop iter %d LLM failed: %s", i, result.get("error"))
                last_error = result.get("error", "llm_failed")
                traces.append(
                    LoopTrace(
                        iteration=i,
                        objective=objective,
                        llm_response="",
                        tool_name="",
                        tool_passed=False,
                        tool_output="",
                        decision="llm_failed_retry",
                    )
                )
                continue
            raw = result["content"]
            if self.hooks is not None:
                hdecision = await self.hooks.emit(HookEvent.POST_LLM, {"content": raw, "objective": objective})
                if not hdecision.allowed:
                    logger.warning("loop iter %d hook denied POST_LLM: %s", i, hdecision.reason)
                    last_error = hdecision.reason
                    traces.append(
                        LoopTrace(
                            iteration=i,
                            objective=objective,
                            llm_response=raw[:500],
                            tool_name="",
                            tool_passed=False,
                            tool_output="",
                            decision="hook_denied",
                        )
                    )
                    continue
                if hdecision.action == HookAction.MODIFY and hdecision.modified_content is not None:
                    raw = hdecision.modified_content
            produced = extract(raw) if extract is not None else MLXClient.extract_code(raw, self.extract_language)
            last_output = produced
            tool_passed, tool_output, tool_error = True, "", ""
            if verify_tool is not None:
                if self.hooks is not None:
                    pdecision = await self.hooks.emit(
                        HookEvent.PRE_EXEC, {"content": produced, "tool": verify_tool, "objective": objective}
                    )
                    if not pdecision.allowed:
                        tool_passed = False
                        tool_error = f"hook_denied:{pdecision.reason}"
                        logger.warning("loop iter %d hook denied PRE_EXEC: %s", i, pdecision.reason)
                        traces.append(
                            LoopTrace(
                                iteration=i,
                                objective=objective,
                                llm_response=raw[:500],
                                tool_name=verify_tool,
                                tool_passed=False,
                                tool_output="",
                                decision="hook_denied",
                            )
                        )
                        last_error = tool_error
                        continue
                try:
                    tool = self._tool(verify_tool)
                    tr = await tool.execute(produced)
                    tool_passed = tr.passed
                    tool_output = tr.output
                    tool_error = tr.error
                except Exception as e:
                    tool_passed = False
                    tool_error = f"tool_exception:{e}"
                    logger.error("loop verify tool %s raised: %s", verify_tool, e)
            decision = "pass" if tool_passed else "retry_with_feedback"
            traces.append(
                LoopTrace(
                    iteration=i,
                    objective=objective,
                    llm_response=raw[:500],
                    tool_name=verify_tool or "",
                    tool_passed=tool_passed,
                    tool_output=(tool_output or tool_error)[:500],
                    decision=decision,
                )
            )
            if tool_passed:
                logger.info("loop passed at iter %d: %s", i, objective)
                for t in traces:
                    self._append_trace(t)
                return {
                    "status": LoopStatus.COMPLETED.value,
                    "result": produced,
                    "iterations": i,
                    "traces": [t.to_dict() for t in traces],
                }
            last_error = tool_error or tool_output or "verify_failed"
            logger.info("loop iter %d verify failed, retrying: %s", i, last_error[:200])
        for t in traces:
            self._append_trace(t)
        logger.warning("loop reached max_iter %d: %s", self.max_iter, objective)
        return {
            "status": LoopStatus.MAX_ITER.value,
            "result": last_output,
            "iterations": self.max_iter,
            "last_error": last_error,
            "traces": [t.to_dict() for t in traces],
        }

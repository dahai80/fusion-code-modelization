# GateGuard: New file. Importers: none (test). Affected API: none. Data schemas: none. User instruction: M1 — test Agent Loop execution engine.

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.core.agent_loop import AgentLoop, LoopTool, LoopToolResult
from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.migration.transpiler import CodeTranspiler
from fusion_code_modelization.refactor.refactorer import IncrementalRefactorer
from fusion_code_modelization.test_gen.generator import UnitTestGenerator

logger = logging.getLogger(__name__)


class TestAgentLoopCore:
    @pytest.mark.asyncio
    async def test_loop_pass_first_iter(self):
        client = MLXClient()
        loop = AgentLoop(
            client=client,
            tools=[LoopTool(name="v", execute=AsyncMock(return_value=LoopToolResult(passed=True, output="ok")))],
            max_iter=3,
        )
        with patch.object(
            client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "```python\nx=1\n```"})
        ):
            result = await loop.run(
                objective="test",
                build_prompt=lambda ctx, fb: "prompt",
                extract=None,
                verify_tool="v",
            )
        assert result["status"] == "completed"
        assert result["iterations"] == 1
        assert result["result"] == "x=1"

    @pytest.mark.asyncio
    async def test_loop_converges_after_retry(self):
        client = MLXClient()
        call_count = {"v": 0}

        async def execute(produced):
            call_count["v"] += 1
            passed = call_count["v"] >= 2
            return LoopToolResult(passed=passed, output="" if passed else "bad", error="" if passed else "fail")

        loop = AgentLoop(client=client, tools=[LoopTool(name="v", execute=execute)], max_iter=5)
        with patch.object(
            client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "```python\nx\n```"})
        ):
            result = await loop.run(objective="test", build_prompt=lambda ctx, fb: "p", verify_tool="v")
        assert result["status"] == "completed"
        assert result["iterations"] == 2
        assert len(result["traces"]) == 2
        assert result["traces"][0]["tool_passed"] is False
        assert result["traces"][1]["tool_passed"] is True

    @pytest.mark.asyncio
    async def test_loop_max_iter_reached(self):
        client = MLXClient()
        loop = AgentLoop(
            client=client,
            tools=[LoopTool(name="v", execute=AsyncMock(return_value=LoopToolResult(passed=False, error="nope")))],
            max_iter=2,
        )
        with patch.object(
            client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "```python\nx\n```"})
        ):
            result = await loop.run(objective="test", build_prompt=lambda ctx, fb: "p", verify_tool="v")
        assert result["status"] == "max_iter_reached"
        assert result["iterations"] == 2
        assert result["last_error"] == "nope"

    @pytest.mark.asyncio
    async def test_loop_llm_failure_retries(self):
        client = MLXClient()
        loop = AgentLoop(
            client=client,
            tools=[LoopTool(name="v", execute=AsyncMock(return_value=LoopToolResult(passed=True)))],
            max_iter=3,
        )
        chat = AsyncMock(
            side_effect=[
                {"status": "failed", "error": "empty_content"},
                {"status": "completed", "content": "```python\nok\n```"},
            ]
        )
        with patch.object(client, "chat", new=chat):
            result = await loop.run(objective="test", build_prompt=lambda ctx, fb: "p", verify_tool="v")
        assert result["status"] == "completed"
        assert result["iterations"] == 2
        assert result["traces"][0]["decision"] == "llm_failed_retry"

    @pytest.mark.asyncio
    async def test_loop_trace_written(self, tmp_path):
        client = MLXClient()
        trace_file = tmp_path / "trace.jsonl"
        loop = AgentLoop(
            client=client,
            tools=[LoopTool(name="v", execute=AsyncMock(return_value=LoopToolResult(passed=True)))],
            max_iter=2,
            trace_path=trace_file,
        )
        with patch.object(
            client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "```python\nx\n```"})
        ):
            await loop.run(objective="test", build_prompt=lambda ctx, fb: "p", verify_tool="v")
        assert trace_file.exists()
        lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert '"iteration": 1' in lines[0]


class TestRefactorWithLoop:
    @pytest.mark.asyncio
    async def test_refactor_loop_success(self):
        r = IncrementalRefactorer()
        refactored = "def foo():\n    x = 1\n    return x"
        chat = AsyncMock(return_value={"status": "completed", "content": f"```python\n{refactored}\n```"})
        simple = AsyncMock(return_value="YES they are equivalent")
        with patch.object(r._client, "chat", new=chat), patch.object(r._client, "simple_chat", new=simple):
            result = await r.refactor_with_loop("def foo():\n    x=1\n    return x", "python", max_iter=3)
        assert result["status"] == "completed"
        assert result["iterations"] == 1
        assert "x = 1" in result["result"]

    @pytest.mark.asyncio
    async def test_refactor_loop_retry_then_pass(self):
        r = IncrementalRefactorer()
        refactored = "def foo():\n    x = 1\n    return x"
        chat = AsyncMock(return_value={"status": "completed", "content": f"```python\n{refactored}\n```"})
        simple = AsyncMock(side_effect=["NO different behavior", "YES equivalent"])
        with patch.object(r._client, "chat", new=chat), patch.object(r._client, "simple_chat", new=simple):
            result = await r.refactor_with_loop("def foo():\n    x=1\n    return x", "python", max_iter=5)
        assert result["status"] == "completed"
        assert result["iterations"] == 2

    @pytest.mark.asyncio
    async def test_refactor_loop_max_iter(self):
        r = IncrementalRefactorer()
        chat = AsyncMock(return_value={"status": "completed", "content": "```python\nx\n```"})
        simple = AsyncMock(return_value="NO never equivalent")
        with patch.object(r._client, "chat", new=chat), patch.object(r._client, "simple_chat", new=simple):
            result = await r.refactor_with_loop("def foo():\n    pass", "python", max_iter=2)
        assert result["status"] == "max_iter_reached"
        assert result["iterations"] == 2


class TestTranspileWithLoop:
    @pytest.mark.asyncio
    async def test_transpile_loop_success(self):
        t = CodeTranspiler()
        transpiled = "func add(a, b int) int { return a + b }"
        chat = AsyncMock(return_value={"status": "completed", "content": f"```go\n{transpiled}\n```"})
        verify = AsyncMock(return_value={"verified": True, "details": "YES same"})
        with patch.object(t._client, "chat", new=chat), patch.object(t, "verify", new=verify):
            result = await t.transpile_with_loop("int add(int a, int b){return a+b;}", "java", "go", max_iter=3)
        assert result["status"] == "completed"
        assert result["iterations"] == 1
        assert "func add" in result["code"]

    @pytest.mark.asyncio
    async def test_transpile_loop_same_lang_skipped(self):
        t = CodeTranspiler()
        result = await t.transpile_with_loop("x=1", "python", "python", max_iter=3)
        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_transpile_loop_max_iter(self):
        t = CodeTranspiler()
        chat = AsyncMock(return_value={"status": "completed", "content": "```go\nx\n```"})
        verify = AsyncMock(return_value={"verified": False, "details": "NO"})
        with patch.object(t._client, "chat", new=chat), patch.object(t, "verify", new=verify):
            result = await t.transpile_with_loop("int x;", "java", "go", max_iter=2)
        assert result["status"] == "failed"
        assert result["iterations"] == 2


class TestTestGenWithLoop:
    @pytest.mark.asyncio
    async def test_generate_loop_python_compile_pass(self):
        g = UnitTestGenerator()
        valid_tests = "def test_foo():\n    assert 1 == 1\n"
        chat = AsyncMock(return_value={"status": "completed", "content": f"```python\n{valid_tests}\n```"})
        with patch.object(g._client, "chat", new=chat):
            result = await g.generate_with_loop("def foo(): return 1", "python", max_iter=3)
        assert result["status"] == "completed"
        assert result["iterations"] == 1
        assert "test_foo" in result["tests"]

    @pytest.mark.asyncio
    async def test_generate_loop_python_syntax_retry(self):
        g = UnitTestGenerator()
        bad = "def test_foo(:\n    assert 1"
        good = "def test_foo():\n    assert 1 == 1\n"
        chat = AsyncMock(
            side_effect=[
                {"status": "completed", "content": f"```python\n{bad}\n```"},
                {"status": "completed", "content": f"```python\n{good}\n```"},
            ]
        )
        with patch.object(g._client, "chat", new=chat):
            result = await g.generate_with_loop("def foo(): return 1", "python", max_iter=5)
        assert result["status"] == "completed"
        assert result["iterations"] == 2

    @pytest.mark.asyncio
    async def test_generate_loop_non_python_uses_llm_check(self):
        g = UnitTestGenerator()
        js_tests = "function testFoo() { assert(1 === 1); }"
        chat = AsyncMock(return_value={"status": "completed", "content": f"```javascript\n{js_tests}\n```"})
        simple = AsyncMock(return_value="YES valid javascript code")
        with patch.object(g._client, "chat", new=chat), patch.object(g._client, "simple_chat", new=simple):
            result = await g.generate_with_loop("function foo(){return 1;}", "javascript", max_iter=3)
        assert result["status"] == "completed"
        assert result["iterations"] == 1

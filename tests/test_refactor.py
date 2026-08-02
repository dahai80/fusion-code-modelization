from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.refactor.refactorer import IncrementalRefactorer

logger = logging.getLogger(__name__)


class TestIncrementalRefactorer:
    def test_init_default(self):
        r = IncrementalRefactorer()
        assert r._client is not None
        assert isinstance(r._client, MLXClient)

    def test_init_with_custom_url(self):
        r = IncrementalRefactorer(mlx_url="http://custom:9999/v1")
        assert r._client.config.base_url == "http://custom:9999/v1"

    def test_init_with_injected_client(self):
        client = MLXClient()
        r = IncrementalRefactorer(client=client)
        assert r._client is client

    @pytest.mark.asyncio
    async def test_refactor_success(self):
        r = IncrementalRefactorer()
        original = "def foo():\n    x=1\n    return x"
        refactored_code = "def foo():\n    x = 1\n    return x"
        mock_content = f"```python\n{refactored_code}\n```"
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": mock_content})
        ):
            result = await r.refactor(original, "python")
            assert result["status"] == "completed"
            assert result["original"] == original
            assert "refactored" in result
            assert "original_lines" in result
            assert "refactored_lines" in result
            assert result["original_lines"] == len(original.splitlines())

    @pytest.mark.asyncio
    async def test_refactor_success_with_instructions(self):
        r = IncrementalRefactorer()
        original = "def bar():\n    y=2"
        refactored_code = "def bar():\n    y = 2"
        mock_content = f"```python\n{refactored_code}\n```"
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": mock_content})
        ) as mock_chat:
            result = await r.refactor(original, "python", instructions="Add type hints")
            assert result["status"] == "completed"
            call_args = mock_chat.call_args
            prompt = call_args.kwargs.get("messages", call_args[0][0] if call_args[0] else [])[0]["content"]
            assert "Add type hints" in prompt

    @pytest.mark.asyncio
    async def test_refactor_failure(self):
        r = IncrementalRefactorer()
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "connection refused"})
        ):
            result = await r.refactor("x=1", "python")
            assert result["status"] == "failed"
            assert "error" in result
            assert result["error"] == "connection refused"

    @pytest.mark.asyncio
    async def test_refactor_line_counts(self):
        r = IncrementalRefactorer()
        original = "a=1\nb=2\nc=3"
        refactored_code = "a = 1\nb = 2\nc = 3"
        mock_content = f"```python\n{refactored_code}\n```"
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": mock_content})
        ):
            result = await r.refactor(original, "python")
            assert result["status"] == "completed"
            assert result["original_lines"] == 3
            assert result["refactored_lines"] == 3

    @pytest.mark.asyncio
    async def test_refactor_code_without_fences(self):
        r = IncrementalRefactorer()
        original = "x=1"
        plain_code = "x = 1"
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": plain_code})
        ):
            result = await r.refactor(original, "python")
            assert result["status"] == "completed"
            assert "refactored" in result

    @pytest.mark.asyncio
    async def test_dual_run_verify_yes(self):
        r = IncrementalRefactorer()
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "YES, same output"})
        ):
            result = await r.dual_run_verify("a", "a", "python")
            assert result["verified"] is True
            assert "details" in result

    @pytest.mark.asyncio
    async def test_dual_run_verify_identical(self):
        r = IncrementalRefactorer()
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "IDENTICAL behavior"})
        ):
            result = await r.dual_run_verify("x=1", "x = 1", "python")
            assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_dual_run_verify_same_keyword(self):
        r = IncrementalRefactorer()
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "SAME logic preserved"})
        ):
            result = await r.dual_run_verify("a", "b", "python")
            assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_dual_run_verify_no(self):
        r = IncrementalRefactorer()
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "NO, different behavior"})
        ):
            result = await r.dual_run_verify("a", "b", "python")
            assert result["verified"] is False

    @pytest.mark.asyncio
    async def test_dual_run_verify_failure(self):
        r = IncrementalRefactorer()
        with patch.object(r._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "timeout"})):
            result = await r.dual_run_verify("a", "b", "python")
            assert result["verified"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_dual_run_verify_details_truncated(self):
        r = IncrementalRefactorer()
        long_content = "YES, " + "x" * 600
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": long_content})
        ):
            result = await r.dual_run_verify("a", "b", "python")
            assert result["verified"] is True
            assert len(result["details"]) <= 500

    @pytest.mark.asyncio
    async def test_characterize_success(self):
        r = IncrementalRefactorer()
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "def test_foo(): pass"})
        ):
            result = await r.characterize("def foo(): pass", "python")
            assert result["status"] == "completed"
            assert result["tests"] == "def test_foo(): pass"
            assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_characterize_failure(self):
        r = IncrementalRefactorer()
        with patch.object(
            r._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "model unavailable"})
        ):
            result = await r.characterize("code", "java")
            assert result["status"] == "failed"
            assert result["error"] == "model unavailable"

    @pytest.mark.asyncio
    async def test_apply_refactoring_workflow(self):
        r = IncrementalRefactorer()
        original = "def add(a,b): return a+b"
        refactored_code = "def add(a: int, b: int) -> int:\n    return a + b"
        with patch.object(
            r._client,
            "chat",
            new=AsyncMock(
                side_effect=[
                    {"status": "completed", "content": f"```python\n{refactored_code}\n```"},
                    {"status": "completed", "content": "YES, same behavior"},
                ]
            ),
        ):
            refactor_result = await r.refactor(original, "python", instructions="Add type hints")
            assert refactor_result["status"] == "completed"
            verify_result = await r.dual_run_verify(original, refactor_result["refactored"], "python")
            assert verify_result["verified"] is True

    @pytest.mark.asyncio
    async def test_apply_refactoring_verification_fails(self):
        r = IncrementalRefactorer()
        original = "def add(a,b): return a+b"
        refactored_code = "def subtract(a, b): return a - b"
        with patch.object(
            r._client,
            "chat",
            new=AsyncMock(
                side_effect=[
                    {"status": "completed", "content": f"```python\n{refactored_code}\n```"},
                    {"status": "completed", "content": "NO, different outputs"},
                ]
            ),
        ):
            refactor_result = await r.refactor(original, "python")
            assert refactor_result["status"] == "completed"
            verify_result = await r.dual_run_verify(original, refactor_result["refactored"], "python")
            assert verify_result["verified"] is False

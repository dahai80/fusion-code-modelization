from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.migration.transpiler import LANGUAGE_MAP, CodeTranspiler

logger = logging.getLogger(__name__)


class TestCodeTranspiler:
    def setup_method(self):
        self.transpiler = CodeTranspiler(client=MLXClient())

    # ── transpile success ──

    @pytest.mark.asyncio
    async def test_transpile_success(self):
        llm_output = '```java\npublic class Hello {\n    public static void main(String[] args) {\n        System.out.println("hi");\n    }\n}\n```'
        mock_response = {"status": "completed", "content": llm_output}
        with patch.object(self.transpiler._client, "chat", new=AsyncMock(return_value=mock_response)):
            result = await self.transpiler.transpile(
                code='DISPLAY "hi".',
                source_lang="cobol",
                target_lang="java",
            )
            assert result["status"] == "completed"
            assert result["source_lang"] == "cobol"
            assert result["target_lang"] == "java"
            assert "Hello" in result["code"]
            assert result["original_size"] == len('DISPLAY "hi".')
            assert result["transpiled_size"] == len(result["code"])

    @pytest.mark.asyncio
    async def test_transpile_preserve_logic_flag(self):
        llm_output = '```go\nfunc main() {\n    fmt.Println("hi")\n}\n```'
        mock_response = {"status": "completed", "content": llm_output}
        with patch.object(self.transpiler._client, "chat", new=AsyncMock(return_value=mock_response)) as mock_chat:
            await self.transpiler.transpile(
                code='print("hi")',
                source_lang="python",
                target_lang="go",
                preserve_logic=True,
            )
            call_args = mock_chat.call_args
            prompt = call_args.kwargs["messages"][0]["content"]
            assert "CRITICAL" in prompt

    @pytest.mark.asyncio
    async def test_transpile_no_preserve_logic(self):
        llm_output = '```go\nfunc main() {\n    fmt.Println("hi")\n}\n```'
        mock_response = {"status": "completed", "content": llm_output}
        with patch.object(self.transpiler._client, "chat", new=AsyncMock(return_value=mock_response)) as mock_chat:
            await self.transpiler.transpile(
                code='print("hi")',
                source_lang="python",
                target_lang="go",
                preserve_logic=False,
            )
            call_args = mock_chat.call_args
            prompt = call_args.kwargs["messages"][0]["content"]
            assert "CRITICAL" not in prompt

    # ── transpile failure ──

    @pytest.mark.asyncio
    async def test_transpile_failure(self):
        mock_response = {"status": "failed", "error": "connection refused"}
        with patch.object(self.transpiler._client, "chat", new=AsyncMock(return_value=mock_response)):
            result = await self.transpiler.transpile(
                code="some code",
                source_lang="java",
                target_lang="go",
            )
            assert result["status"] == "failed"
            assert result["error"] == "connection refused"
            assert result["source_lang"] == "java"
            assert result["target_lang"] == "go"

    @pytest.mark.asyncio
    async def test_transpile_unknown_error(self):
        mock_response = {"status": "failed"}
        with patch.object(self.transpiler._client, "chat", new=AsyncMock(return_value=mock_response)):
            result = await self.transpiler.transpile(
                code="x = 1",
                source_lang="python",
                target_lang="go",
            )
            assert result["status"] == "failed"
            assert result["error"] == "Unknown"

    # ── same language skip ──

    @pytest.mark.asyncio
    async def test_transpile_same_language_skipped(self):
        result = await self.transpiler.transpile(
            code="x = 1",
            source_lang="python",
            target_lang="python",
        )
        assert result["status"] == "skipped"
        assert result["code"] == "x = 1"
        assert result["message"] == "Same language"

    # ── verify ──

    @pytest.mark.asyncio
    async def test_verify_yes(self):
        mock_response = {"status": "completed", "content": "YES, the logic is identical."}
        with patch.object(self.transpiler._client, "chat", new=AsyncMock(return_value=mock_response)):
            result = await self.transpiler.verify("original", "transpiled", "java")
            assert result["verified"] is True
            assert "identical" in result["details"]

    @pytest.mark.asyncio
    async def test_verify_no(self):
        mock_response = {"status": "completed", "content": "NO, the logic differs here."}
        with patch.object(self.transpiler._client, "chat", new=AsyncMock(return_value=mock_response)):
            result = await self.transpiler.verify("original", "transpiled", "java")
            assert result["verified"] is False

    @pytest.mark.asyncio
    async def test_verify_failure(self):
        mock_response = {"status": "failed", "error": "timeout"}
        with patch.object(self.transpiler._client, "chat", new=AsyncMock(return_value=mock_response)):
            result = await self.transpiler.verify("original", "transpiled", "java")
            assert result["verified"] is False
            assert result["error"] == "timeout"

    # ── supported language pairs ──

    def test_list_supported_migrations(self):
        migrations = CodeTranspiler.list_supported_migrations()
        assert len(migrations) > 0
        assert {"source": "cobol", "target": "java"} in migrations
        assert {"source": "python", "target": "go"} in migrations

    def test_language_map_structure(self):
        for src, targets in LANGUAGE_MAP.items():
            assert isinstance(src, str)
            assert isinstance(targets, list)
            assert src not in targets
            for tgt in targets:
                assert isinstance(tgt, str)

    def test_supported_source_languages(self):
        expected = {"cobol", "vb6", "java", "python", "javascript", "csharp"}
        assert set(LANGUAGE_MAP.keys()) == expected

    # ── extract_code parsing ──

    def test_extract_code_with_fence(self):
        content = 'Here is the result:\n```java\nSystem.out.println("hello");\n```\nDone.'
        result = MLXClient.extract_code(content, "java")
        assert 'System.out.println("hello")' in result
        assert "Here is" not in result

    def test_extract_code_no_fence(self):
        content = 'System.out.println("hello");'
        result = MLXClient.extract_code(content, "java")
        assert 'System.out.println("hello")' in result

    def test_extract_code_multiple_fences(self):
        content = "```python\nx = 1\n```\nSome text\n```java\ny = 2\n```"
        result = MLXClient.extract_code(content)
        assert "x = 1" in result

    # ── constructor ──

    def test_init_with_client(self):
        client = MLXClient()
        transpiler = CodeTranspiler(client=client)
        assert transpiler._client is client

    def test_init_default_url(self):
        transpiler = CodeTranspiler(mlx_url="http://custom:9999/v1")
        assert transpiler._client.config.base_url == "http://custom:9999/v1"

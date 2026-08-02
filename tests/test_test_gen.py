from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.test_gen.generator import UnitTestGenerator

logger = logging.getLogger(__name__)


class TestUnitTestGenerator:
    @pytest.mark.asyncio
    async def test_generate_unit_tests_success(self):
        g = UnitTestGenerator()
        mock_content = "```python\nimport pytest\n\ndef test_foo():\n    assert foo() == 1\n```"
        with patch.object(
            g._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": mock_content}),
        ):
            result = await g.generate_unit_tests("def foo(): return 1", "python")
            assert result["status"] == "completed"
            assert "tests" in result
            assert result["language"] == "python"
            assert "test_foo" in result["tests"]

    @pytest.mark.asyncio
    async def test_generate_unit_tests_failure(self):
        g = UnitTestGenerator()
        with patch.object(
            g._client,
            "chat",
            new=AsyncMock(return_value={"status": "failed", "error": "connection refused"}),
        ):
            result = await g.generate_unit_tests("def foo(): return 1", "python")
            assert result["status"] == "failed"
            assert "error" in result
            assert result["error"] == "connection refused"

    @pytest.mark.asyncio
    async def test_generate_unit_tests_no_code_fence(self):
        g = UnitTestGenerator()
        mock_content = "def test_bar():\n    assert True"
        with patch.object(
            g._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": mock_content}),
        ):
            result = await g.generate_unit_tests("x = 1", "python")
            assert result["status"] == "completed"
            assert result["tests"] == mock_content.strip()

    @pytest.mark.asyncio
    async def test_generate_unit_tests_java(self):
        g = UnitTestGenerator()
        mock_content = "```java\n@Test\npublic void testCalc() {\n    assertEquals(2, calc(1, 1));\n}\n```"
        with patch.object(
            g._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": mock_content}),
        ):
            result = await g.generate_unit_tests("public int calc(int a, int b) { return a + b; }", "java")
            assert result["status"] == "completed"
            assert result["language"] == "java"
            assert "testCalc" in result["tests"]

    @pytest.mark.asyncio
    async def test_generate_integration_tests_success(self):
        g = UnitTestGenerator()
        components = [
            {"name": "AuthService", "desc": "Handles user authentication"},
            {"name": "UserRepo", "desc": "Database operations for users"},
        ]
        mock_content = "Integration tests for AuthService and UserRepo data flow"
        with patch.object(
            g._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": mock_content}),
        ):
            result = await g.generate_integration_tests(components, "python")
            assert result["status"] == "completed"
            assert result["tests"] == mock_content
            assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_generate_integration_tests_failure(self):
        g = UnitTestGenerator()
        components = [{"name": "Svc", "desc": "A service"}]
        with patch.object(
            g._client,
            "chat",
            new=AsyncMock(return_value={"status": "failed", "error": "timeout"}),
        ):
            result = await g.generate_integration_tests(components, "java")
            assert result["status"] == "failed"
            assert result["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_generate_integration_tests_empty_components(self):
        g = UnitTestGenerator()
        mock_content = "Integration tests for components"
        with patch.object(
            g._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": mock_content}),
        ):
            result = await g.generate_integration_tests([], "python")
            assert result["status"] == "completed"
            assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_generate_integration_tests_missing_fields(self):
        g = UnitTestGenerator()
        components = [{"name": "Mod1"}, {"desc": "No name component"}]
        mock_content = "Integration tests output"
        with patch.object(
            g._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": mock_content}),
        ):
            result = await g.generate_integration_tests(components, "python")
            assert result["status"] == "completed"

    def test_init_default(self):
        g = UnitTestGenerator()
        assert g._client is not None

    def test_init_with_custom_url(self):
        g = UnitTestGenerator(mlx_url="http://custom:9999/v1")
        assert g._client is not None

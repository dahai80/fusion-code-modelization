from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.doc_gen import DocSection, DocumentationGenerator


class TestDocSection:
    def test_to_dict(self):
        s = DocSection(title="Intro", content="Hello", order=1)
        d = s.to_dict()
        assert d == {"title": "Intro", "content": "Hello", "order": 1}

    def test_defaults(self):
        s = DocSection(title="Test")
        assert s.content == ""
        assert s.order == 0


class TestDocumentationGenerator:
    @pytest.mark.asyncio
    async def test_generate_docs_success(self):
        gen = DocumentationGenerator()
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "# Module Docs\n\nDescription here"}),
        ):
            result = await gen.generate_docs("def foo(): pass", "python")
            assert result["status"] == "completed"
            assert "documentation" in result

    @pytest.mark.asyncio
    async def test_generate_docs_with_code_fence(self):
        gen = DocumentationGenerator()
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "```markdown\n# Docs\n\nSome content\n```"}),
        ):
            result = await gen.generate_docs("class Foo:", "python", doc_type="class")
            assert result["status"] == "completed"
            assert result["doc_type"] == "class"

    @pytest.mark.asyncio
    async def test_generate_docs_failure(self):
        gen = DocumentationGenerator()
        with patch.object(gen._client, "chat", new=AsyncMock(side_effect=Exception("connection error"))):
            result = await gen.generate_docs("code", "python")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_generate_api_docs_success(self):
        gen = DocumentationGenerator()
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "GET /api/health\n200 OK"}),
        ):
            result = await gen.generate_api_docs("from fastapi import FastAPI", "python")
            assert result["status"] == "completed"
            assert result["doc_type"] == "api"

    @pytest.mark.asyncio
    async def test_generate_api_docs_failure(self):
        gen = DocumentationGenerator()
        with patch.object(gen._client, "chat", new=AsyncMock(side_effect=Exception("timeout"))):
            result = await gen.generate_api_docs("code", "python")
            assert result["status"] == "failed"

    def test_build_readme(self):
        sections = [
            DocSection(title="Install", content="pip install x", order=2),
            DocSection(title="Intro", content="Welcome", order=1),
        ]
        readme = DocumentationGenerator.build_readme(sections)
        assert readme.index("## Intro") < readme.index("## Install")

    def test_build_readme_empty(self):
        readme = DocumentationGenerator.build_readme([])
        assert readme == ""

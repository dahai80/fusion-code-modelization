from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.pr_gen import BoundaryType, DocGenerator, MicroserviceDecomposer, PRGenerator

logger = logging.getLogger(__name__)


class TestPRGenerator:
    @pytest.mark.asyncio
    async def test_generate_pr_description_success(self):
        gen = PRGenerator()
        changes = [
            {"path": "src/main.py", "summary": "added feature X"},
            {"path": "src/utils.py", "summary": "refactored Y"},
        ]
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(
                return_value={"status": "completed", "content": "## Changes\n\nAdded feature X and refactored Y."}
            ),
        ):
            result = await gen.generate_pr_description(changes)
            assert result["description"] == "## Changes\n\nAdded feature X and refactored Y."
            assert "- src/main.py: added feature X" in result["summary"]
            assert "- src/utils.py: refactored Y" in result["summary"]

    @pytest.mark.asyncio
    async def test_generate_pr_description_fallback_on_failure(self):
        gen = PRGenerator()
        changes = [{"path": "src/app.py", "action": "deleted"}]
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(return_value={"status": "failed", "error": "model unavailable"}),
        ):
            result = await gen.generate_pr_description(changes)
            assert "error" in result
            assert result["error"] == "model unavailable"
            assert "src/app.py" in result["description"]

    @pytest.mark.asyncio
    async def test_generate_pr_description_empty_changes(self):
        gen = PRGenerator()
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "No changes."}),
        ):
            result = await gen.generate_pr_description([])
            assert result["description"] == "No changes."
            assert result["summary"] == ""

    @pytest.mark.asyncio
    async def test_generate_pr_description_uses_action_when_no_summary(self):
        gen = PRGenerator()
        changes = [{"path": "a.py", "action": "created"}]
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "PR body"}),
        ):
            result = await gen.generate_pr_description(changes)
            assert "- a.py: created" in result["summary"]


class TestDocGenerator:
    @pytest.mark.asyncio
    async def test_generate_migration_report(self):
        gen = DocGenerator()
        analysis = {"total_files": 10, "languages": ["COBOL", "Java"]}
        results = [
            {"file": "payroll.cbl", "status": "completed", "source_lang": "COBOL", "target_lang": "Java"},
            {"file": "report.cbl", "status": "failed", "source_lang": "COBOL", "target_lang": "Java"},
        ]
        report = await gen.generate_migration_report(analysis, results)
        assert "# Code Modernization Report" in report
        assert "Total files analyzed: 10" in report
        assert "Files migrated: 2" in report
        assert "payroll.cbl" in report
        assert "report.cbl" in report
        assert "COBOL" in report

    @pytest.mark.asyncio
    async def test_generate_migration_report_empty_results(self):
        gen = DocGenerator()
        analysis = {"total_files": 0, "languages": []}
        report = await gen.generate_migration_report(analysis, [])
        assert "Files migrated: 0" in report
        assert "Languages: []" in report

    @pytest.mark.asyncio
    async def test_generate_api_docs_success(self):
        gen = DocGenerator()
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "## API Reference\n\n### GET /health"}),
        ):
            result = await gen.generate_api_docs("from fastapi import FastAPI", "python")
            assert "## API Reference" in result
            assert "GET /health" in result

    @pytest.mark.asyncio
    async def test_generate_api_docs_failure(self):
        gen = DocGenerator()
        with patch.object(
            gen._client,
            "chat",
            new=AsyncMock(return_value={"status": "failed", "error": "timeout"}),
        ):
            result = await gen.generate_api_docs("code", "java")
            assert "Error generating docs" in result
            assert "timeout" in result


class TestMicroserviceDecomposer:
    def test_analyze_boundaries_microservice(self):
        decomposer = MicroserviceDecomposer()
        graph = {
            "nodes": {
                "auth/login.py": {},
                "auth/logout.py": {},
                "billing/invoice.py": {},
                "billing/payment.py": {},
                "utils.py": {},
            }
        }
        services = decomposer.analyze_boundaries(graph, BoundaryType.MICROSERVICE)
        names = {s["name"] for s in services}
        assert "auth" in names
        assert "billing" in names
        for s in services:
            assert s["boundary_type"] == BoundaryType.MICROSERVICE
            assert s["size"] >= 2

    def test_analyze_boundaries_module(self):
        decomposer = MicroserviceDecomposer()
        graph = {
            "nodes": {
                "auth/login.py": {},
                "auth/session/token.py": {},
                "billing/invoice.py": {},
            }
        }
        services = decomposer.analyze_boundaries(graph, BoundaryType.MODULE)
        names = {s["name"] for s in services}
        assert "auth/login.py" in names
        assert "auth/session" in names
        assert "billing/invoice.py" in names
        for s in services:
            assert s["boundary_type"] == BoundaryType.MODULE
            assert s["size"] >= 1

    def test_analyze_boundaries_package(self):
        decomposer = MicroserviceDecomposer()
        graph = {
            "nodes": {
                "auth/login.py": {},
                "billing/invoice.py": {},
                "utils.py": {},
            }
        }
        services = decomposer.analyze_boundaries(graph, BoundaryType.PACKAGE)
        names = {s["name"] for s in services}
        assert "auth" in names
        assert "billing" in names
        assert "utils.py" in names
        for s in services:
            assert s["boundary_type"] == BoundaryType.PACKAGE
            assert s["size"] >= 1

    def test_analyze_boundaries_empty_graph(self):
        decomposer = MicroserviceDecomposer()
        services = decomposer.analyze_boundaries({"nodes": {}}, BoundaryType.MICROSERVICE)
        assert services == []

    def test_analyze_boundaries_default_type(self):
        decomposer = MicroserviceDecomposer()
        graph = {
            "nodes": {
                "svc/a.py": {},
                "svc/b.py": {},
            }
        }
        services = decomposer.analyze_boundaries(graph)
        assert len(services) == 1
        assert services[0]["boundary_type"] == BoundaryType.MICROSERVICE

    @pytest.mark.asyncio
    async def test_suggest_decomposition_success(self):
        decomposer = MicroserviceDecomposer()
        with patch.object(
            decomposer._client,
            "chat",
            new=AsyncMock(
                return_value={"status": "completed", "content": "Split into Auth, Billing, and Notification services."}
            ),
        ):
            result = await decomposer.suggest_decomposition("class Auth: pass\nclass Billing: pass", "python")
            assert result["suggestions"] == "Split into Auth, Billing, and Notification services."
            assert result["language"] == "python"
            assert result["boundary_type"] == BoundaryType.MICROSERVICE

    @pytest.mark.asyncio
    async def test_suggest_decomposition_module_type(self):
        decomposer = MicroserviceDecomposer()
        with patch.object(
            decomposer._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "Organize into auth, billing modules."}),
        ):
            result = await decomposer.suggest_decomposition("code", "java", boundary_type=BoundaryType.MODULE)
            assert result["boundary_type"] == BoundaryType.MODULE
            assert "auth, billing modules" in result["suggestions"]

    @pytest.mark.asyncio
    async def test_suggest_decomposition_package_type(self):
        decomposer = MicroserviceDecomposer()
        with patch.object(
            decomposer._client,
            "chat",
            new=AsyncMock(
                return_value={"status": "completed", "content": "Use com.app.auth, com.app.billing packages."}
            ),
        ):
            result = await decomposer.suggest_decomposition("code", "java", boundary_type=BoundaryType.PACKAGE)
            assert result["boundary_type"] == BoundaryType.PACKAGE

    @pytest.mark.asyncio
    async def test_suggest_decomposition_failure(self):
        decomposer = MicroserviceDecomposer()
        with patch.object(
            decomposer._client,
            "chat",
            new=AsyncMock(return_value={"status": "failed", "error": "model overloaded"}),
        ):
            result = await decomposer.suggest_decomposition("code", "python")
            assert "error" in result
            assert result["error"] == "model overloaded"


class TestBoundaryType:
    def test_all_values(self):
        assert BoundaryType.MICROSERVICE == "microservice"
        assert BoundaryType.MODULE == "module"
        assert BoundaryType.PACKAGE == "package"

    def test_all_tuple(self):
        assert BoundaryType.ALL == ("microservice", "module", "package")
        assert len(BoundaryType.ALL) == 3

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.pipeline import AuditLog, PipelineIntegrator, PriorityScorer
from fusion_code_modelization.pr_gen import DocGenerator, MicroserviceDecomposer, PRGenerator

# ── AuditLog ──


class TestAuditLog:
    def test_defaults(self):
        log = AuditLog(action="refactor", module="core", file="main.py", status="success")
        assert log.action == "refactor"
        assert log.timestamp > 0


# ── PipelineIntegrator ──


class TestPipelineIntegrator:
    def test_create_pr_no_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pi = PipelineIntegrator(repo_path=tmpdir)
            with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
                result = pi.create_pr("branch", "title", "desc", [])
                assert "error" in result

    def test_generate_ci_config_python(self):
        pi = PipelineIntegrator()
        config = pi.generate_ci_config("python")
        assert "python" in config.get(".github/workflows/ci.yml", "")

    def test_generate_ci_config_java(self):
        pi = PipelineIntegrator()
        config = pi.generate_ci_config("java")
        assert "java" in config.get(".github/workflows/ci.yml", "")

    def test_generate_ci_config_go(self):
        pi = PipelineIntegrator()
        config = pi.generate_ci_config("go")
        assert "go" in config.get(".github/workflows/ci.yml", "")

    def test_audit_log(self):
        pi = PipelineIntegrator()
        pi._log("test", "core", "f.py", "success", "details")
        logs = pi.get_audit_log()
        assert len(logs) == 1
        assert logs[0]["action"] == "test"

    def test_export_audit_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pi = PipelineIntegrator()
            pi._log("test", "core", "f.py", "success")
            out = str(Path(tmpdir) / "audit.json")
            result = pi.export_audit_log(out)
            assert Path(out).exists()
            data = json.loads(result)
            assert len(data) == 1


# ── PriorityScorer ──


class TestPriorityScorer:
    def test_score_large_file(self):
        score = PriorityScorer.score_file({"size_bytes": 200000, "dependencies": [], "language": "python"})
        assert score["score"] >= 30
        assert score["priority"] in ("high", "medium")

    def test_score_legacy_language(self):
        score = PriorityScorer.score_file({"size_bytes": 1000, "dependencies": [], "language": "cobol"})
        assert score["score"] >= 40
        assert "legacy_cobol" in score["factors"]

    def test_score_dead_code(self):
        score = PriorityScorer.score_file(
            {"size_bytes": 1000, "dependencies": [], "language": "python", "is_dead": True}
        )
        assert score["score"] == 0
        assert score["priority"] == "low"

    def test_score_highly_dependent(self):
        score = PriorityScorer.score_file(
            {"size_bytes": 5000, "dependencies": [f"dep{i}" for i in range(15)], "language": "java"}
        )
        assert score["score"] >= 30
        assert "highly_dependent" in score["factors"]


# ── PRGenerator ──


class TestPRGenerator:
    @pytest.mark.asyncio
    async def test_generate_pr_description(self):
        prg = PRGenerator()
        with patch.object(
            prg._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "PR description here"})
        ):
            result = await prg.generate_pr_description(
                [{"path": "main.py", "action": "modified", "summary": "refactored"}]
            )
            assert "description" in result


# ── DocGenerator ──


class TestDocGenerator:
    @pytest.mark.asyncio
    async def test_generate_migration_report(self):
        dg = DocGenerator()
        analysis = {"total_files": 5, "languages": ["python"]}
        results = [{"file": "main.py", "status": "completed", "source_lang": "python", "target_lang": "go"}]
        report = await dg.generate_migration_report(analysis, results)
        assert "Code Modernization Report" in report
        assert "main.py" in report

    @pytest.mark.asyncio
    async def test_generate_api_docs(self):
        dg = DocGenerator()
        with patch.object(
            dg._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "API docs"})
        ):
            result = await dg.generate_api_docs("def foo(): pass", "python")
            assert "API docs" in result

    @pytest.mark.asyncio
    async def test_generate_api_docs_failure(self):
        dg = DocGenerator()
        with patch.object(dg._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "fail"})):
            result = await dg.generate_api_docs("code", "python")
            assert "Error" in result


# ── MicroserviceDecomposer ──


class TestMicroserviceDecomposer:
    def test_analyze_boundaries(self):
        md = MicroserviceDecomposer()
        graph = {
            "nodes": {
                "auth/login.py": {"path": "auth/login.py"},
                "auth/register.py": {"path": "auth/register.py"},
                "api/users.py": {"path": "api/users.py"},
                "api/roles.py": {"path": "api/roles.py"},
            }
        }
        services = md.analyze_boundaries(graph)
        assert len(services) >= 2
        names = [s["name"] for s in services]
        assert "auth" in names
        assert "api" in names

    @pytest.mark.asyncio
    async def test_suggest_decomposition(self):
        md = MicroserviceDecomposer()
        with patch.object(
            md._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "Split into 3 services"})
        ):
            result = await md.suggest_decomposition("class App {}", "java")
            assert "suggestions" in result

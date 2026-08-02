from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from fusion_code_modelization.pipeline import AuditLog, PipelineIntegrator, PriorityScorer

logger = logging.getLogger(__name__)


class TestAuditLog:
    def test_creation_defaults(self):
        log = AuditLog(action="create_pr", module="pipeline", file="main.py", status="success")
        assert log.action == "create_pr"
        assert log.module == "pipeline"
        assert log.file == "main.py"
        assert log.status == "success"
        assert log.details == ""
        assert log.timestamp > 0

    def test_creation_with_all_fields(self):
        log = AuditLog(
            action="transpile",
            module="migration",
            file="app.cobol",
            status="completed",
            timestamp=1700000000.0,
            details="converted to java",
        )
        assert log.timestamp == 1700000000.0
        assert log.details == "converted to java"

    def test_to_dict(self):
        log = AuditLog(
            action="scan",
            module="security",
            file="auth.py",
            status="failed",
            timestamp=1700000000.0,
            details="vulnerability found",
        )
        d = log.to_dict()
        assert d == {
            "action": "scan",
            "module": "security",
            "file": "auth.py",
            "status": "failed",
            "timestamp": 1700000000.0,
            "details": "vulnerability found",
        }

    def test_timestamp_auto_set(self):
        log = AuditLog(action="test", module="m", file="f", status="ok", timestamp=0.0)
        assert log.timestamp > 0

    def test_timestamp_preserved_when_provided(self):
        ts = 1234567890.0
        log = AuditLog(action="test", module="m", file="f", status="ok", timestamp=ts)
        assert log.timestamp == ts


class TestPipelineIntegrator:
    def test_init_default_path(self):
        integrator = PipelineIntegrator()
        assert integrator.repo_path == Path(".").expanduser().resolve()

    def test_init_custom_path(self):
        integrator = PipelineIntegrator(repo_path="/tmp/test-repo")
        assert integrator.repo_path == Path("/tmp/test-repo").expanduser().resolve()

    @patch("subprocess.run")
    def test_create_pr_success(self, mock_run):
        mock_run.return_value = MagicMock()
        integrator = PipelineIntegrator(repo_path="/tmp/test-repo")
        changes = [
            {"path": "src/main.py", "content": "print('hello')"},
            {"path": "src/utils.py", "content": "def util(): pass"},
        ]
        result = integrator.create_pr("feature-branch", "Add main", "New feature", changes)
        assert result["status"] == "created"
        assert result["branch"] == "feature-branch"
        assert result["title"] == "Add main"
        assert result["files_changed"] == 2
        assert mock_run.call_count == 4

    @patch("subprocess.run")
    def test_create_pr_with_delete(self, mock_run):
        mock_run.return_value = MagicMock()
        integrator = PipelineIntegrator(repo_path="/tmp/test-repo")
        with tempfile.TemporaryDirectory() as tmpdir:
            del_file = Path(tmpdir) / "old_file.py"
            del_file.write_text("old content", encoding="utf-8")
            integrator.repo_path = Path(tmpdir)
            changes = [{"path": "old_file.py", "action": "delete"}]
            result = integrator.create_pr("cleanup", "Remove old", "Cleanup", changes)
            assert result["status"] == "created"
            assert not del_file.exists()

    @patch("subprocess.run", side_effect=RuntimeError("git not found"))
    def test_create_pr_error(self, mock_run):
        integrator = PipelineIntegrator(repo_path="/tmp/test-repo")
        result = integrator.create_pr("branch", "Title", "Desc", [])
        assert result["status"] == "error"
        assert "git not found" in result["error"]

    def test_generate_ci_config_python(self):
        integrator = PipelineIntegrator()
        config = integrator.generate_ci_config("python")
        assert ".github/workflows/ci.yml" in config
        assert "pytest" in config[".github/workflows/ci.yml"]

    def test_generate_ci_config_java(self):
        integrator = PipelineIntegrator()
        config = integrator.generate_ci_config("java")
        assert "mvn test" in config[".github/workflows/ci.yml"]

    def test_generate_ci_config_go(self):
        integrator = PipelineIntegrator()
        config = integrator.generate_ci_config("go")
        assert "go test" in config[".github/workflows/ci.yml"]

    def test_generate_ci_config_unknown_defaults_python(self):
        integrator = PipelineIntegrator()
        config = integrator.generate_ci_config("rust")
        assert "pytest" in config[".github/workflows/ci.yml"]

    def test_get_audit_log_empty(self):
        integrator = PipelineIntegrator()
        logs = integrator.get_audit_log()
        assert logs == []

    @patch("subprocess.run")
    def test_get_audit_log_after_create_pr(self, mock_run):
        mock_run.return_value = MagicMock()
        integrator = PipelineIntegrator(repo_path="/tmp/test-repo")
        integrator.create_pr("b1", "t1", "d1", [])
        integrator.create_pr("b2", "t2", "d2", [])
        logs = integrator.get_audit_log()
        assert len(logs) == 2
        assert logs[0]["action"] == "create_pr"
        assert logs[0]["file"] == "b1"
        assert logs[1]["file"] == "b2"

    @patch("subprocess.run")
    def test_get_audit_log_limit(self, mock_run):
        mock_run.return_value = MagicMock()
        integrator = PipelineIntegrator(repo_path="/tmp/test-repo")
        for i in range(5):
            integrator.create_pr(f"b{i}", f"t{i}", f"d{i}", [])
        logs = integrator.get_audit_log(limit=2)
        assert len(logs) == 2
        assert logs[0]["file"] == "b3"
        assert logs[1]["file"] == "b4"

    def test_export_audit_log_no_path(self):
        integrator = PipelineIntegrator()
        output = integrator.export_audit_log()
        assert output == "[]"

    @patch("subprocess.run")
    def test_export_audit_log_with_file(self, mock_run):
        mock_run.return_value = MagicMock()
        integrator = PipelineIntegrator(repo_path="/tmp/test-repo")
        integrator.create_pr("b1", "t1", "d1", [])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name
        integrator.export_audit_log(output_path=output_path)
        data = json.loads(Path(output_path).read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["action"] == "create_pr"
        Path(output_path).unlink()

    @patch("subprocess.run")
    def test_create_pr_writes_files(self, mock_run):
        mock_run.return_value = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            integrator = PipelineIntegrator(repo_path=tmpdir)
            changes = [
                {"path": "src/new_file.py", "content": "print('new')"},
            ]
            integrator.create_pr("feature", "Add file", "Desc", changes)
            written = Path(tmpdir) / "src" / "new_file.py"
            assert written.exists()
            assert written.read_text(encoding="utf-8") == "print('new')"


class TestPriorityScorer:
    def test_score_small_file_no_deps(self):
        result = PriorityScorer.score_file({"size_bytes": 500, "dependencies": [], "language": "python"})
        assert result["score"] == 5
        assert result["priority"] == "low"
        assert result["factors"] == []

    def test_score_large_file(self):
        result = PriorityScorer.score_file({"size_bytes": 200000, "dependencies": [], "language": "python"})
        assert result["score"] >= 30
        assert "large_file" in result["factors"]

    def test_score_medium_file(self):
        result = PriorityScorer.score_file({"size_bytes": 50000, "dependencies": [], "language": "python"})
        assert "medium_file" in result["factors"]
        assert result["score"] >= 15

    def test_score_highly_dependent(self):
        result = PriorityScorer.score_file(
            {
                "size_bytes": 100,
                "dependencies": list(range(12)),
                "language": "python",
            }
        )
        assert "highly_dependent" in result["factors"]
        assert result["score"] >= 25

    def test_score_moderately_dependent(self):
        result = PriorityScorer.score_file(
            {
                "size_bytes": 100,
                "dependencies": list(range(7)),
                "language": "python",
            }
        )
        assert "moderately_dependent" in result["factors"]
        assert result["score"] >= 10

    def test_score_legacy_cobol(self):
        result = PriorityScorer.score_file({"size_bytes": 100, "dependencies": [], "language": "cobol"})
        assert "legacy_cobol" in result["factors"]
        assert result["score"] == 40
        assert result["priority"] == "medium"

    def test_score_legacy_vb6(self):
        result = PriorityScorer.score_file({"size_bytes": 100, "dependencies": [], "language": "vb6"})
        assert "legacy_vb6" in result["factors"]
        assert result["score"] >= 35

    def test_score_legacy_vba(self):
        result = PriorityScorer.score_file({"size_bytes": 100, "dependencies": [], "language": "vba"})
        assert "legacy_vba" in result["factors"]

    def test_score_legacy_cics(self):
        result = PriorityScorer.score_file({"size_bytes": 100, "dependencies": [], "language": "cics"})
        assert "legacy_cics" in result["factors"]

    def test_score_dead_code(self):
        result = PriorityScorer.score_file(
            {"size_bytes": 200000, "dependencies": list(range(12)), "language": "cobol", "is_dead": True}
        )
        assert "dead_code" in result["factors"]
        assert result["score"] == 45

    def test_score_dead_code_reduces_below_zero_clamps(self):
        result = PriorityScorer.score_file(
            {"size_bytes": 100, "dependencies": [], "language": "python", "is_dead": True}
        )
        assert result["score"] == 0

    def test_score_priority_high(self):
        result = PriorityScorer.score_file(
            {
                "size_bytes": 200000,
                "dependencies": list(range(12)),
                "language": "cobol",
            }
        )
        assert result["priority"] == "high"

    def test_score_priority_medium(self):
        result = PriorityScorer.score_file({"size_bytes": 50000, "dependencies": list(range(7)), "language": "python"})
        assert result["priority"] == "medium"

    def test_score_empty_input(self):
        result = PriorityScorer.score_file({})
        assert result["score"] == 5
        assert result["priority"] == "low"
        assert result["factors"] == []

    def test_score_is_static_method(self):
        assert isinstance(PriorityScorer.__dict__["score_file"], staticmethod)

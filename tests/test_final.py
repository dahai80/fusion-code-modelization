"""Final coverage push — targets pipeline remaining uncovered lines."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from fusion_code_modelization.pipeline import PipelineIntegrator, PriorityScorer


class TestPipelineFinal:
    def test_create_pr_with_git(self):
        """Test create_pr with a real git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Init a git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            Path(tmpdir, "README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir, capture_output=True)

            pi = PipelineIntegrator(repo_path=tmpdir)
            result = pi.create_pr(
                branch_name="refactor/test",
                title="Refactor main.py",
                description="Modernize codebase",
                changes=[{"path": "main.py", "content": "print('hello world')", "action": "add"}],
            )
            assert result["status"] == "created"
            assert result["files_changed"] == 1

    def test_create_pr_with_delete(self):
        """Test create_pr with a delete action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=tmpdir, capture_output=True)
            Path(tmpdir, "old.py").write_text("old code")
            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir, capture_output=True)

            pi = PipelineIntegrator(repo_path=tmpdir)
            result = pi.create_pr(
                branch_name="refactor/delete",
                title="Delete old file",
                description="Remove dead code",
                changes=[{"path": "old.py", "action": "delete"}],
            )
            assert result["status"] == "created"
            assert not Path(tmpdir, "old.py").exists()

    def test_priority_scorer_edge_cases(self):
        """Test priority scorer edge cases."""
        # Medium file with moderate deps
        score = PriorityScorer.score_file(
            {"size_bytes": 50000, "dependencies": [f"d{i}" for i in range(7)], "language": "java"}
        )
        assert score["score"] >= 20
        # Legacy language with no deps
        score = PriorityScorer.score_file({"size_bytes": 100, "dependencies": [], "language": "cobol"})
        assert score["score"] >= 40
        # Small file with no deps, unknown language
        score = PriorityScorer.score_file({"size_bytes": 50, "dependencies": [], "language": "unknown"})
        assert score["score"] >= 5

    def test_audit_log_persistence(self):
        """Test audit log with multiple entries."""
        pi = PipelineIntegrator()
        for i in range(5):
            pi._log(f"action_{i}", "module", "file.py", "success", f"details_{i}")
        logs = pi.get_audit_log(limit=100)
        assert len(logs) == 5
        assert logs[0]["action"] == "action_0"
        assert logs[-1]["action"] == "action_4"

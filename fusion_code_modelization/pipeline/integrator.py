# GateGuard: New file. Importers: pipeline/__init__.py, main __init__.py, tests. Affected API: none (PipelineIntegrator extracted from __init__.py). Data schemas: none. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..trace import ArtifactType, RelationshipType, TraceTracker
from .models import AuditLog

logger = logging.getLogger(__name__)


class PipelineIntegrator:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).expanduser().resolve()
        self._audit_logs: list[AuditLog] = []

    def create_pr(self, branch_name: str, title: str, description: str, changes: list[dict]) -> dict[str, Any]:
        import subprocess

        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo_path,
                capture_output=True,
                timeout=10,
            )
            for change in changes:
                file_path = self.repo_path / change["path"]
                if change.get("action") == "delete":
                    if file_path.exists():
                        file_path.unlink()
                else:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(change["content"], encoding="utf-8")
                subprocess.run(
                    ["git", "add", change["path"]],
                    cwd=self.repo_path,
                    capture_output=True,
                    timeout=10,
                )
            subprocess.run(
                ["git", "commit", "-m", title, "-m", description],
                cwd=self.repo_path,
                capture_output=True,
                timeout=10,
            )
            pr_info = {
                "branch": branch_name,
                "title": title,
                "description": description,
                "files_changed": len(changes),
                "status": "created",
            }
            self._log("create_pr", "pipeline", branch_name, "success", str(pr_info))
            return pr_info
        except Exception as e:
            self._log("create_pr", "pipeline", branch_name, "failed", str(e))
            return {"status": "error", "error": str(e)}

    def generate_ci_config(self, language: str) -> dict[str, str]:
        configs = {
            "python": {
                ".github/workflows/ci.yml": (
                    "name: CI\non: [push, pull_request]\njobs:\n  test:\n"
                    "    runs-on: ubuntu-latest\n    steps:\n"
                    "      - uses: actions/checkout@v3\n"
                    "      - uses: actions/setup-python@v4\n"
                    "        with:\n          python-version: '3.12'\n"
                    "      - run: pip install -e .[test]\n"
                    "      - run: pytest tests/\n"
                ),
            },
            "java": {
                ".github/workflows/ci.yml": (
                    "name: CI\non: [push, pull_request]\njobs:\n  test:\n"
                    "    runs-on: ubuntu-latest\n    steps:\n"
                    "      - uses: actions/checkout@v3\n"
                    "      - uses: actions/setup-java@v3\n"
                    "        with:\n          java-version: '17'\n"
                    "      - run: mvn test\n"
                ),
            },
            "go": {
                ".github/workflows/ci.yml": (
                    "name: CI\non: [push, pull_request]\njobs:\n  test:\n"
                    "    runs-on: ubuntu-latest\n    steps:\n"
                    "      - uses: actions/checkout@v3\n"
                    "      - uses: actions/setup-go@v4\n"
                    "        with:\n          go-version: '1.22'\n"
                    "      - run: go test ./...\n"
                ),
            },
        }
        return configs.get(language, configs["python"])

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._audit_logs[-limit:]]

    def export_audit_log(self, output_path: str = "") -> str:
        data = self.get_audit_log(limit=1000)
        output = json.dumps(data, indent=2, ensure_ascii=False)
        if output_path:
            Path(output_path).write_text(output, encoding="utf-8")
        return output

    def _log(self, action: str, module: str, file: str, status: str, details: str = "") -> None:
        self._audit_logs.append(AuditLog(action=action, module=module, file=file, status=status, details=details))

    def trace_artifact(
        self, artifact_type: str, artifact_id: str, name: str, metadata: dict | None = None
    ) -> str | None:
        tracker = self._get_trace_tracker()
        if not tracker:
            return None
        try:
            at = ArtifactType(artifact_type)
        except ValueError:
            logger.warning("unknown artifact type: %s", artifact_type)
            return None
        node = tracker.create_node(at, artifact_id, name, metadata or {})
        logger.info("traced artifact: %s (%s) -> node %s", name, artifact_type, node.node_id)
        return node.node_id

    def link_artifacts(
        self, source_id: str, target_id: str, relationship: str, metadata: dict | None = None
    ) -> str | None:
        tracker = self._get_trace_tracker()
        if not tracker:
            return None
        try:
            rel = RelationshipType(relationship)
        except ValueError:
            logger.warning("unknown relationship type: %s", relationship)
            return None
        edge = tracker.link_nodes(source_id, target_id, rel, metadata or {})
        logger.info("linked %s -> %s via %s", source_id, target_id, relationship)
        return edge.edge_id if edge else None

    def get_trace_forward(self, artifact_id: str, max_depth: int = 10) -> dict | None:
        tracker = self._get_trace_tracker()
        if not tracker:
            return None
        chain = tracker.trace_forward(artifact_id, max_depth)
        return chain.to_dict() if chain else None

    def get_trace_backward(self, artifact_id: str, max_depth: int = 10) -> dict | None:
        tracker = self._get_trace_tracker()
        if not tracker:
            return None
        chain = tracker.trace_backward(artifact_id, max_depth)
        return chain.to_dict() if chain else None

    def _get_trace_tracker(self) -> TraceTracker | None:
        if not hasattr(self, "_trace_tracker"):
            try:
                self._trace_tracker = TraceTracker(store_dir=str(self.repo_path / ".fusion" / "trace"))
            except Exception as e:
                logger.warning("failed to init trace tracker: %s", e)
                self._trace_tracker = None
        return self._trace_tracker

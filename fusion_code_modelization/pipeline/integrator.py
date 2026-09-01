# GateGuard: New file. Importers: pipeline/__init__.py, main __init__.py, tests. Affected API: none (PipelineIntegrator extracted from __init__.py). Data schemas: none. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast

from ..core.hooks import HookEvent, HookRegistry
from ..core.safe_writer import SafeWriter, UnsafePathError
from ..trace import ArtifactType, RelationshipType, TraceStore, TraceTracker
from .models import AuditLog

logger = logging.getLogger(__name__)


class PipelineIntegrator:
    def __init__(self, repo_path: str = ".", hooks: HookRegistry | None = None):
        self.repo_path = Path(repo_path).expanduser().resolve()
        self._audit_logs: list[AuditLog] = []
        self._hooks = hooks
        self._writer = SafeWriter(self.repo_path, registry=hooks)
        self._trace_tracker: TraceTracker | None = None

    def _check_exec(self, command: list[str]) -> bool:
        import inspect

        if self._hooks is None or not self._hooks.enabled:
            return True
        payload = {"event": HookEvent.PRE_EXEC.value, "command": " ".join(command)}
        for handler in self._hooks.handlers.get(HookEvent.PRE_EXEC, []):
            try:
                decision = handler.execute(payload)
                if inspect.isawaitable(decision):
                    logger.debug("skipping async PRE_EXEC handler: %s", handler.name)
                    cast("Any", decision).close()
                    continue
            except Exception as e:
                logger.error("PRE_EXEC hook %s raised: %s", handler.name, e)
                return False
            if not decision.allowed:
                logger.warning("PRE_EXEC denied %s: %s", command, decision.reason)
                return False
        return True

    def _emit_post_exec(self, command: list[str], succeeded: bool, details: str = "") -> None:
        import inspect

        if self._hooks is None or not self._hooks.enabled:
            return
        payload = {
            "event": HookEvent.POST_EXEC.value,
            "command": " ".join(command),
            "succeeded": succeeded,
            "details": details,
        }
        for handler in self._hooks.handlers.get(HookEvent.POST_EXEC, []):
            try:
                decision = handler.execute(payload)
                if inspect.isawaitable(decision):
                    logger.debug("skipping async POST_EXEC handler: %s", handler.name)
                    cast("Any", decision).close()
                    continue
            except Exception as e:
                logger.error("POST_EXEC hook %s raised: %s", handler.name, e)

    def _run(self, command: list[str]) -> Any:
        import subprocess

        if not self._check_exec(command):
            raise UnsafePathError(f"pre_exec denied: {' '.join(command)}")
        result = subprocess.run(
            command,
            cwd=self.repo_path,
            capture_output=True,
            timeout=10,
        )
        self._emit_post_exec(
            command,
            succeeded=result.returncode == 0,
            details=f"rc={result.returncode}",
        )
        return result

    def create_pr(self, branch_name: str, title: str, description: str, changes: list[dict]) -> dict[str, Any]:
        try:
            self._run(["git", "checkout", "-b", branch_name])
            for change in changes:
                rel = change["path"]
                try:
                    if change.get("action") == "delete":
                        self._writer.unlink(rel)
                    else:
                        self._writer.write_text(rel, change.get("content", ""))
                except UnsafePathError as e:
                    self._log("create_pr", "pipeline", rel, "denied", str(e))
                    logger.error("create_pr blocked unsafe path: %s", e)
                    return {"status": "error", "error": str(e)}
                self._run(["git", "add", "--", rel])
            self._run(["git", "commit", "-m", title, "-m", description])
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
            export_writer = SafeWriter(self.repo_path, registry=self._writer.registry, strict=False)
            try:
                export_writer.write_text(output_path, output)
            except UnsafePathError as e:
                logger.error("export_audit_log blocked unsafe path: %s", e)
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
        try:
            node = tracker.create_node(at, artifact_id, name, metadata or {})
        except Exception as e:
            logger.warning("trace create_node failed (pipeline continues): %s", e)
            return None
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
        try:
            edge = tracker.link_nodes(source_id, target_id, rel, metadata or {})
        except Exception as e:
            logger.warning("trace link_nodes failed (pipeline continues): %s", e)
            return None
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
        if self._trace_tracker is None:
            try:
                self._trace_tracker = TraceTracker(
                    store=TraceStore(store_dir=str(self.repo_path / ".fusion" / "trace"))
                )
            except Exception as e:
                logger.warning("failed to init trace tracker: %s", e)
                self._trace_tracker = None
        return self._trace_tracker

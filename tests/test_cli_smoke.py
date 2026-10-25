from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.cli import main

ALL_SUBCOMMANDS = [
    "analyze",
    "transpile",
    "refactor",
    "test-gen",
    "security",
    "session",
    "snapshot",
    "workflow",
    "memory",
    "sandbox",
    "decompose",
    "doc-gen",
    "audit",
    "cluster",
    "plugin",
    "benchmark",
    "loadbalancer",
    "offline",
    "trace",
    "agent-comm",
    "version",
    "serve",
]


def _run_cli(monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["fusion-code-modelization"] + argv)
    try:
        main()
    except SystemExit as e:
        return int(e.code or 0)
    return 0


@pytest.fixture
def smoke_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "proj"
    project.mkdir()
    (project / "sample.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    empty = tmp_path / "empty.py"
    empty.write_text("", encoding="utf-8")
    llm_response = {"status": "failed", "error": "smoke_test_no_llm"}
    with patch(
        "fusion_code_modelization.core.client.MLXClient.chat",
        new=AsyncMock(return_value=llm_response),
    ):
        yield {"tmp": tmp_path, "project": project, "empty": empty}


class TestCliHelpSmoke:
    @pytest.mark.parametrize("cmd", ALL_SUBCOMMANDS)
    def test_help_exits_zero(self, smoke_env, monkeypatch, cmd):
        assert _run_cli(monkeypatch, [cmd, "--help"]) == 0


class TestCliInvocationSmoke:
    def test_analyze(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["analyze", str(smoke_env["project"])]) == 0

    def test_transpile_empty_input(self, smoke_env, monkeypatch):
        assert (
            _run_cli(
                monkeypatch,
                ["transpile", str(smoke_env["empty"]), "--from", "python", "--to", "go"],
            )
            == 0
        )

    def test_refactor_empty_input(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["refactor", str(smoke_env["empty"])]) == 0

    def test_test_gen_empty_input(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["test-gen", str(smoke_env["empty"])]) == 0

    def test_security_empty_input(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["security", str(smoke_env["empty"])]) == 0

    def test_session_list(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["session", "list"]) == 0

    def test_snapshot_create_list(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["snapshot", "create", "--project-dir", str(smoke_env["project"])]) == 0
        assert _run_cli(monkeypatch, ["snapshot", "list", "--project-dir", str(smoke_env["project"])]) == 0

    def test_workflow_decompose(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["workflow", "decompose", "--description", "demo task"]) == 0

    def test_memory_init_list_load(self, smoke_env, monkeypatch):
        pd = str(smoke_env["project"])
        assert _run_cli(monkeypatch, ["memory", "init", "--project-dir", pd]) == 0
        assert _run_cli(monkeypatch, ["memory", "list", "--project-dir", pd]) == 0
        assert _run_cli(monkeypatch, ["memory", "load", "--project-dir", pd]) == 0

    def test_sandbox_check_allowed_exits_zero(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["sandbox", "check", "--path", str(smoke_env["project"] / "sample.py")]) == 0

    def test_sandbox_check_denied_exits_nonzero(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["sandbox", "check", "--path", str(smoke_env["project"] / ".env")]) != 0

    def test_decompose_static(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["decompose", str(smoke_env["project"])]) == 0

    def test_doc_gen_empty_input(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["doc-gen", str(smoke_env["empty"])]) == 0

    def test_audit_log(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["audit", "log", "--action-type", "custom", "--severity", "info"]) == 0

    def test_cluster_status(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["cluster", "status"]) == 0

    def test_plugin_status(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["plugin", "status"]) == 0

    def test_benchmark_list_and_run(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["benchmark", "list"]) == 0
        assert (
            _run_cli(
                monkeypatch,
                ["benchmark", "run", "--suite", "migration_quality", "--path", str(smoke_env["project"])],
            )
            == 0
        )

    def test_loadbalancer_overview_rebalance(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["loadbalancer", "overview"]) == 0
        assert _run_cli(monkeypatch, ["loadbalancer", "rebalance"]) == 0

    def test_offline_capabilities(self, smoke_env, monkeypatch):
        from fusion_code_modelization.offline import OfflineManager, OfflineMode

        with patch.object(OfflineManager, "detect_mode", return_value=OfflineMode.FULL_OFFLINE):
            assert _run_cli(monkeypatch, ["offline", "capabilities", "--mode", "full_offline"]) == 0

    def test_trace_create(self, smoke_env, monkeypatch):
        assert (
            _run_cli(
                monkeypatch,
                ["trace", "create", "--artifact-type", "code_change", "--artifact-id", "smoke-1", "--name", "smoke"],
            )
            == 0
        )

    def test_agent_comm_create(self, smoke_env, monkeypatch):
        assert (
            _run_cli(
                monkeypatch,
                ["agent-comm", "create", "--description", "demo", "--agents", "a1,a2"],
            )
            == 0
        )

    def test_version(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["version"]) == 0

    def test_serve_help_only(self, smoke_env, monkeypatch):
        assert _run_cli(monkeypatch, ["serve", "--help"]) == 0


class TestGrepGate:
    def test_no_check_path_call_on_sandbox_guard(self):
        cli_src = Path("fusion_code_modelization/cli/__init__.py").read_text(encoding="utf-8")
        assert "guard.check_path" not in cli_src

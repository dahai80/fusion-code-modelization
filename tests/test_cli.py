from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fusion_code_modelization.cli import VERSION, main

logger = logging.getLogger(__name__)


def _run_cli(*args):
    with patch("sys.argv", ["fusion-code-modelization"] + list(args)):
        main()


class TestCLI:
    def test_version(self, capsys):
        _run_cli("version")
        out = capsys.readouterr().out
        assert f"Fusion-Code-Modelization v{VERSION}" in out
        assert "fusion-mlx" in out

    def test_analyze(self, capsys, tmp_path):
        fake_graph = MagicMock()
        fake_graph.nodes = ["a", "b"]
        fake_graph.edges = [("a", "b")]
        fake_debt = {"total_hours": 10.0, "items": []}
        fake_report = "ANALYSIS REPORT"

        with patch("fusion_code_modelization.analyzer.dependency.DependencyAnalyzer") as MockAnalyzer:
            inst = MockAnalyzer.return_value
            inst.scan_directory.return_value = fake_graph
            inst.estimate_tech_debt.return_value = fake_debt
            inst.generate_report.return_value = fake_report
            _run_cli("analyze", str(tmp_path))

        out = capsys.readouterr().out
        assert "ANALYSIS REPORT" in out
        MockAnalyzer.return_value.scan_directory.assert_called_once_with(str(tmp_path))

    def test_analyze_with_output(self, capsys, tmp_path):
        fake_graph = MagicMock()
        fake_debt = {"total_hours": 0}
        out_file = tmp_path / "report.txt"

        with patch("fusion_code_modelization.analyzer.dependency.DependencyAnalyzer") as MockAnalyzer:
            inst = MockAnalyzer.return_value
            inst.scan_directory.return_value = fake_graph
            inst.estimate_tech_debt.return_value = fake_debt
            inst.generate_report.return_value = "REPORT"
            _run_cli("analyze", str(tmp_path), "--output", str(out_file))

        assert out_file.exists()
        assert out_file.read_text() == "REPORT"

    def test_transpile(self, capsys, tmp_path):
        src = tmp_path / "src.cob"
        src.write_text("MOVE A TO B")

        with patch("fusion_code_modelization.migration.transpiler.CodeTranspiler") as MockTranspiler:
            inst = MockTranspiler.return_value
            inst.transpile = AsyncMock(return_value={"status": "completed", "code": "class Main {}"})
            _run_cli(
                "transpile",
                str(src),
                "--from",
                "cobol",
                "--to",
                "java",
            )

        out = capsys.readouterr().out
        assert "class Main {}" in out

    def test_transpile_failure(self, capsys, tmp_path):
        src = tmp_path / "src.cob"
        src.write_text("MOVE A TO B")

        with patch("fusion_code_modelization.migration.transpiler.CodeTranspiler") as MockTranspiler:
            inst = MockTranspiler.return_value
            inst.transpile = AsyncMock(return_value={"status": "failed", "error": "bad code"})
            _run_cli(
                "transpile",
                str(src),
                "--from",
                "cobol",
                "--to",
                "java",
            )

        out = capsys.readouterr().out
        assert "bad code" in out

    def test_refactor(self, capsys, tmp_path):
        src = tmp_path / "main.py"
        src.write_text("def foo(): pass")

        with patch("fusion_code_modelization.refactor.refactorer.IncrementalRefactorer") as MockRefactorer:
            inst = MockRefactorer.return_value
            inst.refactor = AsyncMock(return_value={"status": "completed", "refactored": "def foo():\n    pass"})
            _run_cli("refactor", str(src), "--instructions", "add type hints")

        out = capsys.readouterr().out
        assert "def foo" in out

    def test_refactor_failure(self, capsys, tmp_path):
        src = tmp_path / "main.py"
        src.write_text("def foo(): pass")

        with patch("fusion_code_modelization.refactor.refactorer.IncrementalRefactorer") as MockRefactorer:
            inst = MockRefactorer.return_value
            inst.refactor = AsyncMock(return_value={"status": "failed", "error": "parse error"})
            _run_cli("refactor", str(src))

        out = capsys.readouterr().out
        assert "parse error" in out

    def test_test_gen(self, capsys, tmp_path):
        src = tmp_path / "calc.py"
        src.write_text("def add(a, b): return a + b")

        with patch("fusion_code_modelization.test_gen.generator.UnitTestGenerator") as MockGenerator:
            inst = MockGenerator.return_value
            inst.generate_unit_tests = AsyncMock(return_value={"status": "completed", "tests": "def test_add(): ..."})
            _run_cli("test-gen", str(src), "--language", "python")

        out = capsys.readouterr().out
        assert "def test_add" in out

    def test_test_gen_failure(self, capsys, tmp_path):
        src = tmp_path / "calc.py"
        src.write_text("def add(a, b): return a + b")

        with patch("fusion_code_modelization.test_gen.generator.UnitTestGenerator") as MockGenerator:
            inst = MockGenerator.return_value
            inst.generate_unit_tests = AsyncMock(return_value={"status": "failed", "error": "timeout"})
            _run_cli("test-gen", str(src))

        out = capsys.readouterr().out
        assert "timeout" in out

    def test_security(self, capsys, tmp_path):
        src = tmp_path / "app.py"
        src.write_text("password = 'hardcoded'")

        with patch("fusion_code_modelization.security.scanner.SecurityScanner") as MockScanner:
            inst = MockScanner.return_value
            inst.scan = AsyncMock(
                return_value={
                    "status": "completed",
                    "total_findings": 2,
                    "findings": [
                        {"severity": "high", "line": 1, "description": "eval usage"},
                        {"severity": "medium", "line": 5, "description": "hardcoded secret"},
                    ],
                }
            )
            _run_cli("security", str(src), "--language", "python")

        out = capsys.readouterr().out
        assert "2 issue(s)" in out
        assert "eval usage" in out

    def test_benchmark_list(self, capsys):
        fake_suite = MagicMock()
        fake_suite.items = [MagicMock(), MagicMock()]
        fake_suite.category = MagicMock(value="code_quality")

        with patch("fusion_code_modelization.benchmark.BenchmarkRunner") as MockRunner:
            inst = MockRunner.return_value
            inst.list_suites.return_value = ["suite_a"]
            inst.get_suite.return_value = fake_suite
            _run_cli("benchmark", "list")

        out = capsys.readouterr().out
        assert "suite_a" in out

    def test_benchmark_run(self, capsys):
        fake_result = MagicMock()
        fake_result.status = MagicMock(value="passed")
        fake_result.item_id = "item_1"
        fake_result.score = 85.0
        fake_result.target_score = 100.0

        fake_report = MagicMock()
        fake_report.report_id = "rpt-001"
        fake_report.passed_count = 1
        fake_report.failed_count = 0
        fake_report.skipped_count = 0
        fake_report.average_score = 85.0
        fake_report.results = [fake_result]

        with patch("fusion_code_modelization.benchmark.BenchmarkRunner") as MockRunner:
            inst = MockRunner.return_value
            inst.run_suite.return_value = fake_report
            _run_cli("benchmark", "run", "--suite", "suite_a")

        out = capsys.readouterr().out
        assert "rpt-001" in out
        assert "85.0%" in out

    def test_loadbalancer_overview(self, capsys):
        with (
            patch("fusion_code_modelization.loadbalancer.LoadBalancer") as MockLB,
            patch("fusion_code_modelization.loadbalancer.BalancerConfig") as MockConfig,
            patch("fusion_code_modelization.loadbalancer.LoadBalanceStrategy") as MockStrategy,
        ):
            MockStrategy.return_value = MagicMock()
            MockConfig.return_value = MagicMock()
            inst = MockLB.return_value
            inst.get_cluster_overview.return_value = {"nodes": 3, "total_tasks": 10}
            _run_cli("loadbalancer", "overview")

        out = capsys.readouterr().out
        assert "nodes" in out

    def test_loadbalancer_rebalance(self, capsys):
        with (
            patch("fusion_code_modelization.loadbalancer.LoadBalancer") as MockLB,
            patch("fusion_code_modelization.loadbalancer.BalancerConfig") as MockConfig,
            patch("fusion_code_modelization.loadbalancer.LoadBalanceStrategy") as MockStrategy,
        ):
            MockStrategy.return_value = MagicMock()
            MockConfig.return_value = MagicMock()
            inst = MockLB.return_value
            inst.rebalance.return_value = [
                {
                    "overloaded_node": "n1",
                    "underloaded_node": "n2",
                    "tasks_to_move": 2,
                }
            ]
            _run_cli("loadbalancer", "rebalance")

        out = capsys.readouterr().out
        assert "n1" in out
        assert "n2" in out

    def test_offline_detect(self, capsys):
        with patch("fusion_code_modelization.offline.OfflineManager") as MockMgr:
            inst = MockMgr.return_value
            inst.detect_mode.return_value = MagicMock(value="online")
            _run_cli("offline", "detect")

        out = capsys.readouterr().out
        assert "online" in out

    def test_offline_capabilities(self, capsys):
        cap1 = "transpile"
        cap2 = "analyze"

        with patch("fusion_code_modelization.offline.OfflineManager") as MockMgr:
            inst = MockMgr.return_value
            inst.get_available_capabilities.return_value = [cap1, cap2]
            _run_cli("offline", "capabilities")

        out = capsys.readouterr().out
        assert "transpile" in out
        assert "2" in out

    def test_trace_create(self, capsys):
        fake_node = MagicMock()
        fake_node.node_id = "node-1"
        fake_node.artifact_type = MagicMock(value="source")

        with patch("fusion_code_modelization.trace.TraceTracker") as MockTracker:
            inst = MockTracker.return_value
            inst.create_node.return_value = fake_node
            _run_cli(
                "trace",
                "create",
                "--artifact-type",
                "source",
                "--artifact-id",
                "main.py",
            )

        out = capsys.readouterr().out
        assert "node-1" in out

    def test_trace_forward(self, capsys):
        fake_chain = MagicMock()
        fake_chain.nodes = [MagicMock(node_id="n1", artifact_type=MagicMock(value="source"), name="main.py")]
        fake_chain.edges = []
        fake_chain.depth = 1

        with patch("fusion_code_modelization.trace.TraceTracker") as MockTracker:
            inst = MockTracker.return_value
            inst.trace_forward.return_value = fake_chain
            _run_cli("trace", "forward", "--artifact-id", "main.py")

        out = capsys.readouterr().out
        assert "Forward trace" in out

    def test_agent_comm_create(self, capsys):
        fake_task = MagicMock()
        fake_task.collaboration_id = "collab-1"
        fake_task.channel_name = "ch-1"
        fake_task.agent_ids = ["agent-a", "agent-b"]

        with patch("fusion_code_modelization.agent_comm.CollaborationCoordinator") as MockCoord:
            inst = MockCoord.return_value
            inst.create_collaboration.return_value = fake_task
            _run_cli(
                "agent-comm",
                "create",
                "--description",
                "test task",
                "--agents",
                "agent-a,agent-b",
            )

        out = capsys.readouterr().out
        assert "collab-1" in out

    def test_agent_comm_list(self, capsys):
        fake_task = MagicMock()
        fake_task.collaboration_id = "collab-1"
        fake_task.status = MagicMock(value="active")
        fake_task.task_description = "test description here"

        with patch("fusion_code_modelization.agent_comm.CollaborationCoordinator") as MockCoord:
            inst = MockCoord.return_value
            inst.list_tasks.return_value = [fake_task]
            _run_cli("agent-comm", "list")

        out = capsys.readouterr().out
        assert "collab-1" in out

    def test_invalid_subcommand_exits(self):
        with patch("sys.argv", ["fusion-code-modelization"]), pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_analyze_uses_mlx_url(self, tmp_path):
        with patch("fusion_code_modelization.analyzer.dependency.DependencyAnalyzer") as MockAnalyzer:
            inst = MockAnalyzer.return_value
            inst.scan_directory.return_value = MagicMock()
            inst.estimate_tech_debt.return_value = {}
            inst.generate_report.return_value = "OK"
            _run_cli("--mlx-url", "http://custom:9999/v1", "analyze", str(tmp_path))

        MockAnalyzer.assert_called_once_with(mlx_url="http://custom:9999/v1")

    def test_transpile_with_output(self, capsys, tmp_path):
        src = tmp_path / "src.vb"
        src.write_text("Dim x As Integer")
        out_file = tmp_path / "out.cs"

        with patch("fusion_code_modelization.migration.transpiler.CodeTranspiler") as MockTranspiler:
            inst = MockTranspiler.return_value
            inst.transpile = AsyncMock(return_value={"status": "completed", "code": "int x;"})
            _run_cli(
                "transpile",
                str(src),
                "--from",
                "vb6",
                "--to",
                "csharp",
                "--output",
                str(out_file),
            )

        assert out_file.exists()
        assert out_file.read_text() == "int x;"

    def test_refactor_with_output(self, capsys, tmp_path):
        src = tmp_path / "main.py"
        src.write_text("def foo(): pass")
        out_file = tmp_path / "out.py"

        with patch("fusion_code_modelization.refactor.refactorer.IncrementalRefactorer") as MockRefactorer:
            inst = MockRefactorer.return_value
            inst.refactor = AsyncMock(return_value={"status": "completed", "refactored": "def foo() -> None: pass"})
            _run_cli(
                "refactor",
                str(src),
                "--output",
                str(out_file),
            )

        assert out_file.exists()
        assert "-> None" in out_file.read_text()

    def test_test_gen_with_output(self, capsys, tmp_path):
        src = tmp_path / "calc.py"
        src.write_text("def add(a, b): return a + b")
        out_file = tmp_path / "test_calc.py"

        with patch("fusion_code_modelization.test_gen.generator.UnitTestGenerator") as MockGenerator:
            inst = MockGenerator.return_value
            inst.generate_unit_tests = AsyncMock(
                return_value={"status": "completed", "tests": "def test_add(): assert add(1,2)==3"}
            )
            _run_cli(
                "test-gen",
                str(src),
                "--language",
                "python",
                "--output",
                str(out_file),
            )

        assert out_file.exists()
        assert "test_add" in out_file.read_text()

    def test_security_with_output(self, capsys, tmp_path):
        src = tmp_path / "app.py"
        src.write_text("password = 'hardcoded'")
        out_file = tmp_path / "security.json"

        scan_result = {
            "status": "completed",
            "total_findings": 1,
            "findings": [{"severity": "critical", "line": 1, "description": "hardcoded password"}],
        }

        with patch("fusion_code_modelization.security.scanner.SecurityScanner") as MockScanner:
            inst = MockScanner.return_value
            inst.scan = AsyncMock(return_value=scan_result)
            _run_cli(
                "security",
                str(src),
                "--language",
                "python",
                "--output",
                str(out_file),
            )

        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["total_findings"] == 1

    def test_loadbalancer_predict(self, capsys):
        with (
            patch("fusion_code_modelization.loadbalancer.LoadBalancer") as MockLB,
            patch("fusion_code_modelization.loadbalancer.BalancerConfig") as MockConfig,
            patch("fusion_code_modelization.loadbalancer.LoadBalanceStrategy") as MockStrategy,
        ):
            MockStrategy.return_value = MagicMock()
            MockConfig.return_value = MagicMock()
            inst = MockLB.return_value
            inst.predict_capacity.return_value = {
                "current_utilization": 0.6,
                "predicted_peak": 0.85,
            }
            _run_cli("loadbalancer", "predict", "--duration-hours", "2.5")

        out = capsys.readouterr().out
        assert "current_utilization" in out
        inst.predict_capacity.assert_called_once_with(duration_hours=2.5)

    def test_loadbalancer_select(self, capsys):
        fake_decision = MagicMock()
        fake_decision.selected_node = "node-2"
        fake_decision.strategy = MagicMock(value="least_loaded")
        fake_decision.reason = "lowest load score"

        with (
            patch("fusion_code_modelization.loadbalancer.LoadBalancer") as MockLB,
            patch("fusion_code_modelization.loadbalancer.BalancerConfig") as MockConfig,
            patch("fusion_code_modelization.loadbalancer.LoadBalanceStrategy") as MockStrategy,
        ):
            MockStrategy.return_value = MagicMock()
            MockConfig.return_value = MagicMock()
            inst = MockLB.return_value
            inst.select_node.return_value = fake_decision
            _run_cli("loadbalancer", "select", "--session-id", "sess-1")

        out = capsys.readouterr().out
        assert "node-2" in out
        assert "least_loaded" in out

    def test_offline_prepare(self, capsys, tmp_path):
        fake_pkg = {
            "status": "completed",
            "package_id": "pkg-001",
            "mode": "full_offline",
            "size_mb": 512.3,
            "model_count": 2,
            "plugin_count": 0,
        }

        with (
            patch("fusion_code_modelization.offline.OfflineManager") as MockMgr,
            patch("fusion_code_modelization.offline.OfflineMode") as MockMode,
        ):
            MockMode.return_value = MagicMock()
            inst = MockMgr.return_value
            inst.prepare_offline_package.return_value = fake_pkg
            _run_cli(
                "offline",
                "prepare",
                "--mode",
                "full_offline",
                "--package-dir",
                str(tmp_path),
                "--model-ids",
                "model-a,model-b",
            )

        out = capsys.readouterr().out
        assert "pkg-001" in out
        assert "512.3" in out

    def test_trace_report(self, capsys):
        fake_report = MagicMock()
        fake_report.to_markdown.return_value = "# Trace Report\n\nSummary here"

        with patch("fusion_code_modelization.trace.TraceTracker") as MockTracker:
            inst = MockTracker.return_value
            inst.generate_report.return_value = fake_report
            _run_cli("trace", "report")

        out = capsys.readouterr().out
        assert "Trace Report" in out

    def test_agent_comm_submit(self, capsys):
        with patch("fusion_code_modelization.agent_comm.CollaborationCoordinator") as MockCoord:
            inst = MockCoord.return_value
            inst.submit_result.return_value = True
            _run_cli(
                "agent-comm",
                "submit",
                "--collab-id",
                "c-1",
                "--agent-id",
                "a-1",
            )

        out = capsys.readouterr().out
        assert "succeeded" in out

    def test_agent_comm_complete(self, capsys):
        with patch("fusion_code_modelization.agent_comm.CollaborationCoordinator") as MockCoord:
            inst = MockCoord.return_value
            inst.complete_collaboration.return_value = True
            _run_cli(
                "agent-comm",
                "complete",
                "--collab-id",
                "c-1",
            )

        out = capsys.readouterr().out
        assert "succeeded" in out

    def test_benchmark_compare(self, capsys):
        with patch("fusion_code_modelization.benchmark.BenchmarkRunner") as MockRunner:
            inst = MockRunner.return_value
            inst.compare_reports.return_value = {
                "regressions": [],
                "improvements": ["item_1"],
                "unchanged": ["item_2"],
            }
            _run_cli(
                "benchmark",
                "compare",
                "--report-a",
                "r1",
                "--report-b",
                "r2",
            )

        out = capsys.readouterr().out
        assert "Regressions" in out
        assert "Improvements" in out

    def test_benchmark_history(self, capsys):
        with patch("fusion_code_modelization.benchmark.BenchmarkRunner") as MockRunner:
            inst = MockRunner.return_value
            inst.get_historical_trends.return_value = [
                {"report_id": "r1", "average_score": 80.0, "passed_count": 5},
            ]
            _run_cli(
                "benchmark",
                "history",
                "--suite",
                "suite_a",
                "--limit",
                "5",
            )

        out = capsys.readouterr().out
        assert "r1" in out
        assert "80.0%" in out

# Integration tests — cross-module interaction
# pipeline traceability + benchmark scoring + loadbalancer+cluster + offline+core + agent_comm+cluster

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


class TestPipelineTraceability:
    def test_pipeline_audit_log_traceable(self):
        from fusion_code_modelization.pipeline import AuditLog, PipelineIntegrator

        integrator = PipelineIntegrator()
        log = integrator.get_audit_log()
        assert isinstance(log, list)
        audit = AuditLog(action="create_pr", module="pipeline", file="test.py", status="success")
        audit_dict = audit.to_dict()
        assert audit_dict["action"] == "create_pr"
        assert audit_dict["module"] == "pipeline"
        assert audit_dict["file"] == "test.py"
        assert audit_dict["status"] == "success"
        assert "timestamp" in audit_dict

    def test_pipeline_trace_forward_backward(self):
        from fusion_code_modelization.pipeline import PipelineIntegrator
        from fusion_code_modelization.trace import TraceStore, TraceTracker

        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=tmp)
            tracker = TraceTracker(store=store)
            integrator = PipelineIntegrator(repo_path=tmp)
            integrator._trace_tracker = tracker
            src_node_id = integrator.trace_artifact("code_change", "src-001", "app.py")
            test_node_id = integrator.trace_artifact("test_result", "test-001", "test_app.py")
            result = integrator.link_artifacts(source_id=src_node_id, target_id=test_node_id, relationship="tests")
            assert result is not None
            fwd = integrator.get_trace_forward("src-001")
            assert fwd is not None
            bwd = integrator.get_trace_backward("test-001")
            assert bwd is not None


class TestBenchmarkScoring:
    def test_benchmark_suite_run_and_score(self):
        from fusion_code_modelization.benchmark import BenchmarkRunner

        runner = BenchmarkRunner()
        suites = runner.list_suites()
        assert isinstance(suites, list)
        if suites:
            suite = runner.get_suite(suites[0])
            assert suite is not None
            report = runner.run_suite(suites[0], score_fn={})
            assert report.report_id
            assert report.avg_score >= 0

    def test_benchmark_compare_reports(self):
        from fusion_code_modelization.benchmark import BenchmarkRunner

        runner = BenchmarkRunner()
        suites = runner.list_suites()
        if not suites:
            pytest.skip("No benchmark suites")
        report_a = runner.run_suite(suites[0], score_fn={})
        report_b = runner.run_suite(suites[0], score_fn={})
        comparison = runner.compare_reports(report_a, report_b)
        assert "regressions" in comparison
        assert "improvements" in comparison
        assert "unchanged" in comparison


class TestLoadBalancerClusterIntegration:
    def test_lb_select_from_cluster_nodes(self):
        from fusion_code_modelization.cluster import ClusterScheduler, NodeInfo
        from fusion_code_modelization.loadbalancer import BalancerConfig, LoadBalancer, LoadBalanceStrategy

        scheduler = ClusterScheduler()
        node = NodeInfo(node_id="node-1", host="localhost", port=11434)
        scheduler.register_node(node)

        config = BalancerConfig(strategy=LoadBalanceStrategy.LEAST_LOADED)
        lb = LoadBalancer(config=config)
        decision = lb.select_node(session_id="sess-001")
        assert decision is not None

    def test_lb_rebalance_after_cluster_register(self):
        from fusion_code_modelization.cluster import ClusterScheduler, NodeInfo
        from fusion_code_modelization.loadbalancer import BalancerConfig, LoadBalancer, LoadBalanceStrategy

        scheduler = ClusterScheduler()
        for i in range(3):
            node = NodeInfo(node_id=f"node-{i}", host="localhost", port=11434 + i)
            scheduler.register_node(node)

        config = BalancerConfig(strategy=LoadBalanceStrategy.ROUND_ROBIN)
        lb = LoadBalancer(config=config)
        suggestions = lb.rebalance()
        assert isinstance(suggestions, list)


class TestOfflineCoreIntegration:
    def test_offline_detect_mode(self):
        from fusion_code_modelization.offline import OfflineManager

        mgr = OfflineManager()
        mode = mgr.detect_mode()
        assert mode.value in ("full_offline", "semi_offline", "online")

    def test_offline_capabilities_list(self):
        from fusion_code_modelization.offline import OfflineManager

        mgr = OfflineManager()
        caps = mgr.get_available_capabilities()
        assert isinstance(caps, list)
        assert len(caps) > 0


class TestAgentCommClusterIntegration:
    def test_agent_comm_with_cluster_register(self):
        from fusion_code_modelization.agent_comm import CollaborationCoordinator
        from fusion_code_modelization.cluster import ClusterScheduler, NodeInfo

        scheduler = ClusterScheduler()
        node = NodeInfo(node_id="agent-node-1", host="10.0.0.1", port=11434)
        scheduler.register_node(node)

        coordinator = CollaborationCoordinator()
        task = coordinator.create_collaboration("Distributed code analysis", ["agent-1", "agent-2"])
        assert task.collaboration_id
        assert len(task.agent_ids) == 2
        assert task.status.value in ("active", "pending")

    def test_agent_comm_submit_and_complete(self):
        from fusion_code_modelization.agent_comm import CollaborationCoordinator

        coordinator = CollaborationCoordinator()
        task = coordinator.create_collaboration("Test task", ["agent-a"])
        collab_id = task.collaboration_id
        ok = coordinator.submit_result(collab_id, "agent-a", {"result": "done"})
        assert ok
        ok = coordinator.complete_collaboration(collab_id)
        assert ok


class TestCrossModuleWorkflow:
    def test_analyze_to_decompose_pipeline(self):
        from fusion_code_modelization.analyzer.dependency import DependencyAnalyzer
        from fusion_code_modelization.decompose import BoundaryDetector

        analyzer = DependencyAnalyzer()
        with tempfile.TemporaryDirectory() as tmp:
            for name in ["mod_a.py", "mod_b.py", "mod_c.py"]:
                Path(tmp, name).write_text(f"# {name}\nimport os\n")
            graph = analyzer.scan_directory(tmp)
            graph_dict = {"nodes": graph.nodes, "edges": graph.edges}
            detector = BoundaryDetector()
            suggestions = detector.detect_boundaries_static(graph_dict)
            assert isinstance(suggestions, list)

    def test_pipeline_scorer_integrator(self):
        from fusion_code_modelization.pipeline import PipelineIntegrator, PriorityScorer

        result = PriorityScorer.score_file(
            {
                "size_bytes": 50000,
                "language": "cobol",
                "is_dead": False,
                "dependencies": list(range(10)),
            }
        )
        assert result["score"] > 0
        integrator = PipelineIntegrator()
        ci = integrator.generate_ci_config("python")
        assert "python" in json.dumps(ci)

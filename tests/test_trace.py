from __future__ import annotations

import tempfile

from fusion_code_modelization.trace.models import (
    ArtifactType,
    RelationshipType,
    TraceEdge,
    TraceNode,
    TraceReport,
)
from fusion_code_modelization.trace.store import TraceStore
from fusion_code_modelization.trace.tracker import TraceTracker


class TestArtifactType:
    def test_enum_values(self):
        assert ArtifactType.REQUIREMENT.value == "requirement"
        assert ArtifactType.CODE_CHANGE.value == "code_change"
        assert ArtifactType.TEST_RESULT.value == "test_result"
        assert ArtifactType.DEPLOYMENT.value == "deployment"
        assert ArtifactType.REVIEW.value == "review"
        assert ArtifactType.MIGRATION.value == "migration"
        assert ArtifactType.SECURITY_SCAN.value == "security_scan"
        assert ArtifactType.BENCHMARK.value == "benchmark"
        assert len(ArtifactType) == 8


class TestRelationshipType:
    def test_enum_values(self):
        assert RelationshipType.DERIVED_FROM.value == "derived_from"
        assert RelationshipType.IMPLEMENTS.value == "implements"
        assert RelationshipType.TESTS.value == "tests"
        assert RelationshipType.DEPENDS_ON.value == "depends_on"
        assert RelationshipType.GENERATES.value == "generates"
        assert RelationshipType.MIGRATES_TO.value == "migrates_to"
        assert RelationshipType.REVIEWS.value == "reviews"
        assert RelationshipType.SUPERSEDES.value == "supersedes"
        assert len(RelationshipType) == 8


class TestTraceNode:
    def test_to_dict(self):
        node = TraceNode(
            artifact_type=ArtifactType.CODE_CHANGE,
            artifact_id="feat-123",
            name="add-login",
        )
        d = node.to_dict()
        assert d["artifact_type"] == "code_change"
        assert d["artifact_id"] == "feat-123"
        assert d["name"] == "add-login"
        assert "node_id" in d

    def test_from_dict_roundtrip(self):
        node = TraceNode(
            artifact_type=ArtifactType.REQUIREMENT,
            artifact_id="req-1",
            name="auth requirement",
            metadata={"priority": "high"},
        )
        d = node.to_dict()
        restored = TraceNode.from_dict(d)
        assert restored.node_id == node.node_id
        assert restored.artifact_type == node.artifact_type
        assert restored.artifact_id == node.artifact_id
        assert restored.name == node.name
        assert restored.metadata == {"priority": "high"}


class TestTraceEdge:
    def test_to_dict(self):
        edge = TraceEdge(
            source_id="n1",
            target_id="n2",
            relationship=RelationshipType.IMPLEMENTS,
        )
        d = edge.to_dict()
        assert d["source_id"] == "n1"
        assert d["target_id"] == "n2"
        assert d["relationship"] == "implements"

    def test_from_dict_roundtrip(self):
        edge = TraceEdge(
            source_id="s1",
            target_id="t1",
            relationship=RelationshipType.TESTS,
            metadata={"suite": "unit"},
        )
        d = edge.to_dict()
        restored = TraceEdge.from_dict(d)
        assert restored.edge_id == edge.edge_id
        assert restored.source_id == edge.source_id
        assert restored.target_id == edge.target_id
        assert restored.relationship == RelationshipType.TESTS
        assert restored.metadata == {"suite": "unit"}


class TestTraceStore:
    def test_add_node_and_get_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=tmp)
            node = TraceNode(artifact_type=ArtifactType.REQUIREMENT, artifact_id="r1")
            store.add_node(node)
            got = store.get_node(node.node_id)
            assert got is not None
            assert got.artifact_id == "r1"

    def test_add_edge_and_get_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=tmp)
            n1 = TraceNode(artifact_type=ArtifactType.REQUIREMENT, artifact_id="r1")
            n2 = TraceNode(artifact_type=ArtifactType.CODE_CHANGE, artifact_id="c1")
            store.add_node(n1)
            store.add_node(n2)
            edge = TraceEdge(source_id=n1.node_id, target_id=n2.node_id, relationship=RelationshipType.IMPLEMENTS)
            store.add_edge(edge)
            got = store.get_edge(edge.edge_id)
            assert got is not None
            assert got.source_id == n1.node_id
            assert got.target_id == n2.node_id

    def test_find_nodes_by_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=tmp)
            store.add_node(TraceNode(artifact_type=ArtifactType.REQUIREMENT, artifact_id="r1"))
            store.add_node(TraceNode(artifact_type=ArtifactType.REQUIREMENT, artifact_id="r2"))
            store.add_node(TraceNode(artifact_type=ArtifactType.CODE_CHANGE, artifact_id="c1"))
            found = store.find_nodes_by_type("requirement")
            assert len(found) == 2

    def test_get_forward_neighbors(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=tmp)
            n1 = TraceNode(artifact_type=ArtifactType.REQUIREMENT, artifact_id="r1")
            n2 = TraceNode(artifact_type=ArtifactType.CODE_CHANGE, artifact_id="c1")
            n3 = TraceNode(artifact_type=ArtifactType.TEST_RESULT, artifact_id="t1")
            store.add_node(n1)
            store.add_node(n2)
            store.add_node(n3)
            store.add_edge(TraceEdge(source_id=n1.node_id, target_id=n2.node_id))
            store.add_edge(TraceEdge(source_id=n1.node_id, target_id=n3.node_id))
            neighbors = store.get_forward_neighbors(n1.node_id)
            assert len(neighbors) == 2
            assert n2.node_id in neighbors
            assert n3.node_id in neighbors

    def test_get_backward_neighbors(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=tmp)
            n1 = TraceNode(artifact_type=ArtifactType.REQUIREMENT, artifact_id="r1")
            n2 = TraceNode(artifact_type=ArtifactType.CODE_CHANGE, artifact_id="c1")
            store.add_node(n1)
            store.add_node(n2)
            store.add_edge(TraceEdge(source_id=n1.node_id, target_id=n2.node_id))
            neighbors = store.get_backward_neighbors(n2.node_id)
            assert n1.node_id in neighbors

    def test_get_orphan_node_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=tmp)
            n1 = TraceNode(artifact_type=ArtifactType.REQUIREMENT, artifact_id="r1")
            n2 = TraceNode(artifact_type=ArtifactType.CODE_CHANGE, artifact_id="c1")
            n_orphan = TraceNode(artifact_type=ArtifactType.DEPLOYMENT, artifact_id="d1")
            store.add_node(n1)
            store.add_node(n2)
            store.add_node(n_orphan)
            store.add_edge(TraceEdge(source_id=n1.node_id, target_id=n2.node_id))
            orphans = store.get_orphan_node_ids()
            assert n_orphan.node_id in orphans
            assert n1.node_id not in orphans
            assert n2.node_id not in orphans

    def test_search_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(store_dir=tmp)
            store.add_node(
                TraceNode(artifact_type=ArtifactType.CODE_CHANGE, artifact_id="feat-1", name="add login page")
            )
            store.add_node(
                TraceNode(artifact_type=ArtifactType.CODE_CHANGE, artifact_id="feat-2", name="add logout page")
            )
            store.add_node(
                TraceNode(artifact_type=ArtifactType.REQUIREMENT, artifact_id="req-1", name="auth requirement")
            )
            results = store.search_nodes("login")
            assert len(results) == 1
            assert results[0].artifact_id == "feat-1"


class TestTraceTracker:
    def _make_tracker(self):
        tmp = tempfile.mkdtemp()
        tracker = TraceTracker(store=TraceStore(store_dir=tmp))
        return tracker

    def test_create_node_returns_trace_node(self):
        tracker = self._make_tracker()
        node = tracker.create_node("code_change", "feat-1", name="add feature")
        assert isinstance(node, TraceNode)
        assert node.artifact_type == ArtifactType.CODE_CHANGE
        assert node.artifact_id == "feat-1"

    def test_link_nodes_creates_edge(self):
        tracker = self._make_tracker()
        n1 = tracker.create_node("requirement", "r1")
        n2 = tracker.create_node("code_change", "c1")
        edge = tracker.link_nodes(n1.node_id, n2.node_id, RelationshipType.IMPLEMENTS)
        assert isinstance(edge, TraceEdge)
        assert edge.source_id == n1.node_id
        assert edge.target_id == n2.node_id
        assert edge.relationship == RelationshipType.IMPLEMENTS

    def test_trace_forward_follows_adjacency(self):
        tracker = self._make_tracker()
        n1 = tracker.create_node("requirement", "r1")
        n2 = tracker.create_node("code_change", "c1")
        n3 = tracker.create_node("test_result", "t1")
        tracker.link_nodes(n1.node_id, n2.node_id)
        tracker.link_nodes(n2.node_id, n3.node_id)
        chain = tracker.trace_forward("r1")
        assert len(chain.nodes) == 3
        assert chain.direction == "forward"

    def test_trace_backward_follows_reverse_adjacency(self):
        tracker = self._make_tracker()
        n1 = tracker.create_node("requirement", "r1")
        n2 = tracker.create_node("code_change", "c1")
        n3 = tracker.create_node("test_result", "t1")
        tracker.link_nodes(n1.node_id, n2.node_id)
        tracker.link_nodes(n2.node_id, n3.node_id)
        chain = tracker.trace_backward("t1")
        assert len(chain.nodes) == 3
        assert chain.direction == "backward"

    def test_trace_forward_nonexistent_returns_empty(self):
        tracker = self._make_tracker()
        chain = tracker.trace_forward("nonexistent")
        assert len(chain.nodes) == 0

    def test_generate_report_with_coverage_score(self):
        tracker = self._make_tracker()
        n1 = tracker.create_node("requirement", "r1")
        n2 = tracker.create_node("code_change", "c1")
        tracker.create_node("deployment", "d1")
        tracker.link_nodes(n1.node_id, n2.node_id)
        report = tracker.generate_report()
        assert report.total_nodes == 3
        assert report.total_edges == 1
        assert report.orphan_nodes == 1
        assert 0.0 < report.coverage_score <= 1.0


class TestTraceReport:
    def test_to_markdown_contains_key_sections(self):
        report = TraceReport(
            total_nodes=5,
            total_edges=3,
            artifact_type_counts={"requirement": 2, "code_change": 3},
            relationship_counts={"implements": 2, "tests": 1},
            orphan_nodes=1,
            coverage_score=0.8,
        )
        md = report.to_markdown()
        assert "# Traceability Report" in md
        assert "## Summary" in md
        assert "Total Nodes: 5" in md
        assert "## Artifact Types" in md
        assert "## Relationships" in md
        assert "requirement: 2" in md

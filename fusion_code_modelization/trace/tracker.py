# GateGuard: New file. Importers: trace/__init__.py, cli/__init__.py, pipeline/__init__.py, tests/test_trace.py. Affected API: none. Data schemas: none. User instruction: Phase 4 V2.0 — TraceTracker with forward/backward tracing per enhancement doc.

from __future__ import annotations

import logging
from collections import deque

from .models import ArtifactType, RelationshipType, TraceChain, TraceEdge, TraceNode, TraceReport
from .store import TraceStore

logger = logging.getLogger(__name__)


class TraceTracker:
    def __init__(self, store: TraceStore | None = None) -> None:
        self.store = store or TraceStore()
        logger.info("TraceTracker initialized")

    def create_node(
        self, artifact_type: str | ArtifactType, artifact_id: str, name: str = "", metadata: dict | None = None
    ) -> TraceNode:
        if isinstance(artifact_type, str):
            artifact_type = ArtifactType(artifact_type)
        node = TraceNode(artifact_type=artifact_type, artifact_id=artifact_id, name=name, metadata=metadata or {})
        self.store.add_node(node)
        logger.info("Created trace node: %s (%s/%s)", node.node_id, artifact_type.value, artifact_id)
        return node

    def link_nodes(
        self,
        source_id: str,
        target_id: str,
        relationship: str | RelationshipType = RelationshipType.DEPENDS_ON,
        metadata: dict | None = None,
    ) -> TraceEdge:
        if isinstance(relationship, str):
            relationship = RelationshipType(relationship)
        edge = TraceEdge(source_id=source_id, target_id=target_id, relationship=relationship, metadata=metadata or {})
        self.store.add_edge(edge)
        logger.info("Linked %s -> %s (%s)", source_id, target_id, relationship.value)
        return edge

    def trace_forward(self, artifact_id: str, max_depth: int = 10) -> TraceChain:
        nodes = self.store.find_nodes_by_artifact_id(artifact_id)
        if not nodes:
            return TraceChain()
        start = nodes[0]
        visited_nodes: dict[str, TraceNode] = {start.node_id: start}
        visited_edges: list[TraceEdge] = []
        queue: deque[tuple[str, int]] = deque([(start.node_id, 0)])
        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor_id in self.store.get_forward_neighbors(current_id):
                neighbor = self.store.get_node(neighbor_id)
                if neighbor and neighbor_id not in visited_nodes:
                    visited_nodes[neighbor_id] = neighbor
                    queue.append((neighbor_id, depth + 1))
                edge = next(
                    (e for e in self.store.get_all_edges() if e.source_id == current_id and e.target_id == neighbor_id),
                    None,
                )
                if edge and edge not in visited_edges:
                    visited_edges.append(edge)
        end_id = list(visited_nodes.keys())[-1] if len(visited_nodes) > 1 else start.node_id
        chain = TraceChain(
            start_node_id=start.node_id,
            end_node_id=end_id,
            direction="forward",
            nodes=list(visited_nodes.values()),
            edges=visited_edges,
            depth=max_depth,
        )
        logger.info("Forward trace from %s: %d nodes, %d edges", artifact_id, len(visited_nodes), len(visited_edges))
        return chain

    def trace_backward(self, artifact_id: str, max_depth: int = 10) -> TraceChain:
        nodes = self.store.find_nodes_by_artifact_id(artifact_id)
        if not nodes:
            return TraceChain()
        start = nodes[0]
        visited_nodes: dict[str, TraceNode] = {start.node_id: start}
        visited_edges: list[TraceEdge] = []
        queue: deque[tuple[str, int]] = deque([(start.node_id, 0)])
        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor_id in self.store.get_backward_neighbors(current_id):
                neighbor = self.store.get_node(neighbor_id)
                if neighbor and neighbor_id not in visited_nodes:
                    visited_nodes[neighbor_id] = neighbor
                    queue.append((neighbor_id, depth + 1))
                edge = next(
                    (e for e in self.store.get_all_edges() if e.target_id == current_id and e.source_id == neighbor_id),
                    None,
                )
                if edge and edge not in visited_edges:
                    visited_edges.append(edge)
        end_id = list(visited_nodes.keys())[-1] if len(visited_nodes) > 1 else start.node_id
        chain = TraceChain(
            start_node_id=start.node_id,
            end_node_id=end_id,
            direction="backward",
            nodes=list(visited_nodes.values()),
            edges=visited_edges,
            depth=max_depth,
        )
        logger.info("Backward trace from %s: %d nodes, %d edges", artifact_id, len(visited_nodes), len(visited_edges))
        return chain

    def get_trace_chain(self, artifact_id: str, direction: str = "forward", max_depth: int = 10) -> TraceChain:
        if direction == "backward":
            return self.trace_backward(artifact_id, max_depth)
        return self.trace_forward(artifact_id, max_depth)

    def generate_report(self, filters: dict | None = None) -> TraceReport:
        all_nodes = self.store.get_all_nodes()
        all_edges = self.store.get_all_edges()
        if filters:
            if "artifact_type" in filters:
                all_nodes = [n for n in all_nodes if n.artifact_type.value == filters["artifact_type"]]
            if "relationship" in filters:
                all_edges = [e for e in all_edges if e.relationship.value == filters["relationship"]]
        artifact_type_counts: dict[str, int] = {}
        for n in all_nodes:
            key = n.artifact_type.value
            artifact_type_counts[key] = artifact_type_counts.get(key, 0) + 1
        relationship_counts: dict[str, int] = {}
        for e in all_edges:
            key = e.relationship.value
            relationship_counts[key] = relationship_counts.get(key, 0) + 1
        orphan_ids = self.store.get_orphan_node_ids()
        total = len(all_nodes)
        connected = total - len(orphan_ids)
        coverage = connected / total if total > 0 else 0.0
        report = TraceReport(
            total_nodes=total,
            total_edges=len(all_edges),
            artifact_type_counts=artifact_type_counts,
            relationship_counts=relationship_counts,
            orphan_nodes=len(orphan_ids),
            coverage_score=coverage,
        )
        logger.info(
            "Generated trace report: %d nodes, %d edges, coverage=%.1f%%", total, len(all_edges), coverage * 100
        )
        return report

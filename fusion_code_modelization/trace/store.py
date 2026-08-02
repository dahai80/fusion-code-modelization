# GateGuard: New file. Importers: trace/tracker.py, trace/__init__.py, tests/test_trace.py. Affected API: none. Data schemas: none. User instruction: Phase 4 V2.0 — TraceStore with JSONL persistence per enhancement doc.

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import TraceEdge, TraceNode

logger = logging.getLogger(__name__)

TRACE_DIR = Path.home() / ".fusion" / "trace"


class TraceStore:
    def __init__(self, store_dir: str | Path | None = None) -> None:
        self.store_dir = Path(store_dir) if store_dir else TRACE_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._nodes_path = self.store_dir / "nodes.jsonl"
        self._edges_path = self.store_dir / "edges.jsonl"
        self._nodes: dict[str, TraceNode] = {}
        self._edges: dict[str, TraceEdge] = {}
        self._adjacency: dict[str, list[str]] = {}
        self._reverse_adjacency: dict[str, list[str]] = {}
        self._load()
        logger.info("TraceStore initialized, nodes=%d edges=%d", len(self._nodes), len(self._edges))

    def add_node(self, node: TraceNode) -> None:
        self._nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = []
        if node.node_id not in self._reverse_adjacency:
            self._reverse_adjacency[node.node_id] = []
        self._append_node(node)

    def add_edge(self, edge: TraceEdge) -> None:
        self._edges[edge.edge_id] = edge
        self._adjacency.setdefault(edge.source_id, []).append(edge.target_id)
        self._reverse_adjacency.setdefault(edge.target_id, []).append(edge.source_id)
        self._append_edge(edge)

    def get_node(self, node_id: str) -> TraceNode | None:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> TraceEdge | None:
        return self._edges.get(edge_id)

    def get_all_nodes(self) -> list[TraceNode]:
        return list(self._nodes.values())

    def get_all_edges(self) -> list[TraceEdge]:
        return list(self._edges.values())

    def find_nodes_by_type(self, artifact_type: str) -> list[TraceNode]:
        return [n for n in self._nodes.values() if n.artifact_type.value == artifact_type]

    def find_nodes_by_artifact_id(self, artifact_id: str) -> list[TraceNode]:
        return [n for n in self._nodes.values() if n.artifact_id == artifact_id]

    def get_forward_neighbors(self, node_id: str) -> list[str]:
        return self._adjacency.get(node_id, [])

    def get_backward_neighbors(self, node_id: str) -> list[str]:
        return self._reverse_adjacency.get(node_id, [])

    def get_orphan_node_ids(self) -> list[str]:
        connected = set()
        for edge in self._edges.values():
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        return [nid for nid in self._nodes if nid not in connected]

    def search_nodes(self, query: str) -> list[TraceNode]:
        q = query.lower()
        return [
            n
            for n in self._nodes.values()
            if q in n.name.lower() or q in n.artifact_id.lower() or q in n.artifact_type.value
        ]

    def _append_node(self, node: TraceNode) -> None:
        with open(self._nodes_path, "a") as f:
            f.write(json.dumps(node.to_dict()) + "\n")

    def _append_edge(self, edge: TraceEdge) -> None:
        with open(self._edges_path, "a") as f:
            f.write(json.dumps(edge.to_dict()) + "\n")

    def _load(self) -> None:
        if self._nodes_path.exists():
            for line in self._nodes_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    node = TraceNode.from_dict(json.loads(line))
                    self._nodes[node.node_id] = node
                    self._adjacency.setdefault(node.node_id, [])
                    self._reverse_adjacency.setdefault(node.node_id, [])
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        if self._edges_path.exists():
            for line in self._edges_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    edge = TraceEdge.from_dict(json.loads(line))
                    self._edges[edge.edge_id] = edge
                    self._adjacency.setdefault(edge.source_id, []).append(edge.target_id)
                    self._reverse_adjacency.setdefault(edge.target_id, []).append(edge.source_id)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

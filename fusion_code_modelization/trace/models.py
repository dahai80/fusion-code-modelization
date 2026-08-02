# GateGuard: New file.
# Importers: trace/__init__.py, trace/tracker.py, trace/store.py, cli/__init__.py, tests/test_trace.py
# Affected API: none
# Data schemas: TraceNode, TraceEdge, TraceChain, TraceReport
# User instruction: Phase 4 V2.0 — trace models per enhancement doc

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime


class ArtifactType(enum.StrEnum):
    REQUIREMENT = "requirement"
    CODE_CHANGE = "code_change"
    TEST_RESULT = "test_result"
    DEPLOYMENT = "deployment"
    REVIEW = "review"
    MIGRATION = "migration"
    SECURITY_SCAN = "security_scan"
    BENCHMARK = "benchmark"


class RelationshipType(enum.StrEnum):
    DERIVED_FROM = "derived_from"
    IMPLEMENTS = "implements"
    TESTS = "tests"
    DEPENDS_ON = "depends_on"
    GENERATES = "generates"
    MIGRATES_TO = "migrates_to"
    REVIEWS = "reviews"
    SUPERSEDES = "supersedes"


@dataclass
class TraceNode:
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    artifact_type: ArtifactType = ArtifactType.REQUIREMENT
    artifact_id: str = ""
    name: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "artifact_type": self.artifact_type.value,
            "artifact_id": self.artifact_id,
            "name": self.name,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TraceNode:
        return cls(
            node_id=data.get("node_id", uuid.uuid4().hex[:12]),
            artifact_type=ArtifactType(data.get("artifact_type", "requirement")),
            artifact_id=data.get("artifact_id", ""),
            name=data.get("name", ""),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class TraceEdge:
    edge_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_id: str = ""
    target_id: str = ""
    relationship: RelationshipType = RelationshipType.DEPENDS_ON
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TraceEdge:
        return cls(
            edge_id=data.get("edge_id", uuid.uuid4().hex[:12]),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            relationship=RelationshipType(data.get("relationship", "depends_on")),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class TraceChain:
    start_node_id: str = ""
    end_node_id: str = ""
    direction: str = "forward"
    nodes: list[TraceNode] = field(default_factory=list)
    edges: list[TraceEdge] = field(default_factory=list)
    depth: int = 0

    def to_dict(self) -> dict:
        return {
            "start_node_id": self.start_node_id,
            "end_node_id": self.end_node_id,
            "direction": self.direction,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "depth": self.depth,
        }


@dataclass
class TraceReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    total_nodes: int = 0
    total_edges: int = 0
    artifact_type_counts: dict = field(default_factory=dict)
    relationship_counts: dict = field(default_factory=dict)
    orphan_nodes: int = 0
    coverage_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "artifact_type_counts": self.artifact_type_counts,
            "relationship_counts": self.relationship_counts,
            "orphan_nodes": self.orphan_nodes,
            "coverage_score": self.coverage_score,
            "timestamp": self.timestamp,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Traceability Report",
            f"- Report ID: {self.report_id}",
            f"- Timestamp: {self.timestamp}",
            "",
            "## Summary",
            f"- Total Nodes: {self.total_nodes}",
            f"- Total Edges: {self.total_edges}",
            f"- Orphan Nodes: {self.orphan_nodes}",
            f"- Coverage Score: {self.coverage_score:.1%}",
            "",
            "## Artifact Types",
        ]
        for atype, count in sorted(self.artifact_type_counts.items()):
            lines.append(f"- {atype}: {count}")
        lines.append("")
        lines.append("## Relationships")
        for rel, count in sorted(self.relationship_counts.items()):
            lines.append(f"- {rel}: {count}")
        return "\n".join(lines)

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..core.client import MLXClient

logger = logging.getLogger(__name__)


@dataclass
class CouplingEdge:
    source: str
    target: str
    weight: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target, "weight": self.weight}


@dataclass
class BoundarySuggestion:
    name: str
    modules: list[str] = field(default_factory=list)
    coupling_score: float = 0.0
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "modules": self.modules,
            "coupling_score": self.coupling_score,
            "rationale": self.rationale,
        }


DECOMPOSE_PROMPT = """Analyze this codebase dependency graph and suggest microservice boundaries.

Rules:
- Group highly-coupled modules into the same service
- Minimize cross-service dependencies
- Each service should have a clear domain responsibility
- Return ONLY valid JSON

Dependency graph:
{graph}

Module sizes:
{sizes}

Return format:
{{
  "boundaries": [
    {{
      "name": "service-name",
      "modules": ["mod1", "mod2"],
      "coupling_score": 0.85,
      "rationale": "These modules share data models and API contracts"
    }}
  ]
}}"""


class BoundaryDetector:
    def __init__(self, mlx_url: str = "http://localhost:11434/v1", client: MLXClient | None = None):
        from ..core.config import ModelConfig

        self._client = client or MLXClient(config=ModelConfig(base_url=mlx_url))

    def compute_coupling(self, graph: dict) -> list[CouplingEdge]:
        edges: list[CouplingEdge] = []
        edge_map: dict[tuple[str, str], int] = defaultdict(int)
        for edge in graph.get("edges", []):
            src_mod = edge.get("source", "").split("/")[0] if "/" in edge.get("source", "") else "root"
            tgt_mod = edge.get("target", "").split("/")[0] if "/" in edge.get("target", "") else "root"
            if src_mod != tgt_mod:
                key = tuple(sorted([src_mod, tgt_mod]))
                edge_map[key] += 1
        for (a, b), weight in edge_map.items():
            edges.append(CouplingEdge(source=a, target=b, weight=weight))
        edges.sort(key=lambda e: e.weight, reverse=True)
        logger.info("Computed %d coupling edges", len(edges))
        return edges

    def detect_boundaries_static(self, graph: dict) -> list[BoundarySuggestion]:
        clusters: dict[str, list[str]] = defaultdict(list)
        for node_id in graph.get("nodes", {}):
            module = node_id.split("/")[0] if "/" in node_id else "root"
            clusters[module].append(node_id)
        suggestions = []
        for module, files in sorted(clusters.items()):
            if len(files) >= 2:
                suggestions.append(
                    BoundarySuggestion(
                        name=module,
                        modules=files,
                        coupling_score=0.5,
                        rationale=f"Module {module} contains {len(files)} files",
                    )
                )
        logger.info("Static detection found %d boundaries", len(suggestions))
        return suggestions

    async def detect_boundaries_llm(self, graph: dict) -> list[BoundarySuggestion]:
        import json

        coupling = self.compute_coupling(graph)
        graph_str = json.dumps(
            {"nodes": list(graph.get("nodes", {}).keys())[:100], "edges": [e.to_dict() for e in coupling[:50]]},
            indent=2,
        )
        sizes: dict[str, int] = defaultdict(int)
        for node_id in graph.get("nodes", {}):
            module = node_id.split("/")[0] if "/" in node_id else "root"
            sizes[module] += 1
        sizes_str = json.dumps(dict(sizes), indent=2)
        prompt = DECOMPOSE_PROMPT.format(graph=graph_str, sizes=sizes_str)
        try:
            response = await self._client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            text = response.get("content", "")
            if text:
                text = self._client.extract_code(text)
            data = json.loads(text)
            suggestions = []
            for b in data.get("boundaries", []):
                suggestions.append(
                    BoundarySuggestion(
                        name=b.get("name", ""),
                        modules=b.get("modules", []),
                        coupling_score=b.get("coupling_score", 0.0),
                        rationale=b.get("rationale", ""),
                    )
                )
            logger.info("LLM detection found %d boundaries", len(suggestions))
            return suggestions
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("LLM boundary detection failed: %s", e)
            return self.detect_boundaries_static(graph)

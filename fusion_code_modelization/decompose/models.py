# GateGuard: New file. Importers: decompose/__init__.py, decompose/detector.py. Affected API: none (extracted from __init__.py). Data schemas: CouplingEdge, BoundarySuggestion. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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

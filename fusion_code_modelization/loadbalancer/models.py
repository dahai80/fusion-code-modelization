# GateGuard: New file. Importers: loadbalancer/__init__.py, loadbalancer/balancer.py, tests/test_loadbalancer.py. Affected API: none. Data schemas: LoadMetric, SchedulingDecision, BalancerConfig. User instruction: Phase 4 V2.0 — loadbalancer models per enhancement doc.

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime


class LoadBalanceStrategy(enum.StrEnum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED_CAPACITY = "weighted_capacity"
    AFFINITY_BASED = "affinity_based"


@dataclass
class LoadMetric:
    node_id: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_percent: float = 0.0
    active_tasks: int = 0
    max_tasks: int = 4
    weight: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def load_score(self) -> float:
        return (self.cpu_percent * 0.4 + self.memory_percent * 0.3 + self.gpu_percent * 0.3) * self.weight

    @property
    def available_capacity(self) -> float:
        if self.max_tasks <= 0:
            return 0.0
        return max(0.0, 1.0 - self.active_tasks / self.max_tasks)

    @property
    def is_overloaded(self) -> bool:
        return self.load_score > 80.0 or self.active_tasks >= self.max_tasks

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "gpu_percent": self.gpu_percent,
            "active_tasks": self.active_tasks,
            "max_tasks": self.max_tasks,
            "weight": self.weight,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LoadMetric:
        return cls(
            node_id=data.get("node_id", ""),
            cpu_percent=data.get("cpu_percent", 0.0),
            memory_percent=data.get("memory_percent", 0.0),
            gpu_percent=data.get("gpu_percent", 0.0),
            active_tasks=data.get("active_tasks", 0),
            max_tasks=data.get("max_tasks", 4),
            weight=data.get("weight", 1.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class SchedulingDecision:
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    selected_node: str = ""
    reason: str = ""
    alternatives: list[str] = field(default_factory=list)
    estimated_wait_ms: float = 0.0
    strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOADED
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "selected_node": self.selected_node,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "estimated_wait_ms": self.estimated_wait_ms,
            "strategy": self.strategy.value,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SchedulingDecision:
        return cls(
            decision_id=data.get("decision_id", uuid.uuid4().hex[:12]),
            selected_node=data.get("selected_node", ""),
            reason=data.get("reason", ""),
            alternatives=data.get("alternatives", []),
            estimated_wait_ms=data.get("estimated_wait_ms", 0.0),
            strategy=LoadBalanceStrategy(data.get("strategy", "least_loaded")),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class BalancerConfig:
    strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOADED
    overload_threshold: float = 80.0
    cooldown_seconds: float = 30.0
    max_retries: int = 3
    affinity_ttl_seconds: float = 3600.0

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.value,
            "overload_threshold": self.overload_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "max_retries": self.max_retries,
            "affinity_ttl_seconds": self.affinity_ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BalancerConfig:
        return cls(
            strategy=LoadBalanceStrategy(data.get("strategy", "least_loaded")),
            overload_threshold=data.get("overload_threshold", 80.0),
            cooldown_seconds=data.get("cooldown_seconds", 30.0),
            max_retries=data.get("max_retries", 3),
            affinity_ttl_seconds=data.get("affinity_ttl_seconds", 3600.0),
        )

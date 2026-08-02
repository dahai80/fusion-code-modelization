# GateGuard: New file. Importers: loadbalancer/balancer.py, loadbalancer/__init__.py, tests/test_loadbalancer.py. Affected API: none. Data schemas: none. User instruction: Phase 4 V2.0 — load balance strategy implementations per enhancement doc.

from __future__ import annotations

import logging
from itertools import cycle

from .models import LoadBalanceStrategy, LoadMetric

logger = logging.getLogger(__name__)


class RoundRobinStrategy:
    def __init__(self) -> None:
        self._cycle: cycle | None = None
        self._node_ids: list[str] = []

    def select(self, metrics: list[LoadMetric]) -> LoadMetric | None:
        if not metrics:
            return None
        current_ids = [m.node_id for m in metrics]
        if current_ids != self._node_ids:
            self._node_ids = current_ids
            self._cycle = cycle(metrics)
        if self._cycle is None:
            self._cycle = cycle(metrics)
        selected = next(self._cycle)
        logger.debug("RoundRobin selected: %s", selected.node_id)
        return selected


class LeastLoadedStrategy:
    def select(self, metrics: list[LoadMetric]) -> LoadMetric | None:
        if not metrics:
            return None
        available = [m for m in metrics if not m.is_overloaded]
        if not available:
            available = metrics
        selected = min(available, key=lambda m: m.load_score)
        logger.debug("LeastLoaded selected: %s (load=%.1f)", selected.node_id, selected.load_score)
        return selected


class WeightedCapacityStrategy:
    def select(self, metrics: list[LoadMetric]) -> LoadMetric | None:
        if not metrics:
            return None
        scored = []
        for m in metrics:
            if m.is_overloaded:
                continue
            score = m.available_capacity * m.weight
            scored.append((m, score))
        if not scored:
            scored = [(m, m.weight) for m in metrics]
        selected = max(scored, key=lambda x: x[1])[0]
        logger.debug(
            "WeightedCapacity selected: %s (capacity=%.2f, weight=%.1f)",
            selected.node_id,
            selected.available_capacity,
            selected.weight,
        )
        return selected


class AffinityBasedStrategy:
    def __init__(self) -> None:
        self._affinity: dict[str, str] = {}

    def set_affinity(self, session_id: str, node_id: str) -> None:
        self._affinity[session_id] = node_id
        logger.debug("Affinity set: session=%s -> node=%s", session_id, node_id)

    def clear_affinity(self, session_id: str) -> None:
        self._affinity.pop(session_id, None)

    def select(self, metrics: list[LoadMetric], session_id: str = "") -> LoadMetric | None:
        if not metrics:
            return None
        if session_id and session_id in self._affinity:
            preferred = self._affinity[session_id]
            match = next((m for m in metrics if m.node_id == preferred), None)
            if match and not match.is_overloaded:
                logger.debug("Affinity hit: session=%s -> node=%s", session_id, preferred)
                return match
            logger.debug("Affinity miss for session=%s, node=%s overloaded or gone", session_id, preferred)
        fallback = LeastLoadedStrategy()
        result = fallback.select(metrics)
        if result and session_id:
            self._affinity[session_id] = result.node_id
        return result


STRATEGY_MAP: dict[LoadBalanceStrategy, type] = {
    LoadBalanceStrategy.ROUND_ROBIN: RoundRobinStrategy,
    LoadBalanceStrategy.LEAST_LOADED: LeastLoadedStrategy,
    LoadBalanceStrategy.WEIGHTED_CAPACITY: WeightedCapacityStrategy,
    LoadBalanceStrategy.AFFINITY_BASED: AffinityBasedStrategy,
}


def get_strategy(
    strategy: LoadBalanceStrategy,
) -> RoundRobinStrategy | LeastLoadedStrategy | WeightedCapacityStrategy | AffinityBasedStrategy:
    cls = STRATEGY_MAP.get(strategy, LeastLoadedStrategy)
    return cls()

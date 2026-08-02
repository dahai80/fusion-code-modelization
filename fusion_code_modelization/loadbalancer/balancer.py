# GateGuard: New file. Importers: loadbalancer/__init__.py, cluster/scheduler.py, cli/__init__.py, tests/test_loadbalancer.py. Affected API: none. Data schemas: none. User instruction: Phase 4 V2.0 — LoadBalancer class per enhancement doc.

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import BalancerConfig, LoadBalanceStrategy, LoadMetric, SchedulingDecision
from .strategy import AffinityBasedStrategy, get_strategy

logger = logging.getLogger(__name__)

STATE_DIR = Path.home() / ".fusion" / "loadbalancer"


class LoadBalancer:
    def __init__(self, config: BalancerConfig | None = None, state_dir: str | Path | None = None) -> None:
        self.config = config or BalancerConfig()
        self.state_dir = Path(state_dir) if state_dir else STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._metrics: dict[str, LoadMetric] = {}
        self._strategy = get_strategy(self.config.strategy)
        self._rr_index: int = 0
        self._load_state()
        logger.info("LoadBalancer initialized, strategy=%s", self.config.strategy.value)

    def update_metrics(self, metrics: list[LoadMetric]) -> None:
        for m in metrics:
            self._metrics[m.node_id] = m
        logger.debug("Updated metrics for %d nodes", len(metrics))

    def evaluate_cluster(self) -> list[LoadMetric]:
        return list(self._metrics.values())

    def select_node(self, session_id: str = "", requirements: dict | None = None) -> SchedulingDecision:
        metrics = list(self._metrics.values())
        if not metrics:
            logger.warning("No cluster nodes available")
            return SchedulingDecision(reason="no_nodes_available")

        if self.config.strategy == LoadBalanceStrategy.AFFINITY_BASED and isinstance(
            self._strategy, AffinityBasedStrategy
        ):
            selected_metric = self._strategy.select(metrics, session_id=session_id)
        elif self.config.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            available = [m for m in metrics if not m.is_overloaded]
            if not available:
                available = metrics
            idx = self._rr_index % len(available)
            selected_metric = available[idx]
            self._rr_index += 1
        else:
            selected_metric = self._strategy.select(metrics)

        if not selected_metric:
            return SchedulingDecision(reason="no_suitable_node")

        alternatives = [m.node_id for m in metrics if m.node_id != selected_metric.node_id and not m.is_overloaded]
        estimated_wait = 0.0
        if selected_metric.is_overloaded:
            estimated_wait = self.config.cooldown_seconds * 1000

        decision = SchedulingDecision(
            selected_node=selected_metric.node_id,
            reason=f"{self.config.strategy.value}: load={selected_metric.load_score:.1f} capacity={selected_metric.available_capacity:.2f}",
            alternatives=alternatives,
            estimated_wait_ms=estimated_wait,
            strategy=self.config.strategy,
        )
        self._save_state()
        logger.info("Selected node: %s via %s", selected_metric.node_id, self.config.strategy.value)
        return decision

    def rebalance(self) -> list[SchedulingDecision]:
        decisions = []
        overloaded = [m for m in self._metrics.values() if m.is_overloaded]
        underloaded = [m for m in self._metrics.values() if not m.is_overloaded]
        for over in overloaded:
            excess = over.active_tasks - over.max_tasks + 1
            if excess > 0 and underloaded:
                target = min(underloaded, key=lambda m: m.load_score)
                decisions.append(
                    SchedulingDecision(
                        selected_node=target.node_id,
                        reason=f"rebalance: {over.node_id} overloaded, moving {excess} tasks to {target.node_id}",
                        alternatives=[m.node_id for m in underloaded if m.node_id != target.node_id],
                        strategy=self.config.strategy,
                    )
                )
        if decisions:
            logger.info("Rebalance: %d decisions made", len(decisions))
        return decisions

    def get_cluster_overview(self) -> dict:
        metrics = list(self._metrics.values())
        if not metrics:
            return {
                "total_nodes": 0,
                "healthy_nodes": 0,
                "overloaded_nodes": 0,
                "total_capacity": 0.0,
                "avg_load": 0.0,
                "nodes": [],
            }
        overloaded = [m for m in metrics if m.is_overloaded]
        total_capacity = sum(m.available_capacity for m in metrics)
        avg_load = sum(m.load_score for m in metrics) / len(metrics)
        return {
            "total_nodes": len(metrics),
            "healthy_nodes": len(metrics) - len(overloaded),
            "overloaded_nodes": len(overloaded),
            "total_capacity": total_capacity,
            "avg_load": avg_load,
            "strategy": self.config.strategy.value,
            "nodes": [m.to_dict() for m in metrics],
        }

    def predict_capacity(self, duration_hours: float = 1.0) -> dict:
        metrics = list(self._metrics.values())
        if not metrics:
            return {"predicted_available_tasks": 0, "predicted_avg_load": 0.0}
        total_available = sum(max(0, m.max_tasks - m.active_tasks) for m in metrics)
        avg_load = sum(m.load_score for m in metrics) / len(metrics)
        decay_factor = max(0.5, 1.0 - (duration_hours * 0.05))
        predicted_load = avg_load * decay_factor
        predicted_tasks = int(total_available * decay_factor)
        return {
            "duration_hours": duration_hours,
            "current_total_available_tasks": total_available,
            "current_avg_load": avg_load,
            "predicted_available_tasks": predicted_tasks,
            "predicted_avg_load": predicted_load,
        }

    def _save_state(self) -> None:
        path = self.state_dir / "state.json"
        data = {
            "config": self.config.to_dict(),
            "metrics": {k: v.to_dict() for k, v in self._metrics.items()},
            "rr_index": self._rr_index,
        }
        path.write_text(json.dumps(data, indent=2))

    def _load_state(self) -> None:
        path = self.state_dir / "state.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            if "config" in data:
                self.config = BalancerConfig.from_dict(data["config"])
            if "metrics" in data:
                self._metrics = {k: LoadMetric.from_dict(v) for k, v in data["metrics"].items()}
            if "rr_index" in data:
                self._rr_index = data["rr_index"]
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("Failed to load loadbalancer state")

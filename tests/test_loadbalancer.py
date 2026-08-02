from __future__ import annotations

import tempfile

import pytest

from fusion_code_modelization.loadbalancer.balancer import LoadBalancer
from fusion_code_modelization.loadbalancer.models import (
    BalancerConfig,
    LoadBalanceStrategy,
    LoadMetric,
    SchedulingDecision,
)
from fusion_code_modelization.loadbalancer.strategy import (
    AffinityBasedStrategy,
    LeastLoadedStrategy,
    RoundRobinStrategy,
    WeightedCapacityStrategy,
    get_strategy,
)


def _make_metric(
    node_id: str = "node-1",
    cpu: float = 10.0,
    mem: float = 10.0,
    gpu: float = 10.0,
    active: int = 0,
    max_tasks: int = 4,
    weight: float = 1.0,
) -> LoadMetric:
    return LoadMetric(
        node_id=node_id,
        cpu_percent=cpu,
        memory_percent=mem,
        gpu_percent=gpu,
        active_tasks=active,
        max_tasks=max_tasks,
        weight=weight,
    )


# ── LoadBalanceStrategy ──


class TestLoadBalanceStrategy:
    def test_enum_values(self):
        assert LoadBalanceStrategy.ROUND_ROBIN == "round_robin"
        assert LoadBalanceStrategy.LEAST_LOADED == "least_loaded"
        assert LoadBalanceStrategy.WEIGHTED_CAPACITY == "weighted_capacity"
        assert LoadBalanceStrategy.AFFINITY_BASED == "affinity_based"

    def test_enum_is_str(self):
        for s in LoadBalanceStrategy:
            assert isinstance(s, str)


# ── LoadMetric ──


class TestLoadMetric:
    def test_load_score_calculation(self):
        m = _make_metric(cpu=50.0, mem=60.0, gpu=70.0, weight=1.0)
        expected = (50.0 * 0.4 + 60.0 * 0.3 + 70.0 * 0.3) * 1.0
        assert abs(m.load_score - expected) < 1e-6

    def test_load_score_with_weight(self):
        m = _make_metric(cpu=50.0, mem=50.0, gpu=50.0, weight=2.0)
        base = 50.0 * 0.4 + 50.0 * 0.3 + 50.0 * 0.3
        assert abs(m.load_score - base * 2.0) < 1e-6

    def test_is_overloaded_cpu(self):
        m = _make_metric(cpu=90.0, mem=90.0, gpu=90.0, active=0)
        assert m.is_overloaded is True

    def test_is_overloaded_tasks(self):
        m = _make_metric(cpu=10.0, active=4, max_tasks=4)
        assert m.is_overloaded is True

    def test_not_overloaded(self):
        m = _make_metric(cpu=30.0, active=1, max_tasks=4)
        assert m.is_overloaded is False

    def test_available_capacity(self):
        m = _make_metric(active=1, max_tasks=4)
        assert abs(m.available_capacity - 0.75) < 1e-6

    def test_available_capacity_full(self):
        m = _make_metric(active=4, max_tasks=4)
        assert m.available_capacity == 0.0

    def test_available_capacity_zero_max(self):
        m = _make_metric(active=0, max_tasks=0)
        assert m.available_capacity == 0.0

    def test_to_dict_from_dict_roundtrip(self):
        m = _make_metric(node_id="n1", cpu=33.0, mem=44.0, gpu=55.0, active=2, max_tasks=8, weight=1.5)
        d = m.to_dict()
        restored = LoadMetric.from_dict(d)
        assert restored.node_id == m.node_id
        assert abs(restored.cpu_percent - m.cpu_percent) < 1e-6
        assert abs(restored.memory_percent - m.memory_percent) < 1e-6
        assert abs(restored.gpu_percent - m.gpu_percent) < 1e-6
        assert restored.active_tasks == m.active_tasks
        assert restored.max_tasks == m.max_tasks
        assert abs(restored.weight - m.weight) < 1e-6


# ── BalancerConfig ──


class TestBalancerConfig:
    def test_defaults(self):
        c = BalancerConfig()
        assert c.strategy == LoadBalanceStrategy.LEAST_LOADED
        assert c.overload_threshold == 80.0
        assert c.cooldown_seconds == 30.0
        assert c.max_retries == 3
        assert c.affinity_ttl_seconds == 3600.0


# ── SchedulingDecision ──


class TestSchedulingDecision:
    def test_to_dict_from_dict_roundtrip(self):
        sd = SchedulingDecision(
            selected_node="node-a",
            reason="test",
            alternatives=["node-b", "node-c"],
            estimated_wait_ms=500.0,
            strategy=LoadBalanceStrategy.WEIGHTED_CAPACITY,
        )
        d = sd.to_dict()
        restored = SchedulingDecision.from_dict(d)
        assert restored.selected_node == sd.selected_node
        assert restored.reason == sd.reason
        assert restored.alternatives == sd.alternatives
        assert abs(restored.estimated_wait_ms - sd.estimated_wait_ms) < 1e-6
        assert restored.strategy == sd.strategy


# ── Strategy classes ──


class TestRoundRobinStrategy:
    def test_cycles_through_nodes(self):
        s = RoundRobinStrategy()
        metrics = [_make_metric(node_id="a"), _make_metric(node_id="b"), _make_metric(node_id="c")]
        results = [s.select(metrics).node_id for _ in range(6)]
        assert results == ["a", "b", "c", "a", "b", "c"]

    def test_empty_returns_none(self):
        s = RoundRobinStrategy()
        assert s.select([]) is None


class TestLeastLoadedStrategy:
    def test_picks_min_load_score(self):
        s = LeastLoadedStrategy()
        low = _make_metric(node_id="low", cpu=10.0, mem=10.0, gpu=10.0)
        high = _make_metric(node_id="high", cpu=70.0, mem=70.0, gpu=70.0)
        assert s.select([high, low]).node_id == "low"

    def test_empty_returns_none(self):
        s = LeastLoadedStrategy()
        assert s.select([]) is None


class TestWeightedCapacityStrategy:
    def test_picks_max_available_capacity_weight(self):
        s = WeightedCapacityStrategy()
        small = _make_metric(node_id="small", active=3, max_tasks=4, weight=1.0)
        big = _make_metric(node_id="big", active=0, max_tasks=4, weight=2.0)
        assert s.select([small, big]).node_id == "big"

    def test_empty_returns_none(self):
        s = WeightedCapacityStrategy()
        assert s.select([]) is None


class TestAffinityBasedStrategy:
    def test_prefers_same_node_for_session(self):
        s = AffinityBasedStrategy()
        metrics = [_make_metric(node_id="n1", cpu=10.0), _make_metric(node_id="n2", cpu=10.0)]
        first = s.select(metrics, session_id="sess-1")
        assert first is not None
        second = s.select(metrics, session_id="sess-1")
        assert second.node_id == first.node_id

    def test_fallback_when_affinity_node_overloaded(self):
        s = AffinityBasedStrategy()
        m1 = _make_metric(node_id="n1", cpu=90.0, active=4, max_tasks=4)
        m2 = _make_metric(node_id="n2", cpu=10.0, active=0, max_tasks=4)
        s.set_affinity("sess-1", "n1")
        result = s.select([m1, m2], session_id="sess-1")
        assert result.node_id == "n2"

    def test_empty_returns_none(self):
        s = AffinityBasedStrategy()
        assert s.select([], session_id="sess-1") is None


# ── get_strategy factory ──


class TestGetStrategy:
    @pytest.mark.parametrize(
        "strategy, cls",
        [
            (LoadBalanceStrategy.ROUND_ROBIN, RoundRobinStrategy),
            (LoadBalanceStrategy.LEAST_LOADED, LeastLoadedStrategy),
            (LoadBalanceStrategy.WEIGHTED_CAPACITY, WeightedCapacityStrategy),
            (LoadBalanceStrategy.AFFINITY_BASED, AffinityBasedStrategy),
        ],
    )
    def test_returns_correct_class(self, strategy, cls):
        assert isinstance(get_strategy(strategy), cls)


# ── LoadBalancer ──


class TestLoadBalancer:
    def _make_balancer(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOADED) -> LoadBalancer:
        state_dir = tempfile.mkdtemp()
        config = BalancerConfig(strategy=strategy)
        return LoadBalancer(config=config, state_dir=state_dir)

    def test_update_metrics_and_select_node(self):
        lb = self._make_balancer(LoadBalanceStrategy.LEAST_LOADED)
        lb.update_metrics(
            [
                _make_metric(node_id="n1", cpu=50.0),
                _make_metric(node_id="n2", cpu=10.0),
            ]
        )
        decision = lb.select_node()
        assert decision.selected_node == "n2"
        assert decision.selected_node != ""

    def test_select_node_no_nodes(self):
        lb = self._make_balancer()
        decision = lb.select_node()
        assert decision.selected_node == ""

    def test_get_cluster_overview(self):
        lb = self._make_balancer()
        lb.update_metrics(
            [
                _make_metric(node_id="n1", cpu=50.0),
                _make_metric(node_id="n2", cpu=90.0, active=4, max_tasks=4),
            ]
        )
        overview = lb.get_cluster_overview()
        assert overview["total_nodes"] == 2
        assert overview["overloaded_nodes"] == 1
        assert overview["healthy_nodes"] == 1
        assert "avg_load" in overview
        assert len(overview["nodes"]) == 2

    def test_rebalance_identifies_migrations(self):
        lb = self._make_balancer()
        lb.update_metrics(
            [
                _make_metric(node_id="n1", cpu=90.0, active=4, max_tasks=4),
                _make_metric(node_id="n2", cpu=10.0, active=0, max_tasks=4),
            ]
        )
        decisions = lb.rebalance()
        assert len(decisions) >= 1
        assert decisions[0].selected_node == "n2"

    def test_predict_capacity(self):
        lb = self._make_balancer()
        lb.update_metrics(
            [
                _make_metric(node_id="n1", active=1, max_tasks=4),
                _make_metric(node_id="n2", active=0, max_tasks=4),
            ]
        )
        result = lb.predict_capacity(duration_hours=2.0)
        assert "predicted_available_tasks" in result
        assert "predicted_avg_load" in result
        assert result["duration_hours"] == 2.0
        assert result["predicted_available_tasks"] >= 0

    def test_round_robin_through_balancer(self):
        lb = self._make_balancer(LoadBalanceStrategy.ROUND_ROBIN)
        lb.update_metrics(
            [
                _make_metric(node_id="a"),
                _make_metric(node_id="b"),
            ]
        )
        first = lb.select_node().selected_node
        second = lb.select_node().selected_node
        assert first != second

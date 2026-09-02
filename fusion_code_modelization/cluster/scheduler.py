from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from ..loadbalancer import BalancerConfig, LoadBalancer, LoadBalanceStrategy, LoadMetric
from .models import NodeInfo, NodeStatus, TaskDispatch, TaskDispatchStatus
from .node_client import NodeClient

logger = logging.getLogger(__name__)


class ClusterScheduler:
    def __init__(self, cluster_dir: str = ".fusion/cluster", enable_loadbalancer: bool = True):
        self.cluster_dir = Path(cluster_dir)
        self.cluster_dir.mkdir(parents=True, exist_ok=True)
        self._nodes_file = self.cluster_dir / "nodes.json"
        self._tasks_file = self.cluster_dir / "tasks.json"
        self._nodes: dict[str, NodeInfo] = {}
        self._tasks: dict[str, TaskDispatch] = {}
        self._last_nodes_hash: str = ""
        self._last_tasks_hash: str = ""
        self._node_client = NodeClient()
        self._loadbalancer: LoadBalancer | None = None
        if enable_loadbalancer:
            self._loadbalancer = LoadBalancer(
                config=BalancerConfig(strategy=LoadBalanceStrategy.LEAST_LOADED),
                state_dir=str(self.cluster_dir / "lb_state"),
            )
        self._load_state()

    def _load_state(self) -> None:
        if self._nodes_file.exists():
            try:
                data = json.loads(self._nodes_file.read_text(encoding="utf-8"))
                for nid, ndata in data.items():
                    self._nodes[nid] = NodeInfo.from_dict(ndata)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("failed to load nodes: %s", e)
        if self._tasks_file.exists():
            try:
                data = json.loads(self._tasks_file.read_text(encoding="utf-8"))
                for tid, tdata in data.items():
                    self._tasks[tid] = TaskDispatch.from_dict(tdata)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("failed to load tasks: %s", e)

    def _save_state(self) -> None:
        nodes_data = {nid: n.to_dict() for nid, n in self._nodes.items()}
        nodes_json = json.dumps(nodes_data, indent=2, ensure_ascii=False)
        if nodes_json != self._last_nodes_hash:
            self._atomic_write(self._nodes_file, nodes_json)
            self._last_nodes_hash = nodes_json
        tasks_data = {tid: t.to_dict() for tid, t in self._tasks.items()}
        tasks_json = json.dumps(tasks_data, indent=2, ensure_ascii=False)
        if tasks_json != self._last_tasks_hash:
            self._atomic_write(self._tasks_file, tasks_json)
            self._last_tasks_hash = tasks_json

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    def register_node(self, node: NodeInfo) -> NodeInfo:
        self._nodes[node.node_id] = node
        self._save_state()
        logger.info("registered node: %s (%s:%d)", node.node_id, node.host, node.port)
        return node

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._save_state()
        logger.info("removed node: %s", node_id)
        return True

    def discover_nodes(self) -> list[NodeInfo]:
        return list(self._nodes.values())

    async def get_node_status(self) -> list[NodeInfo]:
        import asyncio

        nodes = list(self._nodes.values())
        if not nodes:
            return []
        await asyncio.gather(*(self._node_client.health_check(n) for n in nodes), return_exceptions=True)
        self._save_state()
        return list(self._nodes.values())

    async def dispatch_task(self, session_id: str, target_node: str, description: str = "") -> TaskDispatch:
        node = self._nodes.get(target_node)
        if not node:
            logger.error("dispatch_task: node %s not found", target_node)
            task = TaskDispatch(
                task_id=uuid.uuid4().hex[:12],
                session_id=session_id,
                target_node=target_node,
                status=TaskDispatchStatus.FAILED,
                description=description,
                result={"error": f"node {target_node} not found"},
            )
            return task

        task_id = uuid.uuid4().hex[:12]
        task = TaskDispatch(
            task_id=task_id,
            session_id=session_id,
            target_node=target_node,
            description=description,
            status=TaskDispatchStatus.RUNNING,
        )
        self._tasks[task_id] = task
        self._save_state()

        result = await self._node_client.submit_task(node, session_id, description)
        task.status = TaskDispatchStatus.COMPLETED if result["status"] == "completed" else TaskDispatchStatus.FAILED
        task.result = result
        self._save_state()
        logger.info("dispatch_task: %s -> %s [%s]", task_id, target_node, task.status.value)
        return task

    async def auto_schedule(self, session_id: str, description: str = "", require_gpu: bool = False) -> TaskDispatch:
        if self._loadbalancer:
            return await self._smart_dispatch(session_id, description, require_gpu)
        candidates = [n for n in self._nodes.values() if n.status == NodeStatus.ONLINE]
        if require_gpu:
            candidates = [n for n in candidates if n.gpu_memory_percent < 80.0]
        if not candidates:
            candidates = list(self._nodes.values())
        if not candidates:
            logger.error("auto_schedule: no nodes available")
            return TaskDispatch(
                task_id=uuid.uuid4().hex[:12],
                session_id=session_id,
                target_node="",
                status=TaskDispatchStatus.FAILED,
                description=description,
                result={"error": "no nodes available"},
            )
        best = min(candidates, key=lambda n: n.load_score)
        logger.info("auto_schedule: selected %s (load=%.1f%%)", best.node_id, best.load_score)
        return await self.dispatch_task(session_id, best.node_id, description)

    async def _smart_dispatch(self, session_id: str, description: str, require_gpu: bool) -> TaskDispatch:
        if not self._loadbalancer:
            return await self._fallback_dispatch(session_id, description)
        self._sync_loadbalancer_metrics()
        decision = self._loadbalancer.select_node(session_id=session_id)
        if not decision or not decision.selected_node:
            logger.warning("smart_dispatch: loadbalancer returned no node, falling back")
            return await self._fallback_dispatch(session_id, description)
        target = decision.selected_node
        logger.info("smart_dispatch: selected %s via %s — %s", target, decision.strategy, decision.reason)
        return await self.dispatch_task(session_id, target, description)

    async def _fallback_dispatch(self, session_id: str, description: str) -> TaskDispatch:
        candidates = [n for n in self._nodes.values() if n.status == NodeStatus.ONLINE]
        if not candidates:
            candidates = list(self._nodes.values())
        if not candidates:
            return TaskDispatch(
                task_id=uuid.uuid4().hex[:12],
                session_id=session_id,
                target_node="",
                status=TaskDispatchStatus.FAILED,
                description=description,
                result={"error": "no nodes available"},
            )
        best = min(candidates, key=lambda n: n.load_score)
        return await self.dispatch_task(session_id, best.node_id, description)

    def _sync_loadbalancer_metrics(self):
        if not self._loadbalancer:
            return
        metrics = []
        for node in self._nodes.values():
            metrics.append(
                LoadMetric(
                    node_id=node.node_id,
                    cpu_percent=node.cpu_percent,
                    memory_percent=node.memory_percent,
                    gpu_percent=node.gpu_memory_percent,
                    active_tasks=node.active_tasks,
                )
            )
        if metrics:
            self._loadbalancer.update_metrics(metrics)

    def cluster_health_report(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "total_nodes": len(self._nodes),
            "online_nodes": sum(1 for n in self._nodes.values() if n.status == NodeStatus.ONLINE),
            "total_tasks": len(self._tasks),
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
        }
        if self._loadbalancer:
            self._sync_loadbalancer_metrics()
            report["loadbalancer"] = self._loadbalancer.get_cluster_overview()
            report["rebalance_suggestions"] = self._loadbalancer.rebalance()
        return report

    async def migrate_session(self, session_id: str, from_node: str, to_node: str) -> TaskDispatch:
        logger.info("migrate_session: %s from %s to %s", session_id, from_node, to_node)
        source = self._nodes.get(from_node)
        target = self._nodes.get(to_node)
        if not source or not target:
            return TaskDispatch(
                task_id=uuid.uuid4().hex[:12],
                session_id=session_id,
                target_node=to_node,
                status=TaskDispatchStatus.FAILED,
                result={"error": "source or target node not found"},
            )
        task_id = uuid.uuid4().hex[:12]
        task = TaskDispatch(
            task_id=task_id,
            session_id=session_id,
            target_node=to_node,
            status=TaskDispatchStatus.MIGRATED,
            description=f"migrate from {from_node} to {to_node}",
        )
        self._tasks[task_id] = task
        self._save_state()
        return task

    def list_tasks(self) -> list[TaskDispatch]:
        return list(self._tasks.values())

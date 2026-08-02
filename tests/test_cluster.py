# Test file for cluster module. Affected API: NodeInfo, TaskDispatch, ClusterScheduler, NodeClient. Importer: test runner. Schema: NodeInfo.to_dict. User instruction: 开始阶段3

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.cluster import (
    ClusterScheduler,
    NodeClient,
    NodeInfo,
    NodeStatus,
    TaskDispatch,
    TaskDispatchStatus,
)


class TestNodeStatus:
    def test_values(self):
        assert NodeStatus.ONLINE.value == "online"
        assert NodeStatus.OFFLINE.value == "offline"
        assert NodeStatus.BUSY.value == "busy"
        assert NodeStatus.ERROR.value == "error"


class TestTaskDispatchStatus:
    def test_values(self):
        assert TaskDispatchStatus.PENDING.value == "pending"
        assert TaskDispatchStatus.RUNNING.value == "running"
        assert TaskDispatchStatus.COMPLETED.value == "completed"
        assert TaskDispatchStatus.FAILED.value == "failed"
        assert TaskDispatchStatus.MIGRATED.value == "migrated"


class TestNodeInfo:
    def test_defaults(self):
        n = NodeInfo(node_id="n1")
        assert n.host == "localhost"
        assert n.port == 11434
        assert n.status == NodeStatus.ONLINE
        assert n.last_heartbeat != ""

    def test_load_score(self):
        n = NodeInfo(node_id="n1", cpu_percent=30.0, memory_percent=60.0, gpu_memory_percent=90.0)
        assert n.load_score == 60.0

    def test_load_score_zero(self):
        n = NodeInfo(node_id="n1")
        assert n.load_score == 0.0

    def test_to_dict(self):
        n = NodeInfo(node_id="n1", host="10.0.0.1", port=8080)
        d = n.to_dict()
        assert d["node_id"] == "n1"
        assert d["host"] == "10.0.0.1"
        assert d["port"] == 8080

    def test_from_dict(self):
        data = {"node_id": "n2", "host": "host2", "port": 9999, "status": "busy", "cpu_percent": 50.0}
        n = NodeInfo.from_dict(data)
        assert n.node_id == "n2"
        assert n.status == NodeStatus.BUSY
        assert n.cpu_percent == 50.0

    def test_roundtrip(self):
        n = NodeInfo(node_id="n3", host="h3", cpu_percent=40.0, memory_percent=50.0)
        d = n.to_dict()
        restored = NodeInfo.from_dict(d)
        assert restored.node_id == n.node_id
        assert restored.cpu_percent == n.cpu_percent


class TestTaskDispatch:
    def test_defaults(self):
        t = TaskDispatch(task_id="t1", session_id="s1", target_node="n1")
        assert t.status == TaskDispatchStatus.PENDING
        assert t.created_at != ""

    def test_to_dict(self):
        t = TaskDispatch(task_id="t1", session_id="s1", target_node="n1", status=TaskDispatchStatus.COMPLETED)
        d = t.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "completed"

    def test_from_dict(self):
        data = {"task_id": "t2", "session_id": "s2", "target_node": "n2", "status": "failed"}
        t = TaskDispatch.from_dict(data)
        assert t.status == TaskDispatchStatus.FAILED


class TestClusterScheduler:
    @pytest.fixture
    def scheduler(self, tmp_path):
        return ClusterScheduler(cluster_dir=str(tmp_path / "cluster"))

    def test_register_node(self, scheduler):
        node = NodeInfo(node_id="n1", host="10.0.0.1")
        result = scheduler.register_node(node)
        assert result.node_id == "n1"

    def test_remove_node(self, scheduler):
        scheduler.register_node(NodeInfo(node_id="n1"))
        assert scheduler.remove_node("n1") is True
        assert scheduler.remove_node("n1") is False

    def test_discover_nodes(self, scheduler):
        scheduler.register_node(NodeInfo(node_id="n1"))
        scheduler.register_node(NodeInfo(node_id="n2"))
        nodes = scheduler.discover_nodes()
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_dispatch_task_node_not_found(self, scheduler):
        task = await scheduler.dispatch_task("s1", "missing_node")
        assert task.status == TaskDispatchStatus.FAILED

    @pytest.mark.asyncio
    async def test_dispatch_task_success(self, scheduler):
        scheduler.register_node(NodeInfo(node_id="n1", host="localhost"))
        with patch.object(
            scheduler._node_client, "submit_task", new=AsyncMock(return_value={"status": "completed", "content": "ok"})
        ):
            task = await scheduler.dispatch_task("s1", "n1", "test task")
            assert task.status == TaskDispatchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_dispatch_task_failure(self, scheduler):
        scheduler.register_node(NodeInfo(node_id="n1", host="localhost"))
        with patch.object(
            scheduler._node_client, "submit_task", new=AsyncMock(return_value={"status": "failed", "error": "boom"})
        ):
            task = await scheduler.dispatch_task("s1", "n1", "test task")
            assert task.status == TaskDispatchStatus.FAILED

    @pytest.mark.asyncio
    async def test_auto_schedule(self, scheduler):
        scheduler.register_node(NodeInfo(node_id="n1", cpu_percent=80.0, memory_percent=80.0))
        scheduler.register_node(NodeInfo(node_id="n2", cpu_percent=10.0, memory_percent=10.0))
        with patch.object(
            scheduler._node_client, "submit_task", new=AsyncMock(return_value={"status": "completed", "content": "ok"})
        ):
            task = await scheduler.auto_schedule("s1", "work")
            assert task.status == TaskDispatchStatus.COMPLETED
            assert task.target_node == "n2"

    @pytest.mark.asyncio
    async def test_auto_schedule_no_nodes(self, scheduler):
        task = await scheduler.auto_schedule("s1", "work")
        assert task.status == TaskDispatchStatus.FAILED

    @pytest.mark.asyncio
    async def test_migrate_session(self, scheduler):
        scheduler.register_node(NodeInfo(node_id="n1"))
        scheduler.register_node(NodeInfo(node_id="n2"))
        task = await scheduler.migrate_session("s1", "n1", "n2")
        assert task.status == TaskDispatchStatus.MIGRATED
        assert task.target_node == "n2"

    @pytest.mark.asyncio
    async def test_migrate_session_missing_node(self, scheduler):
        task = await scheduler.migrate_session("s1", "n1", "n2")
        assert task.status == TaskDispatchStatus.FAILED

    def test_list_tasks(self, scheduler):
        tasks = scheduler.list_tasks()
        assert isinstance(tasks, list)

    def test_persistence(self, tmp_path):
        dir_path = str(tmp_path / "cluster")
        s1 = ClusterScheduler(cluster_dir=dir_path)
        s1.register_node(NodeInfo(node_id="persist1"))
        s2 = ClusterScheduler(cluster_dir=dir_path)
        nodes = s2.discover_nodes()
        assert any(n.node_id == "persist1" for n in nodes)


class TestNodeClient:
    @pytest.mark.asyncio
    async def test_health_check_offline(self):
        client = NodeClient(default_timeout=0.1)
        node = NodeInfo(node_id="n1", host="192.0.2.1", port=1)
        result = await client.health_check(node)
        assert result is False
        assert node.status == NodeStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_submit_task_offline(self):
        client = NodeClient(default_timeout=0.1)
        node = NodeInfo(node_id="n1", host="192.0.2.1", port=1)
        result = await client.submit_task(node, "s1", "test")
        assert result["status"] == "failed"

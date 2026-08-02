from __future__ import annotations

import shutil
import tempfile

import pytest

from fusion_code_modelization.agent_comm.channel import AgentChannelManager
from fusion_code_modelization.agent_comm.coordinator import CollaborationCoordinator
from fusion_code_modelization.agent_comm.models import (
    AgentChannel,
    AgentMessage,
    AgentRole,
    CollaborationStatus,
    CollaborationTask,
    MessageType,
)


@pytest.fixture
def state_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


# ── Enum values ──


class TestMessageType:
    def test_values(self):
        assert MessageType.TASK_ASSIGNMENT == "task_assignment"
        assert MessageType.RESULT_DELIVERY == "result_delivery"
        assert MessageType.STATUS_UPDATE == "status_update"
        assert MessageType.CONFLICT_REPORT == "conflict_report"
        assert MessageType.SYNC_REQUEST == "sync_request"
        assert MessageType.SYNC_RESPONSE == "sync_response"
        assert MessageType.HEARTBEAT == "heartbeat"


class TestCollaborationStatus:
    def test_values(self):
        assert CollaborationStatus.PENDING == "pending"
        assert CollaborationStatus.ACTIVE == "active"
        assert CollaborationStatus.COMPLETED == "completed"
        assert CollaborationStatus.FAILED == "failed"
        assert CollaborationStatus.CONFLICT == "conflict"


class TestAgentRole:
    def test_values(self):
        assert AgentRole.LEAD == "lead"
        assert AgentRole.WORKER == "worker"
        assert AgentRole.REVIEWER == "reviewer"
        assert AgentRole.INTEGRATOR == "integrator"


# ── Model roundtrip ──


class TestAgentMessageRoundtrip:
    def test_to_dict_from_dict(self):
        msg = AgentMessage(
            message_id="abc123",
            sender_id="agent_a",
            recipient_id="agent_b",
            channel_name="ch1",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"key": "val"},
            timestamp="2026-01-01T00:00:00",
        )
        d = msg.to_dict()
        restored = AgentMessage.from_dict(d)
        assert restored.message_id == "abc123"
        assert restored.sender_id == "agent_a"
        assert restored.recipient_id == "agent_b"
        assert restored.channel_name == "ch1"
        assert restored.message_type == MessageType.TASK_ASSIGNMENT
        assert restored.payload == {"key": "val"}
        assert restored.timestamp == "2026-01-01T00:00:00"


class TestAgentChannelRoundtrip:
    def test_to_dict_from_dict(self):
        ch = AgentChannel(
            name="test_ch",
            participants=["a", "b"],
            created_at="2026-01-01T00:00:00",
            is_active=True,
        )
        d = ch.to_dict()
        restored = AgentChannel.from_dict(d)
        assert restored.name == "test_ch"
        assert restored.participants == ["a", "b"]
        assert restored.created_at == "2026-01-01T00:00:00"
        assert restored.is_active is True


class TestCollaborationTaskRoundtrip:
    def test_to_dict_from_dict_with_roles(self):
        task = CollaborationTask(
            collaboration_id="collab1",
            task_description="refactor module",
            agent_ids=["a1", "a2"],
            roles={"a1": AgentRole.LEAD, "a2": AgentRole.WORKER},
            status=CollaborationStatus.ACTIVE,
            results={"a1": {"output": "done"}},
            channel_name="ch_collab1",
            created_at="2026-01-01T00:00:00",
        )
        d = task.to_dict()
        assert d["roles"] == {"a1": "lead", "a2": "worker"}
        restored = CollaborationTask.from_dict(d)
        assert restored.collaboration_id == "collab1"
        assert restored.roles == {"a1": AgentRole.LEAD, "a2": AgentRole.WORKER}
        assert restored.status == CollaborationStatus.ACTIVE
        assert restored.results == {"a1": {"output": "done"}}


# ── AgentChannelManager ──


class TestAgentChannelManager:
    def test_create_and_get_channel(self, state_dir):
        mgr = AgentChannelManager(state_dir=state_dir)
        ch = mgr.create_channel("ch1", ["a", "b"])
        assert ch.name == "ch1"
        assert ch.participants == ["a", "b"]
        assert ch.is_active is True
        got = mgr.get_channel("ch1")
        assert got is ch

    def test_list_channels(self, state_dir):
        mgr = AgentChannelManager(state_dir=state_dir)
        mgr.create_channel("ch1", ["a"])
        mgr.create_channel("ch2", ["b"])
        names = {ch.name for ch in mgr.list_channels()}
        assert names == {"ch1", "ch2"}

    def test_close_channel_sets_inactive(self, state_dir):
        mgr = AgentChannelManager(state_dir=state_dir)
        mgr.create_channel("ch1", ["a"])
        assert mgr.close_channel("ch1") is True
        ch = mgr.get_channel("ch1")
        assert ch.is_active is False

    def test_send_message_active_channel(self, state_dir):
        mgr = AgentChannelManager(state_dir=state_dir)
        mgr.create_channel("ch1", ["a", "b"])
        msg = AgentMessage(
            sender_id="a",
            recipient_id="b",
            channel_name="ch1",
            message_type=MessageType.STATUS_UPDATE,
            payload={"x": 1},
        )
        assert mgr.send_message(msg) is True
        received = mgr.receive_messages("b", "ch1")
        assert len(received) == 1
        assert received[0].payload == {"x": 1}

    def test_send_message_inactive_channel_fails(self, state_dir):
        mgr = AgentChannelManager(state_dir=state_dir)
        mgr.create_channel("ch1", ["a", "b"])
        mgr.close_channel("ch1")
        msg = AgentMessage(
            sender_id="a",
            recipient_id="b",
            channel_name="ch1",
            message_type=MessageType.STATUS_UPDATE,
            payload={},
        )
        assert mgr.send_message(msg) is False

    def test_receive_messages_filters_by_agent_id(self, state_dir):
        mgr = AgentChannelManager(state_dir=state_dir)
        mgr.create_channel("ch1", ["a", "b", "c"])
        msg_b = AgentMessage(
            sender_id="a",
            recipient_id="b",
            channel_name="ch1",
            message_type=MessageType.STATUS_UPDATE,
            payload={"to": "b"},
        )
        msg_c = AgentMessage(
            sender_id="a",
            recipient_id="c",
            channel_name="ch1",
            message_type=MessageType.STATUS_UPDATE,
            payload={"to": "c"},
        )
        mgr.send_message(msg_b)
        mgr.send_message(msg_c)
        for_b = mgr.receive_messages("b", "ch1")
        for_c = mgr.receive_messages("c", "ch1")
        assert len(for_b) == 1 and for_b[0].payload["to"] == "b"
        assert len(for_c) == 1 and for_c[0].payload["to"] == "c"

    def test_broadcast_sends_to_all_except_sender(self, state_dir):
        mgr = AgentChannelManager(state_dir=state_dir)
        mgr.create_channel("ch1", ["a", "b", "c"])
        count = mgr.broadcast("a", "ch1", MessageType.SYNC_REQUEST, {"sync": True})
        assert count == 2
        for_b = mgr.receive_messages("b", "ch1")
        for_c = mgr.receive_messages("c", "ch1")
        for_a = mgr.receive_messages("a", "ch1")
        assert len(for_b) == 1
        assert len(for_c) == 1
        assert len(for_a) == 0


# ── CollaborationCoordinator ──


class TestCollaborationCoordinator:
    def test_create_collaboration_creates_task_and_channel(self, state_dir):
        coord = CollaborationCoordinator(state_dir=state_dir)
        task = coord.create_collaboration("refactor core", ["a1", "a2", "a3"])
        assert task.task_description == "refactor core"
        assert task.agent_ids == ["a1", "a2", "a3"]
        assert task.status == CollaborationStatus.ACTIVE
        assert task.roles["a1"] == AgentRole.LEAD
        assert task.roles["a2"] == AgentRole.WORKER
        ch = coord.channel_manager.get_channel(task.channel_name)
        assert ch is not None
        assert ch.is_active is True

    def test_submit_result_stores_result(self, state_dir):
        coord = CollaborationCoordinator(state_dir=state_dir)
        task = coord.create_collaboration("migrate code", ["a1", "a2"])
        result = {"files_migrated": 5, "errors": 0}
        assert coord.submit_result(task.collaboration_id, "a1", result) is True
        fetched = coord.get_task(task.collaboration_id)
        assert fetched.results["a1"] == result

    def test_report_conflict_sets_conflict(self, state_dir):
        coord = CollaborationCoordinator(state_dir=state_dir)
        task = coord.create_collaboration("merge branches", ["a1", "a2"])
        assert coord.report_conflict(task.collaboration_id, "a1", {"reason": "overlap"}) is True
        fetched = coord.get_task(task.collaboration_id)
        assert fetched.status == CollaborationStatus.CONFLICT

    def test_resolve_conflict_sets_active(self, state_dir):
        coord = CollaborationCoordinator(state_dir=state_dir)
        task = coord.create_collaboration("fix bug", ["a1", "a2"])
        coord.report_conflict(task.collaboration_id, "a1", {"reason": "overlap"})
        assert coord.resolve_conflict(task.collaboration_id, {"action": "rebase"}) is True
        fetched = coord.get_task(task.collaboration_id)
        assert fetched.status == CollaborationStatus.ACTIVE

    def test_complete_collaboration_sets_completed_and_closes_channel(self, state_dir):
        coord = CollaborationCoordinator(state_dir=state_dir)
        task = coord.create_collaboration("ship feature", ["a1", "a2"])
        assert coord.complete_collaboration(task.collaboration_id) is True
        fetched = coord.get_task(task.collaboration_id)
        assert fetched.status == CollaborationStatus.COMPLETED
        ch = coord.channel_manager.get_channel(task.channel_name)
        assert ch.is_active is False

    def test_get_agent_role_returns_correct_role(self, state_dir):
        coord = CollaborationCoordinator(state_dir=state_dir)
        task = coord.create_collaboration(
            "review code", ["lead1", "rev1"], {"lead1": AgentRole.LEAD, "rev1": AgentRole.REVIEWER}
        )
        assert coord.get_agent_role(task.collaboration_id, "lead1") == AgentRole.LEAD
        assert coord.get_agent_role(task.collaboration_id, "rev1") == AgentRole.REVIEWER
        assert coord.get_agent_role(task.collaboration_id, "unknown") is None

    def test_list_tasks_filters_by_status(self, state_dir):
        coord = CollaborationCoordinator(state_dir=state_dir)
        t1 = coord.create_collaboration("task1", ["a1"])
        t2 = coord.create_collaboration("task2", ["a2"])
        coord.complete_collaboration(t1.collaboration_id)
        active = coord.list_tasks(status=CollaborationStatus.ACTIVE)
        completed = coord.list_tasks(status=CollaborationStatus.COMPLETED)
        assert len(active) == 1 and active[0].collaboration_id == t2.collaboration_id
        assert len(completed) == 1 and completed[0].collaboration_id == t1.collaboration_id

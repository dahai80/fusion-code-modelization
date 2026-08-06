from __future__ import annotations

import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.session import (
    Session,
    SessionEngine,
    SessionState,
    SessionStore,
)


class TestSessionState:
    def test_valid_transition_idle_to_running(self):
        s = Session(session_id="t1", name="test")
        assert s.can_transition(SessionState.RUNNING)
        assert s.transition(SessionState.RUNNING)
        assert s.state == SessionState.RUNNING

    def test_invalid_transition_idle_to_completed(self):
        s = Session(session_id="t1", name="test")
        assert not s.can_transition(SessionState.COMPLETED)
        assert not s.transition(SessionState.COMPLETED)
        assert s.state == SessionState.IDLE

    def test_full_lifecycle(self):
        s = Session(session_id="t1", name="test")
        assert s.transition(SessionState.RUNNING)
        assert s.transition(SessionState.WAITING_APPROVAL)
        assert s.transition(SessionState.RUNNING)
        assert s.transition(SessionState.COMPLETED)

    def test_failed_can_reset_to_idle(self):
        s = Session(session_id="t1", name="test", state=SessionState.FAILED)
        assert s.transition(SessionState.IDLE)

    def test_completed_is_terminal(self):
        s = Session(session_id="t1", name="test", state=SessionState.COMPLETED)
        assert not s.can_transition(SessionState.RUNNING)


class TestSession:
    def test_add_message(self):
        s = Session(session_id="t1", name="test")
        s.add_message("user", "hello")
        s.add_message("assistant", "hi there")
        assert len(s.messages) == 2
        assert s.messages[0].role == "user"
        assert s.messages[1].content == "hi there"

    def test_to_dict(self):
        s = Session(session_id="t1", name="test")
        d = s.to_dict()
        assert d["session_id"] == "t1"
        assert d["state"] == "idle"
        assert "config" in d


class TestSessionStore:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            session = Session(session_id="s1", name="test-session")
            store.save(session)
            loaded = store.load("s1")
            assert loaded is not None
            assert loaded.session_id == "s1"
            assert loaded.name == "test-session"

    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            assert store.load("nonexistent") is None

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            session = Session(session_id="s1", name="test")
            store.save(session)
            assert store.delete("s1")
            assert store.load("s1") is None

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            store.save(Session(session_id="s1", name="a"))
            store.save(Session(session_id="s2", name="b"))
            sessions = store.list_sessions()
            assert len(sessions) == 2

    def test_list_by_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            s1 = Session(session_id="s1", name="a", state=SessionState.RUNNING)
            s2 = Session(session_id="s2", name="b", state=SessionState.IDLE)
            store.save(s1)
            store.save(s2)
            running = store.list_by_state(SessionState.RUNNING)
            assert len(running) == 1
            assert running[0].session_id == "s1"


class TestSessionEngine:
    def test_create_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test-session", working_dir="/tmp")
            assert session.name == "test-session"
            assert session.state == SessionState.IDLE

    def test_start_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            assert engine.start(session.session_id)
            loaded = engine.get_session(session.session_id)
            assert loaded.state == SessionState.RUNNING

    def test_pause_resume(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            engine.start(session.session_id)
            assert engine.pause(session.session_id)
            assert engine.resume(session.session_id)

    def test_complete_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            engine.start(session.session_id)
            assert engine.complete(session.session_id)

    def test_fail_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            engine.start(session.session_id)
            assert engine.fail(session.session_id, "something went wrong")
            loaded = engine.get_session(session.session_id)
            assert loaded.state == SessionState.FAILED
            assert loaded.error == "something went wrong"

    def test_approval_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            engine.start(session.session_id)
            assert engine.request_approval(session.session_id)
            loaded = engine.get_session(session.session_id)
            assert loaded.state == SessionState.WAITING_APPROVAL
            assert engine.approve(session.session_id)
            loaded = engine.get_session(session.session_id)
            assert loaded.state == SessionState.RUNNING

    def test_delete_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            assert engine.delete(session.session_id)
            assert engine.get_session(session.session_id) is None

    def test_clone_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="original", model="test-model")
            session.add_message("user", "hello")
            store.save(session)
            cloned = engine.clone(session.session_id, new_name="cloned")
            assert cloned is not None
            assert cloned.name == "cloned"
            assert cloned.session_id != session.session_id
            assert cloned.config.model == "test-model"

    def test_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            snap = engine.snapshot(session.session_id)
            assert snap is not None
            assert snap["session_id"] == session.session_id

    @pytest.mark.asyncio
    async def test_chat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            with patch.object(
                engine._clients[session.session_id],
                "chat",
                new=AsyncMock(return_value={"status": "completed", "content": "response"}),
            ):
                result = await engine.chat(session.session_id, "hello")
                assert result["status"] == "completed"
            loaded = engine.get_session(session.session_id)
            assert len(loaded.messages) == 2
            assert loaded.messages[0].role == "user"
            assert loaded.messages[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_chat_nonexistent_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            result = await engine.chat("nonexistent", "hello")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_chat_paused_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="test")
            engine.start(session.session_id)
            engine.pause(session.session_id)
            result = await engine.chat(session.session_id, "hello")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_distribute_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="cluster-test")
            with patch(
                "fusion_code_modelization.cluster.scheduler.ClusterScheduler.dispatch_task",
                new=AsyncMock(
                    return_value=type("TD", (), {"to_dict": lambda self: {"task_id": "tk1", "target_node": "node-a"}})()
                ),
            ):
                result = await engine.distribute_session(session.session_id, ["node-a"], "migrate")
            assert result["status"] == "completed"
            assert len(result["dispatches"]) == 1
            loaded = engine.get_session(session.session_id)
            assert loaded.state.value == "cluster_running"
            assert loaded.config.cluster_nodes == ["node-a"]

    @pytest.mark.asyncio
    async def test_distribute_session_no_nodes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="cluster-test")
            result = await engine.distribute_session(session.session_id, [], "migrate")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_distribute_session_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            result = await engine.distribute_session("nope", ["node-a"], "migrate")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_cluster_status_local(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="s")
            result = await engine.cluster_status(session.session_id)
            assert result["status"] == "completed"
            assert result["cluster_state"] == "local"

    @pytest.mark.asyncio
    async def test_cluster_status_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            result = await engine.cluster_status("nope")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_merge_cluster_results_no_nodes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="s")
            result = await engine.merge_cluster_results(session.session_id)
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_merge_cluster_results_with_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=tmpdir)
            engine = SessionEngine(store=store)
            session = engine.create_session(name="s")
            with patch(
                "fusion_code_modelization.cluster.scheduler.ClusterScheduler.dispatch_task",
                new=AsyncMock(
                    return_value=type("TD", (), {"to_dict": lambda self: {"task_id": "tk1", "target_node": "node-a"}})()
                ),
            ):
                await engine.distribute_session(session.session_id, ["node-a"], "migrate")
            fake_task = type(
                "T",
                (),
                {
                    "session_id": session.session_id,
                    "target_node": "node-a",
                    "status": type("S", (), {"value": "completed"})(),
                    "result": {"content": "merged output"},
                    "to_dict": lambda self: {"task_id": "tk1"},
                },
            )()
            with patch(
                "fusion_code_modelization.cluster.scheduler.ClusterScheduler.list_tasks",
                return_value=[fake_task],
            ):
                result = await engine.merge_cluster_results(session.session_id)
            assert result["status"] == "completed"
            assert result["parts"] == 1
            assert "node-a" in result["merged"]
            loaded = engine.get_session(session.session_id)
            assert loaded.state.value == "completed"

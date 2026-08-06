from __future__ import annotations

import tempfile
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from fusion_code_modelization.server import create_app


class TestServerHealth:
    def test_health(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            resp = client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"


class TestServerSessions:
    def test_create_and_get_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            resp = client.post("/api/sessions", json={"name": "api-test"})
            assert resp.status_code == 200
            sid = resp.json()["session_id"]
            got = client.get(f"/api/sessions/{sid}")
            assert got.status_code == 200
            assert got.json()["session_id"] == sid

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            client.post("/api/sessions", json={"name": "a"})
            client.post("/api/sessions", json={"name": "b"})
            resp = client.get("/api/sessions")
            assert resp.status_code == 200
            assert len(resp.json()) >= 2

    def test_get_session_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            resp = client.get("/api/sessions/nonexistent")
            assert resp.status_code == 404

    def test_session_actions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "s"}).json()["session_id"]
            assert client.post(f"/api/sessions/{sid}/start").status_code == 200
            assert client.post(f"/api/sessions/{sid}/pause").status_code == 200
            assert client.post(f"/api/sessions/{sid}/resume").status_code == 200
            assert client.post(f"/api/sessions/{sid}/complete").status_code == 200

    def test_session_clone(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "orig"}).json()["session_id"]
            resp = client.post(f"/api/sessions/{sid}/clone")
            assert resp.status_code == 200
            assert resp.json()["session_id"] != sid

    def test_session_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "s"}).json()["session_id"]
            resp = client.post(f"/api/sessions/{sid}/delete")
            assert resp.status_code == 200
            assert resp.json()["deleted"] is True

    def test_unknown_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "s"}).json()["session_id"]
            resp = client.post(f"/api/sessions/{sid}/bogus")
            assert resp.status_code == 400


class TestServerChat:
    def test_chat_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "s"}).json()["session_id"]
            with patch(
                "fusion_code_modelization.session.engine.MLXClient.chat",
                new=AsyncMock(return_value={"status": "completed", "content": "hi"}),
            ):
                resp = client.post(f"/api/sessions/{sid}/chat", json={"message": "hello"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "completed"

    def test_chat_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            resp = client.post("/api/sessions/nope/chat", json={"message": "hello"})
            assert resp.status_code == 400

    def test_ws_chat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "s"}).json()["session_id"]
            with (
                patch(
                    "fusion_code_modelization.session.engine.MLXClient.chat",
                    new=AsyncMock(return_value={"status": "completed", "content": "ok"}),
                ),
                client.websocket_connect("/ws/chat") as ws,
            ):
                ws.send_json({"session_id": sid, "message": "hi"})
                data = ws.receive_json()
                assert data["status"] == "completed"


class TestServerCluster:
    def test_cluster_status_local(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "s"}).json()["session_id"]
            resp = client.get(f"/api/sessions/{sid}/cluster-status")
            assert resp.status_code == 200
            assert resp.json()["cluster_state"] == "local"

    def test_distribute_and_merge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "s"}).json()["session_id"]
            with patch(
                "fusion_code_modelization.cluster.scheduler.ClusterScheduler.dispatch_task",
                new=AsyncMock(
                    return_value=type("TD", (), {"to_dict": lambda self: {"task_id": "tk1", "target_node": "node-a"}})()
                ),
            ):
                resp = client.post(f"/api/sessions/{sid}/distribute", json={"nodes": ["node-a"], "description": "m"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "completed"
            fake_task = type(
                "T",
                (),
                {
                    "session_id": sid,
                    "target_node": "node-a",
                    "status": type("S", (), {"value": "completed"})(),
                    "result": {"content": "out"},
                    "to_dict": lambda self: {"task_id": "tk1"},
                },
            )()
            with patch(
                "fusion_code_modelization.cluster.scheduler.ClusterScheduler.list_tasks",
                return_value=[fake_task],
            ):
                mresp = client.post(f"/api/sessions/{sid}/merge")
            assert mresp.status_code == 200
            assert mresp.json()["parts"] == 1

    def test_distribute_no_nodes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            sid = client.post("/api/sessions", json={"name": "s"}).json()["session_id"]
            resp = client.post(f"/api/sessions/{sid}/distribute", json={"nodes": []})
            assert resp.status_code == 400


class TestServerWorkflow:
    def test_run_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir, mlx_url="http://localhost:11434/v1")
            client = TestClient(app)
            fake_result = type(
                "R",
                (),
                {
                    "plan_id": "plan_12345",
                    "status": "completed",
                    "to_dict": lambda self: {"plan_id": "plan_12345", "status": "completed"},
                },
            )()
            with patch(
                "fusion_code_modelization.workflow.executor.WorkflowExecutor.run_workflow",
                new=AsyncMock(return_value=fake_result),
            ):
                resp = client.post("/api/workflows/run", json={"goal": "migrate code"})
            assert resp.status_code == 200
            assert resp.json()["plan_id"] == "plan_12345"
            got = client.get("/api/workflows/plan_12345")
            assert got.status_code == 200

    def test_get_workflow_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(base_dir=tmpdir)
            client = TestClient(app)
            resp = client.get("/api/workflows/unknown")
            assert resp.status_code == 404

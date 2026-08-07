from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from fusion_code_modelization.session import SessionEngine, SessionStore
from fusion_code_modelization.workflow import WorkflowExecutor

logger = logging.getLogger(__name__)

_workflow_results: dict[str, dict[str, Any]] = {}


class SessionCreateRequest(BaseModel):
    name: str = "unnamed"
    description: str = ""


class ChatRequest(BaseModel):
    message: str


class DistributeRequest(BaseModel):
    nodes: list[str]
    description: str = ""


class WorkflowRunRequest(BaseModel):
    goal: str
    context: str = ""
    template: str = "generic"
    max_parallel: int = 4


def create_app(mlx_url: str | None = None, base_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="Fusion-Code-Modelization REST API", version="0.6.3")
    engine = SessionEngine(store=SessionStore(base_dir=base_dir) if base_dir else SessionStore())
    executor = WorkflowExecutor(mlx_url=mlx_url or "http://localhost:11434/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "fusion-code-modelization"}

    @app.get("/api/sessions")
    async def list_sessions() -> list[dict[str, Any]]:
        return [s.to_dict() for s in engine.list_sessions()]

    @app.post("/api/sessions")
    async def create_session(req: SessionCreateRequest) -> dict[str, Any]:
        session = engine.create_session(name=req.name)
        logger.info("API created session %s", session.session_id)
        return session.to_dict()

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, Any]:
        snap = engine.snapshot(session_id)
        if not snap:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return snap

    @app.post("/api/sessions/{session_id}/chat")
    async def chat(session_id: str, req: ChatRequest) -> dict[str, Any]:
        result = await engine.chat(session_id, req.message)
        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("error", "chat failed"))
        return result

    @app.post("/api/sessions/{session_id}/distribute")
    async def distribute(session_id: str, req: DistributeRequest) -> dict[str, Any]:
        result = await engine.distribute_session(session_id, req.nodes, req.description)
        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("error", "distribute failed"))
        return result

    @app.get("/api/sessions/{session_id}/cluster-status")
    async def cluster_status(session_id: str) -> dict[str, Any]:
        result = await engine.cluster_status(session_id)
        if result.get("status") == "failed":
            raise HTTPException(status_code=404, detail=result.get("error", "not found"))
        return result

    @app.post("/api/sessions/{session_id}/merge")
    async def merge(session_id: str) -> dict[str, Any]:
        result = await engine.merge_cluster_results(session_id)
        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("error", "merge failed"))
        return result

    @app.post("/api/sessions/{session_id}/{action}")
    async def session_action(session_id: str, action: str) -> dict[str, Any]:
        simple = {
            "start": engine.start,
            "pause": engine.pause,
            "resume": engine.resume,
            "complete": engine.complete,
            "fail": engine.fail,
        }
        if action in simple:
            try:
                simple[action](session_id)
            except Exception as exc:
                logger.error("session %s action %s failed: %s", session_id, action, exc)
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return engine.snapshot(session_id) or {"session_id": session_id, "action": action}
        if action == "delete":
            engine.delete(session_id)
            return {"session_id": session_id, "deleted": True}
        if action == "clone":
            cloned = engine.clone(session_id)
            return cloned.to_dict()
        raise HTTPException(status_code=400, detail=f"Unknown action {action}")

    @app.post("/api/workflows/run")
    async def run_workflow(req: WorkflowRunRequest) -> dict[str, Any]:
        result = await executor.run_workflow(
            goal=req.goal, context=req.context, template=req.template, max_parallel=req.max_parallel
        )
        data = result.to_dict()
        _workflow_results[result.plan_id] = data
        logger.info("API workflow %s status=%s", result.plan_id, result.status)
        return data

    @app.get("/api/workflows/{plan_id}")
    async def get_workflow(plan_id: str) -> dict[str, Any]:
        if plan_id not in _workflow_results:
            raise HTTPException(status_code=404, detail=f"Workflow {plan_id} not found")
        return _workflow_results[plan_id]

    @app.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                payload = await websocket.receive_json()
                session_id = payload.get("session_id", "")
                message = payload.get("message", "")
                result = await engine.chat(session_id, message)
                await websocket.send_json(result)
        except WebSocketDisconnect:
            logger.info("ws chat disconnected")
        except Exception as exc:
            logger.error("ws chat error: %s", exc)
            await websocket.close()

    return app

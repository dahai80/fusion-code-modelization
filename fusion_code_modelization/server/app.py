from __future__ import annotations

import logging
import os
import shutil
import time
from collections import defaultdict
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fusion_code_modelization import __version__
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL
from fusion_code_modelization.session import SessionEngine, SessionStore
from fusion_code_modelization.workflow import WorkflowExecutor

logger = logging.getLogger(__name__)

_workflow_results: dict[str, dict[str, Any]] = {}

_PUBLIC_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}
MAX_BODY_BYTES = int(os.environ.get("FUSION_MAX_BODY_BYTES", "1048576"))


class _Metrics:
    def __init__(self) -> None:
        self.chat_total = 0
        self.chat_failed = 0
        self.chat_latency_sum = 0.0
        self.chat_latency_count = 0
        self.workflow_total = 0
        self.workflow_failed = 0

    def record_chat(self, latency: float, failed: bool) -> None:
        self.chat_total += 1
        if failed:
            self.chat_failed += 1
        self.chat_latency_sum += latency
        self.chat_latency_count += 1

    def record_workflow(self, failed: bool) -> None:
        self.workflow_total += 1
        if failed:
            self.workflow_failed += 1

    def snapshot(self) -> dict[str, Any]:
        avg = self.chat_latency_sum / self.chat_latency_count if self.chat_latency_count else 0.0
        return {
            "chat_total": self.chat_total,
            "chat_failed": self.chat_failed,
            "chat_avg_latency_ms": round(avg * 1000, 2),
            "workflow_total": self.workflow_total,
            "workflow_failed": self.workflow_failed,
        }


def _resolve_server_api_key() -> str:
    for env_name in ("FUSION_SERVER_API_KEY", "FUSION_MLX_API_KEY", "MLX_API_KEY"):
        key = os.environ.get(env_name, "")
        if key:
            return key
    return ""


def _allowed_hosts() -> set[str]:
    env = os.environ.get("FUSION_ALLOWED_HOSTS", "127.0.0.1,localhost")
    return {h.strip() for h in env.split(",") if h.strip()}


def _origin_allowed(origin: str, allowed: set[str]) -> bool:
    from urllib.parse import urlparse

    host = urlparse(origin).hostname or ""
    return host in allowed


class _RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, client_id: str) -> bool:
        now = time.time()
        bucket = self._hits[client_id]
        cutoff = now - self.window
        self._hits[client_id] = [t for t in bucket if t > cutoff]
        if len(self._hits[client_id]) >= self.max_requests:
            return False
        self._hits[client_id].append(now)
        return True


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


def create_app(
    mlx_url: str | None = None,
    base_dir: str | None = None,
    api_key: str | None = None,
    rate_limit: int = 60,
) -> FastAPI:
    import json
    from contextlib import asynccontextmanager
    from pathlib import Path

    workflow_state_path = Path(os.path.expanduser("~/.fusion/code_mod/workflow_results.json"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if workflow_state_path.exists():
            try:
                _workflow_results.update(json.loads(workflow_state_path.read_text(encoding="utf-8")))
                logger.info("restored %d workflow results from %s", len(_workflow_results), workflow_state_path)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("failed to restore workflow results: %s", e)
        logger.info("server lifespan startup complete")
        yield
        try:
            workflow_state_path.parent.mkdir(parents=True, exist_ok=True)
            workflow_state_path.write_text(
                json.dumps(_workflow_results, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("persisted %d workflow results to %s", len(_workflow_results), workflow_state_path)
        except OSError as e:
            logger.error("failed to persist workflow results: %s", e)
        for sid, client in list(engine._clients.items()):
            try:
                await client.aclose()
            except Exception as e:
                logger.warning("close client %s failed: %s", sid, e)
        try:
            from fusion_core.http_client import close_all

            await close_all()
            logger.info("closed pooled httpx clients")
        except Exception as e:
            logger.warning("close_all failed: %s", e)
        logger.info("server lifespan shutdown complete")

    app = FastAPI(title="Fusion-Code-Modelization REST API", version=__version__, lifespan=lifespan)
    engine = SessionEngine(store=SessionStore(base_dir=base_dir) if base_dir else SessionStore())
    gateway_url = mlx_url or DEFAULT_GATEWAY_URL
    executor = WorkflowExecutor(mlx_url=gateway_url)
    expected_key = api_key if api_key is not None else _resolve_server_api_key()
    limiter = _RateLimiter(max_requests=rate_limit)
    allowed_hosts = _allowed_hosts()
    metrics = _Metrics()
    auth_enabled = bool(expected_key)
    logger.info("server auth enabled=%s", auth_enabled)

    @app.middleware("http")
    async def auth_and_rate_limit(request: Request, call_next):
        from fastapi.responses import JSONResponse

        path = request.url.path
        client_id = request.client.host if request.client else "unknown"
        if not limiter.allow(client_id):
            logger.warning("rate limit exceeded for %s on %s", client_id, path)
            return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
        if path in _PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)
        if auth_enabled:
            header = request.headers.get("Authorization", "")
            token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
            if not token or token != expected_key:
                logger.warning("auth rejected for %s on %s", client_id, path)
                return JSONResponse(status_code=401, content={"detail": "invalid or missing bearer token"})
        return await call_next(request)

    @app.middleware("http")
    async def host_guard(request: Request, call_next):
        # Added last → runs first (outermost): reject oversized bodies and
        # misdirected hosts BEFORE spending auth/rate-limit budget on them.
        from fastapi.responses import JSONResponse

        cl = request.headers.get("content-length", "")
        if cl.isdigit() and int(cl) > MAX_BODY_BYTES:
            logger.warning("body size %s exceeds limit %d on %s", cl, MAX_BODY_BYTES, request.url.path)
            return JSONResponse(status_code=413, content={"detail": "request body too large"})
        host = request.headers.get("host", "").split(":")[0]
        if host and host not in allowed_hosts:
            logger.warning("host guard rejected host=%s", host)
            return JSONResponse(status_code=421, content={"detail": "misdirected request"})
        origin = request.headers.get("origin", "")
        if origin and not _origin_allowed(origin, allowed_hosts):
            logger.warning("CORS rejected origin=%s", origin)
            resp = await call_next(request)
            resp.headers["Access-Control-Allow-Origin"] = "null"
            return resp
        resp = await call_next(request)
        resp.headers["Access-Control-Allow-Origin"] = (
            origin if origin and _origin_allowed(origin, allowed_hosts) else "null"
        )
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        return resp

    @app.get("/health")
    async def health(request: Request) -> JSONResponse:
        checks: dict[str, Any] = {"service": "fusion-code-modelization"}
        healthy = True

        try:
            async with httpx.AsyncClient(timeout=3.0) as hc:
                resp = await hc.get(f"{gateway_url.rstrip('/')}/models")
            if resp.status_code == 200:
                checks["gateway"] = "ok"
            else:
                checks["gateway"] = f"HTTP {resp.status_code}"
                healthy = False
        except Exception as e:
            checks["gateway"] = f"unreachable: {type(e).__name__}"
            healthy = False

        try:
            usage = shutil.disk_usage(os.path.expanduser("~"))
            free_gb = round(usage.free / (1024**3), 2)
            checks["disk_free_gb"] = free_gb
            if free_gb < 1.0:
                checks["disk"] = "low"
                healthy = False
            else:
                checks["disk"] = "ok"
        except Exception as e:
            checks["disk"] = f"error: {type(e).__name__}"

        checks["status"] = "ok" if healthy else "degraded"
        status_code = 200 if healthy else 503
        return JSONResponse(status_code=status_code, content=checks)

    @app.get("/metrics")
    async def metrics_endpoint() -> dict[str, Any]:
        return metrics.snapshot()

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
        start = time.perf_counter()
        result = await engine.chat(session_id, req.message)
        latency = time.perf_counter() - start
        failed = result.get("status") == "failed"
        metrics.record_chat(latency, failed)
        if failed:
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
            if cloned is None:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found for clone")
            return cloned.to_dict()
        raise HTTPException(status_code=400, detail=f"Unknown action {action}")

    @app.post("/api/workflows/run")
    async def run_workflow(req: WorkflowRunRequest) -> dict[str, Any]:
        result = await executor.run_workflow(
            goal=req.goal, context=req.context, template=req.template, max_parallel=req.max_parallel
        )
        data = result.to_dict()
        metrics.record_workflow(result.status not in ("completed", "succeeded", "success"))
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
        if auth_enabled:
            token = websocket.query_params.get("token", "")
            if not token or token != expected_key:
                logger.warning("ws auth rejected")
                await websocket.close(code=4401)
                return
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

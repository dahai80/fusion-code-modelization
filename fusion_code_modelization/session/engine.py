from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import ModelConfig
from fusion_code_modelization.core.progress import emit_complete, emit_error, emit_start

from .state import Session, SessionConfig, SessionState
from .store import SessionStore

logger = logging.getLogger(__name__)


class SessionEngine:
    def __init__(self, store: SessionStore | None = None):
        self._store = store or SessionStore()
        self._clients: dict[str, MLXClient] = {}

    def create_session(
        self,
        name: str = "",
        working_dir: str = "",
        model: str = "qwen3.5-9b",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        security_mode: str = "manual",
        allowed_dirs: list[str] | None = None,
    ) -> Session:
        session_id = uuid.uuid4().hex[:12]
        now = time.time()
        config = SessionConfig(
            session_id=session_id,
            name=name or f"session-{session_id[:6]}",
            working_dir=working_dir,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            security_mode=security_mode,
            allowed_dirs=allowed_dirs or [],
        )
        session = Session(
            session_id=session_id,
            name=config.name,
            config=config,
            created_at=now,
            updated_at=now,
        )
        self._store.save(session)
        self._clients[session_id] = MLXClient(
            ModelConfig(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )
        logger.info("Session created: %s (%s)", session_id, config.name)
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._store.load(session_id)

    def list_sessions(self) -> list[Session]:
        return self._store.list_sessions()

    def list_by_state(self, state: SessionState) -> list[Session]:
        return self._store.list_by_state(state)

    def start(self, session_id: str) -> bool:
        session = self._store.load(session_id)
        if not session:
            return False
        if not session.transition(SessionState.RUNNING):
            return False
        self._store.save(session)
        return True

    def pause(self, session_id: str) -> bool:
        session = self._store.load(session_id)
        if not session:
            return False
        if not session.transition(SessionState.PAUSED):
            return False
        self._store.save(session)
        return True

    def resume(self, session_id: str) -> bool:
        session = self._store.load(session_id)
        if not session:
            return False
        if not session.transition(SessionState.RUNNING):
            return False
        self._store.save(session)
        return True

    def complete(self, session_id: str) -> bool:
        session = self._store.load(session_id)
        if not session:
            return False
        if not session.transition(SessionState.COMPLETED):
            return False
        self._store.save(session)
        return True

    def fail(self, session_id: str, error: str = "") -> bool:
        session = self._store.load(session_id)
        if not session:
            return False
        if not session.transition(SessionState.FAILED):
            return False
        session.error = error
        self._store.save(session)
        return True

    def request_approval(self, session_id: str) -> bool:
        session = self._store.load(session_id)
        if not session:
            return False
        if not session.transition(SessionState.WAITING_APPROVAL):
            return False
        self._store.save(session)
        return True

    def approve(self, session_id: str) -> bool:
        session = self._store.load(session_id)
        if not session:
            return False
        if not session.transition(SessionState.RUNNING):
            return False
        self._store.save(session)
        return True

    def delete(self, session_id: str) -> bool:
        if session_id in self._clients:
            del self._clients[session_id]
        return self._store.delete(session_id)

    def clone(self, session_id: str, new_name: str = "") -> Session | None:
        source = self._store.load(session_id)
        if not source:
            return None
        cloned = self.create_session(
            name=new_name or f"{source.name}-clone",
            working_dir=source.config.working_dir,
            model=source.config.model,
            temperature=source.config.temperature,
            max_tokens=source.config.max_tokens,
            security_mode=source.config.security_mode,
            allowed_dirs=list(source.config.allowed_dirs),
        )
        for msg in source.messages:
            cloned.messages.append(msg)
        self._store.save(cloned)
        logger.info("Session cloned: %s → %s", session_id, cloned.session_id)
        return cloned

    async def chat(self, session_id: str, prompt: str, *, progress_callback=None, **kwargs) -> dict[str, Any]:
        session = self._store.load(session_id)
        if not session:
            return {"status": "failed", "error": f"Session {session_id} not found"}
        if session.state not in (SessionState.RUNNING, SessionState.IDLE):
            return {"status": "failed", "error": f"Session is {session.state.value}, cannot chat"}

        if session.state == SessionState.IDLE:
            session.transition(SessionState.RUNNING)

        client = self._clients.get(session_id)
        if not client:
            client = MLXClient(
                ModelConfig(
                    model=session.config.model,
                    temperature=session.config.temperature,
                    max_tokens=session.config.max_tokens,
                )
            )
            self._clients[session_id] = client

        emit_start("chat", f"session={session_id}", progress_callback)
        session.add_message("user", prompt)
        result = await client.chat(
            messages=[{"role": m.role, "content": m.content} for m in session.messages],
            **kwargs,
        )
        if result["status"] == "completed":
            session.add_message("assistant", result["content"])
            emit_complete("chat", f"session={session_id}", progress_callback)
        else:
            session.error = result.get("error", "")
            emit_error("chat", result.get("error", "Unknown"), progress_callback)
        self._store.save(session)
        return result

    def get_client(self, session_id: str) -> MLXClient | None:
        return self._clients.get(session_id)

    def snapshot(self, session_id: str) -> dict[str, Any] | None:
        session = self._store.load(session_id)
        if not session:
            return None
        return session.to_dict()

    async def distribute_session(self, session_id: str, nodes: list[str], description: str = "") -> dict[str, Any]:
        session = self._store.load(session_id)
        if not session:
            return {"status": "failed", "error": f"Session {session_id} not found"}
        if not nodes:
            return {"status": "failed", "error": "No cluster nodes provided"}
        from fusion_code_modelization.cluster import ClusterScheduler, NodeInfo

        session.config.cluster_nodes = list(nodes)
        if not session.transition(SessionState.CLUSTER_RUNNING):
            return {"status": "failed", "error": f"Cannot transition from {session.state.value} to cluster_running"}
        self._store.save(session)

        scheduler = ClusterScheduler()
        dispatches = []
        for node_id in nodes:
            node = scheduler._nodes.get(node_id)
            if not node:
                node = NodeInfo(node_id=node_id)
                scheduler.register_node(node)
            task = await scheduler.dispatch_task(session_id, node_id, description or session.name)
            dispatches.append(task.to_dict())
        logger.info("Distributed session %s to %d nodes", session_id, len(nodes))
        return {"status": "completed", "session_id": session_id, "dispatches": dispatches}

    async def cluster_status(self, session_id: str) -> dict[str, Any]:
        session = self._store.load(session_id)
        if not session:
            return {"status": "failed", "error": f"Session {session_id} not found"}
        nodes = session.config.cluster_nodes
        if not nodes:
            return {"status": "completed", "session_id": session_id, "cluster_state": "local", "nodes": []}
        from fusion_code_modelization.cluster import ClusterScheduler

        scheduler = ClusterScheduler()
        tasks = [t for t in scheduler.list_tasks() if t.session_id == session_id]
        return {
            "status": "completed",
            "session_id": session_id,
            "cluster_state": session.state.value,
            "nodes": nodes,
            "tasks": [t.to_dict() for t in tasks],
        }

    async def merge_cluster_results(self, session_id: str) -> dict[str, Any]:
        session = self._store.load(session_id)
        if not session:
            return {"status": "failed", "error": f"Session {session_id} not found"}
        nodes = session.config.cluster_nodes
        if not nodes:
            return {"status": "failed", "error": "Session has no cluster nodes"}
        from fusion_code_modelization.cluster import ClusterScheduler

        scheduler = ClusterScheduler()
        tasks = [t for t in scheduler.list_tasks() if t.session_id == session_id and t.status.value == "completed"]
        outputs = []
        for t in tasks:
            result = t.result or {}
            content = result.get("content") or result.get("output") or ""
            if content:
                outputs.append({"node": t.target_node, "output": content})
        merged = "\n---\n".join(f"[{o['node']}]: {o['output']}" for o in outputs)
        session.transition(SessionState.COMPLETED)
        self._store.save(session)
        logger.info("Merged %d cluster results for session %s", len(outputs), session_id)
        return {"status": "completed", "session_id": session_id, "merged": merged, "parts": len(outputs)}

from __future__ import annotations

import logging
from typing import Any

import httpx

from .models import NodeInfo, NodeStatus

logger = logging.getLogger(__name__)


class NodeClient:
    def __init__(self, default_timeout: float = 10.0):
        self.default_timeout = default_timeout

    async def health_check(self, node: NodeInfo) -> bool:
        url = f"http://{node.host}:{node.port}/v1/models"
        try:
            async with httpx.AsyncClient(timeout=self.default_timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    node.status = NodeStatus.ONLINE
                    return True
        except Exception as e:
            logger.warning("health_check failed for %s: %s", node.node_id, e)
        node.status = NodeStatus.OFFLINE
        return False

    async def submit_task(
        self, node: NodeInfo, session_id: str, description: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"http://{node.host}:{node.port}/v1/chat/completions"
        payload = {
            "model": "qwen3.5-9b",
            "messages": [{"role": "user", "content": description}],
            **(params or {}),
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return {"status": "completed", "content": content, "node": node.node_id}
        except Exception as e:
            logger.error("submit_task failed on %s: %s", node.node_id, e)
            return {"status": "failed", "error": str(e), "node": node.node_id}

    async def get_task_status(self, node: NodeInfo, task_id: str) -> dict[str, Any]:
        url = f"http://{node.host}:{node.port}/api/tasks/{task_id}"
        try:
            async with httpx.AsyncClient(timeout=self.default_timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("get_task_status failed on %s: %s", node.node_id, e)
            return {"status": "unknown", "error": str(e)}

    async def fetch_result(self, node: NodeInfo, task_id: str) -> dict[str, Any]:
        url = f"http://{node.host}:{node.port}/api/tasks/{task_id}/result"
        try:
            async with httpx.AsyncClient(timeout=self.default_timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("fetch_result failed on %s: %s", node.node_id, e)
            return {"status": "failed", "error": str(e)}

    async def get_node_load(self, node: NodeInfo) -> NodeInfo:
        url = f"http://{node.host}:{node.port}/api/status"
        try:
            async with httpx.AsyncClient(timeout=self.default_timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                node.cpu_percent = data.get("cpu_percent", 0.0)
                node.memory_percent = data.get("memory_percent", 0.0)
                node.gpu_memory_percent = data.get("gpu_memory_percent", 0.0)
                node.loaded_models = data.get("loaded_models", [])
                node.active_tasks = data.get("active_tasks", 0)
        except Exception as e:
            logger.warning("get_node_load failed for %s: %s", node.node_id, e)
        return node

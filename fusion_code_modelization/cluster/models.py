from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class NodeStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class TaskDispatchStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MIGRATED = "migrated"


@dataclass
class NodeInfo:
    node_id: str
    host: str = "localhost"
    port: int = 11434
    status: NodeStatus = NodeStatus.ONLINE
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_memory_percent: float = 0.0
    loaded_models: list[str] = field(default_factory=list)
    active_tasks: int = 0
    last_heartbeat: str = ""

    def __post_init__(self):
        if not self.last_heartbeat:
            self.last_heartbeat = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "status": self.status.value,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "gpu_memory_percent": self.gpu_memory_percent,
            "loaded_models": self.loaded_models,
            "active_tasks": self.active_tasks,
            "last_heartbeat": self.last_heartbeat,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeInfo:
        return cls(
            node_id=data.get("node_id", ""),
            host=data.get("host", "localhost"),
            port=data.get("port", 11434),
            status=NodeStatus(data.get("status", "offline")),
            cpu_percent=data.get("cpu_percent", 0.0),
            memory_percent=data.get("memory_percent", 0.0),
            gpu_memory_percent=data.get("gpu_memory_percent", 0.0),
            loaded_models=data.get("loaded_models", []),
            active_tasks=data.get("active_tasks", 0),
            last_heartbeat=data.get("last_heartbeat", ""),
        )

    @property
    def load_score(self) -> float:
        return (self.cpu_percent + self.memory_percent + self.gpu_memory_percent) / 3.0


@dataclass
class TaskDispatch:
    task_id: str
    session_id: str
    target_node: str
    status: TaskDispatchStatus = TaskDispatchStatus.PENDING
    description: str = ""
    created_at: str = ""
    completed_at: str = ""
    result: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "target_node": self.target_node,
            "status": self.status.value,
            "description": self.description,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskDispatch:
        return cls(
            task_id=data.get("task_id", ""),
            session_id=data.get("session_id", ""),
            target_node=data.get("target_node", ""),
            status=TaskDispatchStatus(data.get("status", "pending")),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at", ""),
            result=data.get("result", {}),
        )

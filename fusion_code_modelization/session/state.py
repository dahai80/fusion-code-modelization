from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class SessionState(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    CLUSTER_RUNNING = "cluster_running"
    COMPLETED = "completed"
    FAILED = "failed"


_VALID_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.IDLE: {SessionState.RUNNING, SessionState.CLUSTER_RUNNING},
    SessionState.RUNNING: {
        SessionState.WAITING_APPROVAL,
        SessionState.PAUSED,
        SessionState.CLUSTER_RUNNING,
        SessionState.COMPLETED,
        SessionState.FAILED,
    },
    SessionState.CLUSTER_RUNNING: {
        SessionState.RUNNING,
        SessionState.PAUSED,
        SessionState.COMPLETED,
        SessionState.FAILED,
    },
    SessionState.WAITING_APPROVAL: {SessionState.RUNNING, SessionState.PAUSED, SessionState.FAILED},
    SessionState.PAUSED: {
        SessionState.RUNNING,
        SessionState.CLUSTER_RUNNING,
        SessionState.FAILED,
        SessionState.COMPLETED,
    },
    SessionState.COMPLETED: set(),
    SessionState.FAILED: {SessionState.IDLE},
}


@dataclass
class SessionConfig:
    session_id: str = ""
    name: str = ""
    working_dir: str = ""
    model: str = "qwen3.5-9b"
    temperature: float = 0.1
    max_tokens: int = 4096
    security_mode: str = "manual"
    allowed_dirs: list[str] = field(default_factory=list)
    cluster_nodes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionMessage:
    role: str
    content: str
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    session_id: str
    name: str
    state: SessionState = SessionState.IDLE
    config: SessionConfig = field(default_factory=SessionConfig)
    messages: list[SessionMessage] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    error: str = ""

    def can_transition(self, target: SessionState) -> bool:
        return target in _VALID_TRANSITIONS.get(self.state, set())

    def transition(self, target: SessionState) -> bool:
        if not self.can_transition(target):
            logger.warning(
                "Invalid transition %s → %s for session %s",
                self.state.value,
                target.value,
                self.session_id,
            )
            return False
        logger.info(
            "Session %s: %s → %s",
            self.session_id,
            self.state.value,
            target.value,
        )
        self.state = target
        return True

    def add_message(self, role: str, content: str, **kwargs) -> None:
        import time

        self.messages.append(
            SessionMessage(
                role=role,
                content=content,
                timestamp=time.time(),
                metadata=kwargs,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "state": self.state.value,
            "config": {
                "working_dir": self.config.working_dir,
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "security_mode": self.config.security_mode,
                "allowed_dirs": self.config.allowed_dirs,
                "cluster_nodes": self.config.cluster_nodes,
            },
            "messages": [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

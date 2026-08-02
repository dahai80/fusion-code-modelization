# GateGuard: New file. Importers: fusion_code_modelization/__init__.py, cli/__init__.py, tests/test_agent_comm.py. Affected API: none. Data schemas: re-exports from models. User instruction: Phase 4 V2.0 — agent_comm package init per enhancement doc.

from .channel import AgentChannelManager
from .coordinator import CollaborationCoordinator
from .models import (
    AgentChannel,
    AgentMessage,
    AgentRole,
    CollaborationStatus,
    CollaborationTask,
    MessageType,
)

__all__ = [
    "AgentChannel",
    "AgentChannelManager",
    "AgentMessage",
    "AgentRole",
    "CollaborationCoordinator",
    "CollaborationStatus",
    "CollaborationTask",
    "MessageType",
]

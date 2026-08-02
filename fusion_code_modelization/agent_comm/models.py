# GateGuard: New file. Importers: agent_comm/channel.py, agent_comm/coordinator.py, agent_comm/__init__.py, cli/__init__.py, tests/test_agent_comm.py. Affected API: none. Data schemas: AgentMessage, AgentChannel, CollaborationTask. User instruction: Phase 4 V2.0 — agent_comm models per enhancement doc.

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime


class MessageType(enum.StrEnum):
    TASK_ASSIGNMENT = "task_assignment"
    RESULT_DELIVERY = "result_delivery"
    STATUS_UPDATE = "status_update"
    CONFLICT_REPORT = "conflict_report"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    HEARTBEAT = "heartbeat"


class CollaborationStatus(enum.StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class AgentRole(enum.StrEnum):
    LEAD = "lead"
    WORKER = "worker"
    REVIEWER = "reviewer"
    INTEGRATOR = "integrator"


@dataclass
class AgentMessage:
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sender_id: str = ""
    recipient_id: str = ""
    channel_name: str = ""
    message_type: MessageType = MessageType.STATUS_UPDATE
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "channel_name": self.channel_name,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentMessage:
        return cls(
            message_id=data.get("message_id", uuid.uuid4().hex[:12]),
            sender_id=data.get("sender_id", ""),
            recipient_id=data.get("recipient_id", ""),
            channel_name=data.get("channel_name", ""),
            message_type=MessageType(data.get("message_type", "status_update")),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class AgentChannel:
    name: str = ""
    participants: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "participants": self.participants,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentChannel:
        return cls(
            name=data.get("name", ""),
            participants=data.get("participants", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            is_active=data.get("is_active", True),
        )


@dataclass
class CollaborationTask:
    collaboration_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_description: str = ""
    agent_ids: list[str] = field(default_factory=list)
    roles: dict[str, AgentRole] = field(default_factory=dict)
    status: CollaborationStatus = CollaborationStatus.PENDING
    results: dict[str, dict] = field(default_factory=dict)
    channel_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "collaboration_id": self.collaboration_id,
            "task_description": self.task_description,
            "agent_ids": self.agent_ids,
            "roles": {k: v.value for k, v in self.roles.items()},
            "status": self.status.value,
            "results": self.results,
            "channel_name": self.channel_name,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CollaborationTask:
        roles = {}
        for k, v in data.get("roles", {}).items():
            roles[k] = AgentRole(v) if isinstance(v, str) else v
        return cls(
            collaboration_id=data.get("collaboration_id", uuid.uuid4().hex[:12]),
            task_description=data.get("task_description", ""),
            agent_ids=data.get("agent_ids", []),
            roles=roles,
            status=CollaborationStatus(data.get("status", "pending")),
            results=data.get("results", {}),
            channel_name=data.get("channel_name", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )

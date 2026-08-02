# GateGuard: New file. Importers: agent_comm/__init__.py, cli/__init__.py, tests/test_agent_comm.py. Affected API: none. Data schemas: CollaborationTask. User instruction: Phase 4 V2.0 — agent_comm coordinator per enhancement doc.

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from .channel import AgentChannelManager
from .models import AgentMessage, AgentRole, CollaborationStatus, CollaborationTask, MessageType

logger = logging.getLogger(__name__)


class CollaborationCoordinator:
    def __init__(self, state_dir: str | Path = ".agent_comm_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.channel_manager = AgentChannelManager(state_dir=self.state_dir)
        self._tasks_path = self.state_dir / "tasks.jsonl"
        self._tasks: dict[str, CollaborationTask] = {}
        self._load()

    def create_collaboration(
        self,
        task_description: str,
        agent_ids: list[str],
        roles: dict[str, AgentRole] | None = None,
    ) -> CollaborationTask:
        if not roles:
            roles = {}
            if agent_ids:
                roles[agent_ids[0]] = AgentRole.LEAD
            for aid in agent_ids[1:]:
                roles[aid] = AgentRole.WORKER
        channel_name = f"collab_{uuid.uuid4().hex[:8]}"
        self.channel_manager.create_channel(channel_name, agent_ids)
        task = CollaborationTask(
            task_description=task_description,
            agent_ids=agent_ids,
            roles=roles,
            status=CollaborationStatus.ACTIVE,
            channel_name=channel_name,
        )
        self._tasks[task.collaboration_id] = task
        self._append_task(task)
        self.channel_manager.broadcast(
            sender_id="coordinator",
            channel_name=channel_name,
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={
                "collaboration_id": task.collaboration_id,
                "description": task_description,
                "roles": {k: v.value for k, v in roles.items()},
            },
        )
        logger.info("created collaboration %s with %d agents", task.collaboration_id, len(agent_ids))
        return task

    def get_task(self, collaboration_id: str) -> CollaborationTask | None:
        return self._tasks.get(collaboration_id)

    def list_tasks(self, status: CollaborationStatus | None = None) -> list[CollaborationTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def submit_result(self, collaboration_id: str, agent_id: str, result: dict) -> bool:
        task = self._tasks.get(collaboration_id)
        if not task:
            logger.warning("collaboration not found: %s", collaboration_id)
            return False
        task.results[agent_id] = result
        msg = AgentMessage(
            sender_id=agent_id,
            recipient_id="coordinator",
            channel_name=task.channel_name,
            message_type=MessageType.RESULT_DELIVERY,
            payload=result,
        )
        self.channel_manager.send_message(msg)
        logger.info("agent %s submitted result for %s", agent_id, collaboration_id)
        return True

    def report_conflict(self, collaboration_id: str, agent_id: str, conflict_details: dict) -> bool:
        task = self._tasks.get(collaboration_id)
        if not task:
            logger.warning("collaboration not found: %s", collaboration_id)
            return False
        task.status = CollaborationStatus.CONFLICT
        self.channel_manager.broadcast(
            sender_id="coordinator",
            channel_name=task.channel_name,
            message_type=MessageType.CONFLICT_REPORT,
            payload={"collaboration_id": collaboration_id, "reporter": agent_id, "details": conflict_details},
        )
        logger.warning("conflict reported in %s by %s", collaboration_id, agent_id)
        return True

    def resolve_conflict(self, collaboration_id: str, resolution: dict) -> bool:
        task = self._tasks.get(collaboration_id)
        if not task or task.status != CollaborationStatus.CONFLICT:
            logger.warning("cannot resolve: collaboration %s not in conflict", collaboration_id)
            return False
        task.status = CollaborationStatus.ACTIVE
        self.channel_manager.broadcast(
            sender_id="coordinator",
            channel_name=task.channel_name,
            message_type=MessageType.SYNC_RESPONSE,
            payload={"collaboration_id": collaboration_id, "resolution": resolution},
        )
        logger.info("conflict resolved in %s", collaboration_id)
        return True

    def complete_collaboration(self, collaboration_id: str) -> bool:
        task = self._tasks.get(collaboration_id)
        if not task:
            logger.warning("collaboration not found: %s", collaboration_id)
            return False
        task.status = CollaborationStatus.COMPLETED
        self.channel_manager.close_channel(task.channel_name)
        logger.info("completed collaboration %s", collaboration_id)
        return True

    def fail_collaboration(self, collaboration_id: str, reason: str = "") -> bool:
        task = self._tasks.get(collaboration_id)
        if not task:
            logger.warning("collaboration not found: %s", collaboration_id)
            return False
        task.status = CollaborationStatus.FAILED
        self.channel_manager.close_channel(task.channel_name)
        logger.info("failed collaboration %s: %s", collaboration_id, reason)
        return True

    def get_agent_role(self, collaboration_id: str, agent_id: str) -> AgentRole | None:
        task = self._tasks.get(collaboration_id)
        if not task:
            return None
        return task.roles.get(agent_id)

    def _append_task(self, task: CollaborationTask):
        with open(self._tasks_path, "a") as f:
            f.write(json.dumps(task.to_dict()) + "\n")

    def _load(self):
        if not self._tasks_path.exists():
            return
        with open(self._tasks_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    t = CollaborationTask.from_dict(json.loads(line))
                    self._tasks[t.collaboration_id] = t
                except Exception as e:
                    logger.warning("failed to load task: %s", e)

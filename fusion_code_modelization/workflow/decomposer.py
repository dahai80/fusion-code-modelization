from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ..core.client import MLXClient
from ..core.config import DEFAULT_GATEWAY_URL, ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    task_id: str
    title: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    priority: int = 0
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "depends_on": self.depends_on,
            "priority": self.priority,
            "status": self.status,
        }


@dataclass
class WorkflowPlan:
    plan_id: str
    goal: str
    subtasks: list[SubTask] = field(default_factory=list)
    status: str = "planned"
    template: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "status": self.status,
            "template": self.template,
        }

    def ready_tasks(self) -> list[SubTask]:
        completed = {t.task_id for t in self.subtasks if t.status == "completed"}
        return [t for t in self.subtasks if t.status == "pending" and all(d in completed for d in t.depends_on)]


DECOMPOSE_PROMPT = """You are a task decomposition engine. Break the following goal into concrete, parallelizable sub-tasks.

Rules:
- Each sub-task must be independently executable
- Specify dependencies between sub-tasks (task_id references)
- Assign priority: 0=highest, 5=lowest
- Return ONLY valid JSON, no markdown

Goal: {goal}

Context: {context}

Template: {template}

Return format:
{{
  "subtasks": [
    {{
      "task_id": "T1",
      "title": "...",
      "description": "...",
      "depends_on": [],
      "priority": 0
    }}
  ]
}}"""


class TaskDecomposer:
    def __init__(self, mlx_url: str = DEFAULT_GATEWAY_URL, client: MLXClient | None = None):
        self._client = client or MLXClient(config=ModelConfig(base_url=mlx_url))

    async def decompose(
        self,
        goal: str,
        context: str = "",
        template: str = "generic",
    ) -> WorkflowPlan:
        logger.info("Decomposing goal: %s (template=%s)", goal[:80], template)
        prompt = DECOMPOSE_PROMPT.format(goal=goal, context=context, template=template)
        response = await self._client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        subtasks = self._parse_subtasks(response)
        plan_id = f"plan_{abs(hash(goal)) % 100000:05d}"
        plan = WorkflowPlan(plan_id=plan_id, goal=goal, subtasks=subtasks, template=template)
        logger.info("Decomposed into %d subtasks: %s", len(subtasks), [t.task_id for t in subtasks])
        return plan

    def _parse_subtasks(self, response: str) -> list[SubTask]:
        try:
            text = self._client.extract_code(response) or response
            data = json.loads(text)
            tasks = []
            for item in data.get("subtasks", []):
                tasks.append(
                    SubTask(
                        task_id=item.get("task_id", "T?"),
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        depends_on=item.get("depends_on", []),
                        priority=item.get("priority", 5),
                    )
                )
            return tasks
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse decompose response: %s", e)
            return []


WORKFLOW_TEMPLATES = {
    "generic": {
        "name": "Generic Task Decomposition",
        "description": "General-purpose task breakdown",
    },
    "legacy_migration": {
        "name": "Legacy System Migration",
        "description": "Migrate legacy code to modern stack",
        "phases": ["analysis", "planning", "migration", "testing", "cleanup"],
    },
    "security_scan": {
        "name": "Security Vulnerability Scan",
        "description": "Comprehensive security audit",
        "phases": ["dependency_scan", "code_scan", "config_scan", "report"],
    },
    "batch_api": {
        "name": "Batch API Refactoring",
        "description": "Bulk API interface modernization",
        "phases": ["api_inventory", "spec_design", "implementation", "migration", "validation"],
    },
}

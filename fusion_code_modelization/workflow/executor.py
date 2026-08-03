from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ..core.client import MLXClient
from ..core.progress import emit_complete, emit_error, emit_progress, emit_start
from .decomposer import SubTask, WorkflowPlan

logger = logging.getLogger(__name__)


@dataclass
class SubTaskResult:
    task_id: str
    status: str = "pending"
    output: str = ""
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class WorkflowResult:
    plan_id: str
    status: str = "running"
    subtask_results: list[SubTaskResult] = field(default_factory=list)
    merged_output: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "subtask_results": [r.to_dict() for r in self.subtask_results],
            "merged_output": self.merged_output,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.subtask_results if r.status == "completed")

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.subtask_results if r.status == "failed")


MERGE_PROMPT = """You are a code integration engine. Merge the following sub-task results into a coherent final output.

Goal: {goal}

Sub-task results:
{results}

Produce a unified summary that:
1. Integrates all code changes
2. Resolves any conflicts
3. Provides a final summary of what was accomplished

Output the merged result:"""


class WorkflowExecutor:
    def __init__(self, mlx_url: str = "http://localhost:11434/v1", client: MLXClient | None = None):
        from ..core.config import ModelConfig

        self._client = client or MLXClient(config=ModelConfig(base_url=mlx_url))
        self._results: dict[str, SubTaskResult] = {}

    async def execute(self, plan: WorkflowPlan, max_parallel: int = 4, *, progress_callback=None) -> WorkflowResult:
        logger.info("Executing workflow %s with %d subtasks", plan.plan_id, len(plan.subtasks))
        emit_start("workflow", f"plan={plan.plan_id} tasks={len(plan.subtasks)}", progress_callback)
        result = WorkflowResult(
            plan_id=plan.plan_id,
            started_at=time.time(),
        )
        plan.status = "running"

        completed_ids: set[str] = set()
        semaphore = asyncio.Semaphore(max_parallel)

        while len(completed_ids) < len(plan.subtasks):
            ready = [
                t
                for t in plan.subtasks
                if t.task_id not in completed_ids
                and t.status == "pending"
                and all(d in completed_ids for d in t.depends_on)
            ]
            if not ready:
                pending = [t for t in plan.subtasks if t.status == "pending"]
                if pending:
                    logger.warning("Deadlock detected: pending tasks %s", [t.task_id for t in pending])
                    for t in pending:
                        t.status = "failed"
                        self._results[t.task_id] = SubTaskResult(
                            task_id=t.task_id,
                            status="failed",
                            error="deadlock",
                        )
                    completed_ids.update(t.task_id for t in pending)
                break

            async def run_task(task: SubTask) -> SubTaskResult:
                async with semaphore:
                    return await self.execute_subtask(task, plan)

            coros = [run_task(t) for t in ready]
            for t in ready:
                t.status = "running"

            task_results = await asyncio.gather(*coros, return_exceptions=True)

            for t, r in zip(ready, task_results, strict=True):
                if isinstance(r, Exception):
                    t.status = "failed"
                    sr = SubTaskResult(task_id=t.task_id, status="failed", error=str(r))
                else:
                    sr = r
                    t.status = sr.status
                self._results[t.task_id] = sr
                completed_ids.add(t.task_id)

            done_count = len(completed_ids)
            total_count = len(plan.subtasks)
            pct = (done_count / total_count * 100) if total_count > 0 else 100.0
            emit_progress("workflow", f"{done_count}/{total_count} tasks done", pct, progress_callback)

        result.subtask_results = list(self._results.values())

        all_ok = all(r.status == "completed" for r in result.subtask_results)
        if all_ok and result.subtask_results:
            result.merged_output = await self.merge_results(plan, result)
            result.status = "completed"
            plan.status = "completed"
            emit_complete("workflow", f"plan={plan.plan_id}", progress_callback)
        else:
            result.status = "partial" if result.success_count > 0 else "failed"
            plan.status = result.status
            emit_error("workflow", f"plan={plan.plan_id} status={result.status}", progress_callback)

        result.completed_at = time.time()
        logger.info(
            "Workflow %s finished: %s (%d ok, %d failed)",
            plan.plan_id,
            result.status,
            result.success_count,
            result.failure_count,
        )
        return result

    async def execute_subtask(self, task: SubTask, plan: WorkflowPlan) -> SubTaskResult:
        logger.info("Executing subtask %s: %s", task.task_id, task.title)
        result = SubTaskResult(task_id=task.task_id, started_at=time.time())

        dep_outputs = ""
        for dep_id in task.depends_on:
            if dep_id in self._results and self._results[dep_id].output:
                dep_outputs += f"\n[Dependency {dep_id} output]:\n{self._results[dep_id].output}\n"

        prompt = (
            f"You are a sub-agent executing a specific task within a larger workflow.\n"
            f"Overall goal: {plan.goal}\n"
            f"Your task: {task.title}\n"
            f"Description: {task.description}\n"
            f"{dep_outputs}\n"
            f"Execute this task and provide your output."
        )

        try:
            response = await self._client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            result.output = response
            result.status = "completed"
        except Exception as e:
            logger.error("Subtask %s failed: %s", task.task_id, e)
            result.error = str(e)
            result.status = "failed"

        result.completed_at = time.time()
        return result

    async def merge_results(self, plan: WorkflowPlan, result: WorkflowResult) -> str:
        logger.info("Merging results for workflow %s", plan.plan_id)
        results_text = "\n---\n".join(f"[{r.task_id}]: {r.output}" for r in result.subtask_results if r.output)
        prompt = MERGE_PROMPT.format(goal=plan.goal, results=results_text)
        try:
            merged = await self._client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return merged
        except Exception as e:
            logger.error("Merge failed for %s: %s", plan.plan_id, e)
            return f"Merge error: {e}"

    async def run_workflow(
        self,
        goal: str,
        context: str = "",
        template: str = "generic",
        max_parallel: int = 4,
        *,
        progress_callback=None,
    ) -> WorkflowResult:
        from .decomposer import TaskDecomposer

        emit_start("run_workflow", f"goal={goal[:60]}", progress_callback)
        decomposer = TaskDecomposer(client=self._client)
        plan = await decomposer.decompose(goal=goal, context=context, template=template)
        result = await self.execute(plan, max_parallel=max_parallel, progress_callback=progress_callback)
        if result.status == "completed":
            emit_complete("run_workflow", f"plan={plan.plan_id}", progress_callback)
        else:
            emit_error("run_workflow", f"plan={plan.plan_id} status={result.status}", progress_callback)
        return result

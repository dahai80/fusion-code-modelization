from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.workflow import (
    WORKFLOW_TEMPLATES,
    SubTask,
    SubTaskResult,
    TaskDecomposer,
    WorkflowExecutor,
    WorkflowPlan,
    WorkflowResult,
)


class TestSubTask:
    def test_to_dict(self):
        t = SubTask(task_id="T1", title="Do X", description="Desc", depends_on=[], priority=0)
        d = t.to_dict()
        assert d["task_id"] == "T1"
        assert d["title"] == "Do X"
        assert d["depends_on"] == []
        assert d["priority"] == 0
        assert d["status"] == "pending"

    def test_defaults(self):
        t = SubTask(task_id="T2", title="Y", description="")
        assert t.depends_on == []
        assert t.priority == 0
        assert t.status == "pending"


class TestWorkflowPlan:
    def test_ready_tasks_no_deps(self):
        t1 = SubTask(task_id="T1", title="A", description="a")
        t2 = SubTask(task_id="T2", title="B", description="b")
        plan = WorkflowPlan(plan_id="p1", goal="g", subtasks=[t1, t2])
        ready = plan.ready_tasks()
        assert len(ready) == 2

    def test_ready_tasks_with_deps(self):
        t1 = SubTask(task_id="T1", title="A", description="a")
        t2 = SubTask(task_id="T2", title="B", description="b", depends_on=["T1"])
        plan = WorkflowPlan(plan_id="p1", goal="g", subtasks=[t1, t2])
        ready = plan.ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "T1"

    def test_ready_tasks_dep_completed(self):
        t1 = SubTask(task_id="T1", title="A", description="a", status="completed")
        t2 = SubTask(task_id="T2", title="B", description="b", depends_on=["T1"])
        plan = WorkflowPlan(plan_id="p1", goal="g", subtasks=[t1, t2])
        ready = plan.ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "T2"

    def test_to_dict(self):
        plan = WorkflowPlan(plan_id="p1", goal="g", template="generic")
        d = plan.to_dict()
        assert d["plan_id"] == "p1"
        assert d["template"] == "generic"

    def test_status_default(self):
        plan = WorkflowPlan(plan_id="p1", goal="g")
        assert plan.status == "planned"


class TestSubTaskResult:
    def test_to_dict(self):
        r = SubTaskResult(task_id="T1", status="completed", output="done")
        d = r.to_dict()
        assert d["task_id"] == "T1"
        assert d["status"] == "completed"
        assert d["output"] == "done"


class TestWorkflowResult:
    def test_success_failure_counts(self):
        r1 = SubTaskResult(task_id="T1", status="completed")
        r2 = SubTaskResult(task_id="T2", status="failed")
        r3 = SubTaskResult(task_id="T3", status="completed")
        wr = WorkflowResult(plan_id="p1", subtask_results=[r1, r2, r3])
        assert wr.success_count == 2
        assert wr.failure_count == 1

    def test_to_dict(self):
        wr = WorkflowResult(plan_id="p1", status="completed")
        d = wr.to_dict()
        assert d["plan_id"] == "p1"
        assert d["status"] == "completed"


class TestTaskDecomposer:
    @pytest.fixture
    def decomposer(self):
        client = MLXClient()
        return TaskDecomposer(client=client)

    @pytest.mark.asyncio
    async def test_decompose(self, decomposer):
        mock_response = json.dumps(
            {
                "subtasks": [
                    {
                        "task_id": "T1",
                        "title": "Analyze",
                        "description": "Analyze code",
                        "depends_on": [],
                        "priority": 0,
                    },
                    {
                        "task_id": "T2",
                        "title": "Migrate",
                        "description": "Migrate code",
                        "depends_on": ["T1"],
                        "priority": 1,
                    },
                ]
            }
        )
        with patch.object(
            decomposer._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": mock_response})
        ):
            plan = await decomposer.decompose(goal="Migrate legacy Python 2 to 3")
        assert plan.plan_id.startswith("plan_")
        assert len(plan.subtasks) == 2
        assert plan.subtasks[0].task_id == "T1"
        assert plan.subtasks[1].depends_on == ["T1"]

    @pytest.mark.asyncio
    async def test_decompose_parse_failure(self, decomposer):
        with (
            patch.object(
                decomposer._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "not json"})
            ),
            patch.object(decomposer._client, "extract_code", return_value=None),
        ):
            plan = await decomposer.decompose(goal="Bad response")
        assert len(plan.subtasks) == 0

    @pytest.mark.asyncio
    async def test_decompose_failed_status(self, decomposer):
        with patch.object(
            decomposer._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "llm_down"})
        ):
            plan = await decomposer.decompose(goal="Down")
        assert len(plan.subtasks) == 0


class TestWorkflowTemplates:
    def test_generic_template_exists(self):
        assert "generic" in WORKFLOW_TEMPLATES
        assert "name" in WORKFLOW_TEMPLATES["generic"]

    def test_legacy_migration_template(self):
        assert "legacy_migration" in WORKFLOW_TEMPLATES
        assert "phases" in WORKFLOW_TEMPLATES["legacy_migration"]

    def test_security_scan_template(self):
        assert "security_scan" in WORKFLOW_TEMPLATES

    def test_batch_api_template(self):
        assert "batch_api" in WORKFLOW_TEMPLATES


class TestWorkflowExecutor:
    @pytest.fixture
    def executor(self):
        client = MLXClient()
        return WorkflowExecutor(client=client)

    @pytest.mark.asyncio
    async def test_execute_simple_plan(self, executor):
        t1 = SubTask(task_id="T1", title="Task 1", description="Do task 1")
        t2 = SubTask(task_id="T2", title="Task 2", description="Do task 2")
        plan = WorkflowPlan(plan_id="p1", goal="Test", subtasks=[t1, t2])
        with patch.object(
            executor._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "result"})
        ):
            result = await executor.execute(plan)
        assert result.status == "completed"
        assert result.success_count == 2
        assert result.failure_count == 0
        assert result.merged_output != ""

    @pytest.mark.asyncio
    async def test_execute_with_dependency(self, executor):
        t1 = SubTask(task_id="T1", title="First", description="Do first")
        t2 = SubTask(task_id="T2", title="Second", description="Do second", depends_on=["T1"])
        plan = WorkflowPlan(plan_id="p2", goal="Dep test", subtasks=[t1, t2])
        with patch.object(
            executor._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "ok"})
        ):
            result = await executor.execute(plan)
        assert result.status == "completed"
        assert result.success_count == 2

    @pytest.mark.asyncio
    async def test_execute_subtask_failure(self, executor):
        t1 = SubTask(task_id="T1", title="Fail", description="Will fail")
        plan = WorkflowPlan(plan_id="p3", goal="Fail test", subtasks=[t1])
        with patch.object(executor._client, "chat", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
            result = await executor.execute(plan)
        assert result.status == "failed"
        assert result.failure_count == 1

    @pytest.mark.asyncio
    async def test_execute_partial_success(self, executor):
        t1 = SubTask(task_id="T1", title="OK", description="Works")
        t2 = SubTask(task_id="T2", title="Fail", description="Fails")
        plan = WorkflowPlan(plan_id="p4", goal="Partial", subtasks=[t1, t2])
        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("fail")
            return {"status": "completed", "content": "ok"}

        with patch.object(executor._client, "chat", new=AsyncMock(side_effect=side_effect)):
            result = await executor.execute(plan)
        assert result.status == "partial"
        assert result.success_count == 1
        assert result.failure_count == 1

    @pytest.mark.asyncio
    async def test_merge_error_fallback(self, executor):
        t1 = SubTask(task_id="T1", title="Task", description="Do it")
        plan = WorkflowPlan(plan_id="p5", goal="Merge fail", subtasks=[t1])
        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise RuntimeError("merge fail")
            return {"status": "completed", "content": "task output"}

        with patch.object(executor._client, "chat", new=AsyncMock(side_effect=side_effect)):
            result = await executor.execute(plan)
        assert "Merge error" in result.merged_output or result.merged_output == "task output"

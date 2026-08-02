# GateGuard: New file. Importers: benchmark/__init__.py, benchmark/runner.py, tests/test_benchmark.py. Affected API: none. Data schemas: BenchmarkSuite, BenchmarkResult, BenchmarkReport, BenchmarkItem. User instruction: Phase 4 V2.0 — benchmark module per enhancement doc.

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime


class BenchmarkCategory(enum.StrEnum):
    CODE_QUALITY = "code_quality"
    PERFORMANCE = "performance"
    MIGRATION_QUALITY = "migration_quality"
    SECURITY = "security"
    CUSTOM = "custom"


class BenchmarkStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class BenchmarkItem:
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: BenchmarkCategory = BenchmarkCategory.CUSTOM
    target_score: float = 0.0
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category.value,
            "target_score": self.target_score,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BenchmarkItem:
        return cls(
            item_id=data.get("item_id", uuid.uuid4().hex[:12]),
            name=data.get("name", ""),
            category=BenchmarkCategory(data.get("category", "custom")),
            target_score=data.get("target_score", 0.0),
            description=data.get("description", ""),
        )


@dataclass
class BenchmarkSuite:
    suite_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: BenchmarkCategory = BenchmarkCategory.CUSTOM
    items: list[BenchmarkItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "suite_id": self.suite_id,
            "name": self.name,
            "category": self.category.value,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BenchmarkSuite:
        return cls(
            suite_id=data.get("suite_id", uuid.uuid4().hex[:12]),
            name=data.get("name", ""),
            category=BenchmarkCategory(data.get("category", "custom")),
            items=[BenchmarkItem.from_dict(i) for i in data.get("items", [])],
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class BenchmarkResult:
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    item_id: str = ""
    suite_id: str = ""
    status: BenchmarkStatus = BenchmarkStatus.PENDING
    score: float = 0.0
    target_score: float = 0.0
    duration_ms: float = 0.0
    metrics: dict = field(default_factory=dict)
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def passed(self) -> bool:
        return self.status == BenchmarkStatus.PASSED and self.score >= self.target_score

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "item_id": self.item_id,
            "suite_id": self.suite_id,
            "status": self.status.value,
            "score": self.score,
            "target_score": self.target_score,
            "duration_ms": self.duration_ms,
            "metrics": self.metrics,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BenchmarkResult:
        return cls(
            result_id=data.get("result_id", uuid.uuid4().hex[:12]),
            item_id=data.get("item_id", ""),
            suite_id=data.get("suite_id", ""),
            status=BenchmarkStatus(data.get("status", "pending")),
            score=data.get("score", 0.0),
            target_score=data.get("target_score", 0.0),
            duration_ms=data.get("duration_ms", 0.0),
            metrics=data.get("metrics", {}),
            error_message=data.get("error_message", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class BenchmarkReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    suite_id: str = ""
    suite_name: str = ""
    results: list[BenchmarkResult] = field(default_factory=list)
    total_items: int = 0
    passed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    error_items: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    total_duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def compute_summary(self) -> None:
        self.total_items = len(self.results)
        self.passed_items = sum(1 for r in self.results if r.status == BenchmarkStatus.PASSED)
        self.failed_items = sum(1 for r in self.results if r.status == BenchmarkStatus.FAILED)
        self.skipped_items = sum(1 for r in self.results if r.status == BenchmarkStatus.SKIPPED)
        self.error_items = sum(1 for r in self.results if r.status == BenchmarkStatus.ERROR)
        self.pass_rate = self.passed_items / self.total_items if self.total_items > 0 else 0.0
        scored = [r.score for r in self.results if r.status in (BenchmarkStatus.PASSED, BenchmarkStatus.FAILED)]
        self.avg_score = sum(scored) / len(scored) if scored else 0.0
        self.total_duration_ms = sum(r.duration_ms for r in self.results)

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "suite_id": self.suite_id,
            "suite_name": self.suite_name,
            "results": [r.to_dict() for r in self.results],
            "total_items": self.total_items,
            "passed_items": self.passed_items,
            "failed_items": self.failed_items,
            "skipped_items": self.skipped_items,
            "error_items": self.error_items,
            "pass_rate": self.pass_rate,
            "avg_score": self.avg_score,
            "total_duration_ms": self.total_duration_ms,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BenchmarkReport:
        report = cls(
            report_id=data.get("report_id", uuid.uuid4().hex[:12]),
            suite_id=data.get("suite_id", ""),
            suite_name=data.get("suite_name", ""),
            results=[BenchmarkResult.from_dict(r) for r in data.get("results", [])],
            total_items=data.get("total_items", 0),
            passed_items=data.get("passed_items", 0),
            failed_items=data.get("failed_items", 0),
            skipped_items=data.get("skipped_items", 0),
            error_items=data.get("error_items", 0),
            pass_rate=data.get("pass_rate", 0.0),
            avg_score=data.get("avg_score", 0.0),
            total_duration_ms=data.get("total_duration_ms", 0.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )
        return report

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        lines = [
            f"# Benchmark Report: {self.suite_name}",
            f"- Suite ID: {self.suite_id}",
            f"- Report ID: {self.report_id}",
            f"- Timestamp: {self.timestamp}",
            "",
            "## Summary",
            f"- Total: {self.total_items}",
            f"- Passed: {self.passed_items}",
            f"- Failed: {self.failed_items}",
            f"- Skipped: {self.skipped_items}",
            f"- Error: {self.error_items}",
            f"- Pass Rate: {self.pass_rate:.1%}",
            f"- Avg Score: {self.avg_score:.2f}",
            f"- Duration: {self.total_duration_ms:.0f}ms",
            "",
            "## Results",
            "| Item | Status | Score | Target | Duration |",
            "|------|--------|-------|--------|----------|",
        ]
        for r in self.results:
            lines.append(
                f"| {r.item_id} | {r.status.value} | {r.score:.2f} | {r.target_score:.2f} | {r.duration_ms:.0f}ms |"
            )
        return "\n".join(lines)

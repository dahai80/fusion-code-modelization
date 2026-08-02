# GateGuard: New file. Importers: benchmark/__init__.py, benchmark/runner.py, tests/test_benchmark.py. Affected API: none. Data schemas: none. User instruction: Phase 4 V2.0 — predefined benchmark suites per enhancement doc.

from __future__ import annotations

from .models import BenchmarkCategory, BenchmarkItem, BenchmarkSuite


class PredefinedBenchmarkSuites:
    @staticmethod
    def code_quality() -> BenchmarkSuite:
        items = [
            BenchmarkItem(
                name="cyclomatic_complexity",
                category=BenchmarkCategory.CODE_QUALITY,
                target_score=10.0,
                description="Max cyclomatic complexity per function",
            ),
            BenchmarkItem(
                name="duplication_ratio",
                category=BenchmarkCategory.CODE_QUALITY,
                target_score=5.0,
                description="Code duplication percentage (lower is better)",
            ),
            BenchmarkItem(
                name="test_coverage",
                category=BenchmarkCategory.CODE_QUALITY,
                target_score=80.0,
                description="Test coverage percentage",
            ),
            BenchmarkItem(
                name="lint_violations",
                category=BenchmarkCategory.CODE_QUALITY,
                target_score=0.0,
                description="Number of lint violations (lower is better)",
            ),
            BenchmarkItem(
                name="type_safety",
                category=BenchmarkCategory.CODE_QUALITY,
                target_score=90.0,
                description="Type safety score percentage",
            ),
        ]
        return BenchmarkSuite(name="code_quality", category=BenchmarkCategory.CODE_QUALITY, items=items)

    @staticmethod
    def performance() -> BenchmarkSuite:
        items = [
            BenchmarkItem(
                name="inference_latency",
                category=BenchmarkCategory.PERFORMANCE,
                target_score=2000.0,
                description="Inference latency in ms (lower is better)",
            ),
            BenchmarkItem(
                name="throughput",
                category=BenchmarkCategory.PERFORMANCE,
                target_score=50.0,
                description="Requests per second",
            ),
            BenchmarkItem(
                name="memory_peak",
                category=BenchmarkCategory.PERFORMANCE,
                target_score=4096.0,
                description="Peak memory usage in MB (lower is better)",
            ),
            BenchmarkItem(
                name="startup_time",
                category=BenchmarkCategory.PERFORMANCE,
                target_score=5000.0,
                description="Cold start time in ms (lower is better)",
            ),
        ]
        return BenchmarkSuite(name="performance", category=BenchmarkCategory.PERFORMANCE, items=items)

    @staticmethod
    def migration_quality() -> BenchmarkSuite:
        items = [
            BenchmarkItem(
                name="syntax_correctness",
                category=BenchmarkCategory.MIGRATION_QUALITY,
                target_score=95.0,
                description="Syntax correctness percentage after migration",
            ),
            BenchmarkItem(
                name="semantic_preservation",
                category=BenchmarkCategory.MIGRATION_QUALITY,
                target_score=90.0,
                description="Semantic preservation score",
            ),
            BenchmarkItem(
                name="api_compatibility",
                category=BenchmarkCategory.MIGRATION_QUALITY,
                target_score=85.0,
                description="API compatibility percentage",
            ),
            BenchmarkItem(
                name="dependency_resolution",
                category=BenchmarkCategory.MIGRATION_QUALITY,
                target_score=95.0,
                description="Dependency resolution success rate",
            ),
        ]
        return BenchmarkSuite(name="migration_quality", category=BenchmarkCategory.MIGRATION_QUALITY, items=items)

    @staticmethod
    def security() -> BenchmarkSuite:
        items = [
            BenchmarkItem(
                name="vulnerability_count",
                category=BenchmarkCategory.SECURITY,
                target_score=0.0,
                description="Known vulnerability count (lower is better)",
            ),
            BenchmarkItem(
                name="secret_exposure",
                category=BenchmarkCategory.SECURITY,
                target_score=0.0,
                description="Exposed secrets count (lower is better)",
            ),
            BenchmarkItem(
                name="dependency_audit",
                category=BenchmarkCategory.SECURITY,
                target_score=100.0,
                description="Dependency audit pass rate",
            ),
        ]
        return BenchmarkSuite(name="security", category=BenchmarkCategory.SECURITY, items=items)

    @classmethod
    def all_suites(cls) -> dict[str, BenchmarkSuite]:
        return {
            "code_quality": cls.code_quality(),
            "performance": cls.performance(),
            "migration_quality": cls.migration_quality(),
            "security": cls.security(),
        }

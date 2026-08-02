from __future__ import annotations

import shutil
import tempfile

import pytest

from fusion_code_modelization.benchmark.models import (
    BenchmarkCategory,
    BenchmarkItem,
    BenchmarkReport,
    BenchmarkResult,
    BenchmarkStatus,
    BenchmarkSuite,
)
from fusion_code_modelization.benchmark.runner import BenchmarkRunner
from fusion_code_modelization.benchmark.suite import PredefinedBenchmarkSuites


@pytest.fixture
def tmp_results_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


@pytest.fixture
def runner(tmp_results_dir):
    return BenchmarkRunner(results_dir=tmp_results_dir)


# ── Enums ──


class TestBenchmarkCategory:
    def test_values(self):
        assert BenchmarkCategory.CODE_QUALITY == "code_quality"
        assert BenchmarkCategory.PERFORMANCE == "performance"
        assert BenchmarkCategory.MIGRATION_QUALITY == "migration_quality"
        assert BenchmarkCategory.SECURITY == "security"
        assert BenchmarkCategory.CUSTOM == "custom"

    def test_is_str_enum(self):
        assert isinstance(BenchmarkCategory.CODE_QUALITY, str)


class TestBenchmarkStatus:
    def test_values(self):
        assert BenchmarkStatus.PENDING == "pending"
        assert BenchmarkStatus.RUNNING == "running"
        assert BenchmarkStatus.PASSED == "passed"
        assert BenchmarkStatus.FAILED == "failed"
        assert BenchmarkStatus.SKIPPED == "skipped"
        assert BenchmarkStatus.ERROR == "error"


# ── BenchmarkItem ──


class TestBenchmarkItem:
    def test_to_dict_from_dict_roundtrip(self):
        item = BenchmarkItem(
            name="test_item",
            category=BenchmarkCategory.SECURITY,
            target_score=95.0,
            description="a test item",
        )
        d = item.to_dict()
        restored = BenchmarkItem.from_dict(d)
        assert restored.name == "test_item"
        assert restored.category == BenchmarkCategory.SECURITY
        assert restored.target_score == 95.0
        assert restored.description == "a test item"
        assert restored.item_id == item.item_id

    def test_from_dict_defaults(self):
        restored = BenchmarkItem.from_dict({})
        assert restored.name == ""
        assert restored.category == BenchmarkCategory.CUSTOM
        assert restored.target_score == 0.0


# ── BenchmarkSuite ──


class TestBenchmarkSuite:
    def test_to_dict_from_dict_with_items(self):
        items = [
            BenchmarkItem(name="a", target_score=1.0),
            BenchmarkItem(name="b", target_score=2.0),
        ]
        suite = BenchmarkSuite(name="suite_x", category=BenchmarkCategory.PERFORMANCE, items=items)
        d = suite.to_dict()
        restored = BenchmarkSuite.from_dict(d)
        assert restored.name == "suite_x"
        assert restored.category == BenchmarkCategory.PERFORMANCE
        assert len(restored.items) == 2
        assert restored.items[0].name == "a"
        assert restored.items[1].target_score == 2.0

    def test_from_dict_empty_items(self):
        restored = BenchmarkSuite.from_dict({"name": "empty"})
        assert restored.items == []


# ── BenchmarkResult ──


class TestBenchmarkResult:
    def test_passed_property_true(self):
        r = BenchmarkResult(status=BenchmarkStatus.PASSED, score=90.0, target_score=80.0)
        assert r.passed is True

    def test_passed_property_false_low_score(self):
        r = BenchmarkResult(status=BenchmarkStatus.PASSED, score=70.0, target_score=80.0)
        assert r.passed is False

    def test_passed_property_false_wrong_status(self):
        r = BenchmarkResult(status=BenchmarkStatus.FAILED, score=90.0, target_score=80.0)
        assert r.passed is False

    def test_from_dict_missing_fields(self):
        r = BenchmarkResult.from_dict({})
        assert r.score == 0.0
        assert r.target_score == 0.0
        assert r.status == BenchmarkStatus.PENDING
        assert r.item_id == ""
        assert r.duration_ms == 0.0
        assert r.metrics == {}
        assert r.error_message == ""


# ── BenchmarkReport ──


class TestBenchmarkReport:
    def test_compute_summary(self):
        results = [
            BenchmarkResult(status=BenchmarkStatus.PASSED, score=90.0, target_score=80.0, duration_ms=10.0),
            BenchmarkResult(status=BenchmarkStatus.FAILED, score=50.0, target_score=80.0, duration_ms=20.0),
            BenchmarkResult(status=BenchmarkStatus.SKIPPED, score=0.0, target_score=80.0, duration_ms=0.0),
            BenchmarkResult(status=BenchmarkStatus.ERROR, score=0.0, target_score=80.0, duration_ms=5.0),
        ]
        report = BenchmarkReport(suite_name="test", results=results)
        report.compute_summary()
        assert report.total_items == 4
        assert report.passed_items == 1
        assert report.failed_items == 1
        assert report.skipped_items == 1
        assert report.error_items == 1
        assert report.pass_rate == 0.25
        assert report.avg_score == 70.0
        assert report.total_duration_ms == 35.0

    def test_compute_summary_empty(self):
        report = BenchmarkReport(results=[])
        report.compute_summary()
        assert report.total_items == 0
        assert report.pass_rate == 0.0
        assert report.avg_score == 0.0

    def test_to_markdown_contains_sections(self):
        results = [
            BenchmarkResult(
                item_id="i1", status=BenchmarkStatus.PASSED, score=90.0, target_score=80.0, duration_ms=10.0
            ),
        ]
        report = BenchmarkReport(suite_name="demo_suite", results=results)
        report.compute_summary()
        md = report.to_markdown()
        assert "# Benchmark Report: demo_suite" in md
        assert "## Summary" in md
        assert "## Results" in md
        assert "i1" in md


# ── PredefinedBenchmarkSuites ──


class TestPredefinedBenchmarkSuites:
    def test_code_quality_has_5_items(self):
        suite = PredefinedBenchmarkSuites.code_quality()
        assert suite.name == "code_quality"
        assert len(suite.items) == 5
        assert suite.category == BenchmarkCategory.CODE_QUALITY

    def test_all_suites_returns_4(self):
        suites = PredefinedBenchmarkSuites.all_suites()
        assert len(suites) == 4
        assert "code_quality" in suites
        assert "performance" in suites
        assert "migration_quality" in suites
        assert "security" in suites


# ── BenchmarkRunner ──


class TestBenchmarkRunner:
    def test_list_suites_includes_predefined(self, runner):
        names = runner.list_suites()
        assert "code_quality" in names
        assert "performance" in names
        assert "migration_quality" in names
        assert "security" in names

    def test_register_and_get_suite(self, runner):
        custom = BenchmarkSuite(name="custom_suite", items=[BenchmarkItem(name="x", target_score=1.0)])
        runner.register_suite(custom)
        assert runner.get_suite("custom_suite") is not None
        assert "custom_suite" in runner.list_suites()

    def test_run_suite_passed_failed_skipped(self, runner):
        score_fn = {
            "cyclomatic_complexity": 8.0,
            "duplication_ratio": 6.0,
            "test_coverage": 85.0,
        }
        report = runner.run_suite("code_quality", score_fn=score_fn)
        statuses = {r.status for r in report.results}
        assert BenchmarkStatus.PASSED in statuses
        assert BenchmarkStatus.FAILED in statuses
        assert BenchmarkStatus.SKIPPED in statuses
        assert report.passed_items + report.failed_items + report.skipped_items == report.total_items

    def test_run_suite_not_found(self, runner):
        report = runner.run_suite("nonexistent")
        assert report.total_items == 0

    def test_run_single_passed(self, runner):
        result = runner.run_single("code_quality", "test_coverage", score=85.0, duration_ms=5.0)
        assert result.status == BenchmarkStatus.PASSED
        assert result.score == 85.0
        assert result.duration_ms == 5.0

    def test_run_single_failed(self, runner):
        result = runner.run_single("code_quality", "test_coverage", score=50.0, duration_ms=3.0)
        assert result.status == BenchmarkStatus.FAILED

    def test_run_single_item_not_found(self, runner):
        result = runner.run_single("code_quality", "no_such_item", score=100.0)
        assert result.item_id == ""

    def test_compare_reports(self, runner):
        score_fn_a = {
            "cyclomatic_complexity": 8.0,
            "duplication_ratio": 3.0,
            "test_coverage": 70.0,
            "lint_violations": 0.0,
            "type_safety": 90.0,
        }
        score_fn_b = {
            "cyclomatic_complexity": 6.0,
            "duplication_ratio": 4.0,
            "test_coverage": 75.0,
            "lint_violations": 0.0,
            "type_safety": 90.0,
        }
        report_a = runner.run_suite("code_quality", score_fn=score_fn_a)
        report_b = runner.run_suite("code_quality", score_fn=score_fn_b)
        comparison = runner.compare_reports(report_a, report_b)
        assert "regressions" in comparison
        assert "improvements" in comparison
        assert "unchanged" in comparison
        assert comparison["regression_count"] + comparison["improvement_count"] >= 0

    def test_load_report(self, runner):
        score_fn = {"cyclomatic_complexity": 8.0}
        report = runner.run_suite("code_quality", score_fn=score_fn)
        loaded = runner.load_report(report.report_id)
        assert loaded is not None
        assert loaded.report_id == report.report_id
        assert loaded.suite_name == "code_quality"

    def test_load_report_not_found(self, runner):
        assert runner.load_report("nonexistent_id") is None

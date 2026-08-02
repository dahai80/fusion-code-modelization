# GateGuard: New file. Importers: benchmark/__init__.py, tests/test_benchmark.py, cli/__init__.py. Affected API: none. Data schemas: none. User instruction: Phase 4 V2.0 — benchmark runner per enhancement doc.

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .models import BenchmarkReport, BenchmarkResult, BenchmarkStatus, BenchmarkSuite
from .suite import PredefinedBenchmarkSuites

logger = logging.getLogger(__name__)

RESULTS_DIR = Path.home() / ".fusion" / "benchmark" / "results"


class BenchmarkRunner:
    def __init__(self, results_dir: str | Path | None = None) -> None:
        self.results_dir = Path(results_dir) if results_dir else RESULTS_DIR
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._suites: dict[str, BenchmarkSuite] = PredefinedBenchmarkSuites.all_suites()
        self._custom_suites: dict[str, BenchmarkSuite] = {}
        logger.info("BenchmarkRunner initialized, results_dir=%s", self.results_dir)

    def register_suite(self, suite: BenchmarkSuite) -> None:
        self._custom_suites[suite.name] = suite
        logger.info("Registered custom suite: %s", suite.name)

    def get_suite(self, suite_name: str) -> BenchmarkSuite | None:
        return self._suites.get(suite_name) or self._custom_suites.get(suite_name)

    def list_suites(self) -> list[str]:
        return list(self._suites.keys()) + list(self._custom_suites.keys())

    def run_suite(self, suite_name: str, score_fn: dict | None = None) -> BenchmarkReport:
        suite = self.get_suite(suite_name)
        if not suite:
            logger.error("Suite not found: %s", suite_name)
            return BenchmarkReport(suite_name=suite_name)
        logger.info("Running suite: %s (%d items)", suite_name, len(suite.items))
        results = []
        for item in suite.items:
            result = self._run_item(item, suite.suite_id, score_fn)
            results.append(result)
        report = BenchmarkReport(suite_id=suite.suite_id, suite_name=suite_name, results=results)
        report.compute_summary()
        self._save_report(report)
        logger.info("Suite %s complete: pass_rate=%.1f%%", suite_name, report.pass_rate * 100)
        return report

    def run_single(
        self, suite_name: str, item_name: str, score: float = 0.0, duration_ms: float = 0.0
    ) -> BenchmarkResult:
        suite = self.get_suite(suite_name)
        if not suite:
            logger.error("Suite not found: %s", suite_name)
            return BenchmarkResult()
        item = next((i for i in suite.items if i.name == item_name), None)
        if not item:
            logger.error("Item not found: %s in suite %s", item_name, suite_name)
            return BenchmarkResult()
        status = BenchmarkStatus.PASSED if score >= item.target_score else BenchmarkStatus.FAILED
        result = BenchmarkResult(
            item_id=item.item_id,
            suite_id=suite.suite_id,
            status=status,
            score=score,
            target_score=item.target_score,
            duration_ms=duration_ms,
        )
        logger.info(
            "Single benchmark %s: score=%.2f target=%.2f status=%s", item_name, score, item.target_score, status.value
        )
        return result

    def _run_item(self, item, suite_id: str, score_fn: dict | None = None) -> BenchmarkResult:
        start = time.monotonic()
        if score_fn and item.name in score_fn:
            try:
                score = float(score_fn[item.name])
                status = BenchmarkStatus.PASSED if score >= item.target_score else BenchmarkStatus.FAILED
            except (ValueError, TypeError):
                score = 0.0
                status = BenchmarkStatus.ERROR
        else:
            score = 0.0
            status = BenchmarkStatus.SKIPPED
        elapsed = (time.monotonic() - start) * 1000
        return BenchmarkResult(
            item_id=item.item_id,
            suite_id=suite_id,
            status=status,
            score=score,
            target_score=item.target_score,
            duration_ms=elapsed,
        )

    def _save_report(self, report: BenchmarkReport) -> None:
        path = self.results_dir / f"{report.report_id}.json"
        path.write_text(report.to_json())
        logger.debug("Saved report: %s", path)

    def load_report(self, report_id: str) -> BenchmarkReport | None:
        path = self.results_dir / f"{report_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return BenchmarkReport.from_dict(data)

    def compare_reports(self, report_a: BenchmarkReport, report_b: BenchmarkReport) -> dict:
        a_scores = {r.item_id: r for r in report_a.results}
        b_scores = {r.item_id: r for r in report_b.results}
        regressions = []
        improvements = []
        unchanged = []
        for item_id in a_scores:
            if item_id not in b_scores:
                continue
            a_val = a_scores[item_id].score
            b_val = b_scores[item_id].score
            diff = b_val - a_val
            entry = {"item_id": item_id, "a_score": a_val, "b_score": b_val, "diff": diff}
            if diff > 0:
                improvements.append(entry)
            elif diff < 0:
                regressions.append(entry)
            else:
                unchanged.append(entry)
        result = {
            "report_a": report_a.report_id,
            "report_b": report_b.report_id,
            "regressions": regressions,
            "improvements": improvements,
            "unchanged": unchanged,
            "regression_count": len(regressions),
            "improvement_count": len(improvements),
        }
        logger.info(
            "Compared %s vs %s: %d regressions, %d improvements",
            report_a.report_id,
            report_b.report_id,
            len(regressions),
            len(improvements),
        )
        return result

    def get_historical_trends(self, suite_name: str, limit: int = 10) -> list[dict]:
        reports = []
        for path in sorted(self.results_dir.glob("*.json"), reverse=True)[: limit * 2]:
            try:
                data = json.loads(path.read_text())
                if data.get("suite_name") == suite_name:
                    reports.append(
                        {
                            "report_id": data["report_id"],
                            "pass_rate": data.get("pass_rate", 0.0),
                            "avg_score": data.get("avg_score", 0.0),
                            "timestamp": data.get("timestamp", ""),
                        }
                    )
            except (json.JSONDecodeError, KeyError):
                continue
        return reports[:limit]

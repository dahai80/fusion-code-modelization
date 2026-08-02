# GateGuard: New file. Importers: test runner. Affected API: AuditEntry, AuditFilter, AuditReport, AuditStore, AuditLogger. Data schemas: AuditEntry.to_dict/from_dict. User instruction: "开始阶段3".

from __future__ import annotations

import pytest

from fusion_code_modelization.audit import (
    AuditAction,
    AuditEntry,
    AuditFilter,
    AuditLogger,
    AuditReport,
    AuditSeverity,
    AuditStore,
)


class TestAuditAction:
    def test_all_values(self):
        assert AuditAction.FILE_READ.value == "file_read"
        assert AuditAction.CUSTOM.value == "custom"
        assert len(AuditAction) == 18

    def test_str_enum(self):
        assert isinstance(AuditAction.FILE_READ, str)


class TestAuditSeverity:
    def test_values(self):
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditEntry:
    def test_to_dict(self):
        entry = AuditEntry(action=AuditAction.FILE_READ, target="main.py", actor="user1")
        d = entry.to_dict()
        assert d["action"] == "file_read"
        assert d["target"] == "main.py"
        assert d["actor"] == "user1"
        assert d["severity"] == "info"
        assert d["entry_id"] != ""
        assert d["timestamp"] != ""

    def test_from_dict(self):
        data = {
            "entry_id": "abc123",
            "timestamp": "2026-01-01T00:00:00",
            "action": "file_write",
            "target": "out.py",
            "actor": "bot",
            "severity": "warning",
            "details": {"key": "val"},
        }
        entry = AuditEntry.from_dict(data)
        assert entry.entry_id == "abc123"
        assert entry.action == AuditAction.FILE_WRITE
        assert entry.severity == AuditSeverity.WARNING
        assert entry.details == {"key": "val"}

    def test_auto_id_and_timestamp(self):
        entry = AuditEntry(action=AuditAction.CUSTOM, target="x")
        assert entry.entry_id != ""
        assert entry.timestamp != ""

    def test_roundtrip(self):
        entry = AuditEntry(
            action=AuditAction.SECURITY_SCAN, target="scan1", severity=AuditSeverity.CRITICAL, details={"risk": "high"}
        )
        d = entry.to_dict()
        restored = AuditEntry.from_dict(d)
        assert restored.action == entry.action
        assert restored.target == entry.target
        assert restored.severity == entry.severity
        assert restored.details == entry.details


class TestAuditFilter:
    def test_matches_action(self):
        f = AuditFilter(action=AuditAction.FILE_READ)
        e1 = AuditEntry(action=AuditAction.FILE_READ, target="a.py")
        e2 = AuditEntry(action=AuditAction.FILE_WRITE, target="b.py")
        assert f.matches(e1) is True
        assert f.matches(e2) is False

    def test_matches_actor(self):
        f = AuditFilter(actor="admin")
        e1 = AuditEntry(action=AuditAction.CUSTOM, target="x", actor="admin")
        e2 = AuditEntry(action=AuditAction.CUSTOM, target="x", actor="user")
        assert f.matches(e1) is True
        assert f.matches(e2) is False

    def test_matches_severity(self):
        f = AuditFilter(severity=AuditSeverity.CRITICAL)
        e1 = AuditEntry(action=AuditAction.CUSTOM, target="x", severity=AuditSeverity.CRITICAL)
        e2 = AuditEntry(action=AuditAction.CUSTOM, target="x", severity=AuditSeverity.INFO)
        assert f.matches(e1) is True
        assert f.matches(e2) is False

    def test_matches_target_substring(self):
        f = AuditFilter(target="main")
        e1 = AuditEntry(action=AuditAction.FILE_READ, target="src/main.py")
        assert f.matches(e1) is True

    def test_no_filter_matches_all(self):
        f = AuditFilter()
        e = AuditEntry(action=AuditAction.FILE_DELETE, target="x", actor="y", severity=AuditSeverity.WARNING)
        assert f.matches(e) is True


class TestAuditReport:
    def test_to_json(self):
        entries = [AuditEntry(action=AuditAction.FILE_READ, target="a.py")]
        report = AuditReport(title="Test Report", entries=entries, statistics={"total": 1})
        result = report.to_json()
        assert result["title"] == "Test Report"
        assert result["total_entries"] == 1
        assert len(result["entries"]) == 1

    def test_to_csv(self):
        entries = [AuditEntry(action=AuditAction.FILE_WRITE, target="b.py", actor="admin")]
        report = AuditReport(title="CSV", entries=entries)
        csv = report.to_csv()
        assert "entry_id" in csv
        assert "file_write" in csv
        assert "admin" in csv

    def test_to_markdown(self):
        entries = [AuditEntry(action=AuditAction.CUSTOM, target="x")]
        report = AuditReport(title="MD Report", entries=entries)
        md = report.to_markdown()
        assert "# MD Report" in md
        assert "custom" in md


class TestAuditStore:
    @pytest.fixture
    def store(self, tmp_path):
        return AuditStore(store_dir=str(tmp_path / "audit"))

    def test_append_and_read(self, store):
        entry = AuditEntry(action=AuditAction.FILE_READ, target="a.py")
        store.append(entry)
        entries = store.read_all()
        assert len(entries) == 1
        assert entries[0].action == AuditAction.FILE_READ

    def test_read_all_limit(self, store):
        for i in range(5):
            store.append(AuditEntry(action=AuditAction.CUSTOM, target=f"t{i}"))
        entries = store.read_all(limit=3)
        assert len(entries) == 3

    def test_search_by_action(self, store):
        store.append(AuditEntry(action=AuditAction.FILE_READ, target="a.py"))
        store.append(AuditEntry(action=AuditAction.FILE_WRITE, target="b.py"))
        results = store.search(action=AuditAction.FILE_READ)
        assert len(results) == 1
        assert results[0].target == "a.py"

    def test_search_by_actor(self, store):
        store.append(AuditEntry(action=AuditAction.CUSTOM, target="x", actor="alice"))
        store.append(AuditEntry(action=AuditAction.CUSTOM, target="y", actor="bob"))
        results = store.search(actor="alice")
        assert len(results) == 1

    def test_get_statistics(self, store):
        store.append(AuditEntry(action=AuditAction.FILE_READ, target="a.py", severity=AuditSeverity.INFO))
        store.append(AuditEntry(action=AuditAction.FILE_READ, target="b.py", severity=AuditSeverity.WARNING))
        stats = store.get_statistics()
        assert stats["total_entries"] == 2
        assert stats["action_counts"]["file_read"] == 2
        assert stats["severity_counts"]["warning"] == 1

    def test_cleanup(self, store):
        store.append(AuditEntry(action=AuditAction.CUSTOM, target="old"))
        removed = store.cleanup(max_age_days=0)
        assert removed >= 0


class TestAuditLogger:
    @pytest.fixture
    def logger_inst(self, tmp_path):
        return AuditLogger(store_dir=str(tmp_path / "audit"))

    def test_log_operation(self, logger_inst):
        entry = logger_inst.log_operation(action=AuditAction.FILE_WRITE, target="out.py")
        assert entry.action == AuditAction.FILE_WRITE
        assert entry.target == "out.py"
        assert entry.entry_id != ""

    def test_search_with_query(self, logger_inst):
        logger_inst.log_operation(action=AuditAction.CUSTOM, target="findme")
        logger_inst.log_operation(action=AuditAction.CUSTOM, target="other")
        results = logger_inst.search(query="findme")
        assert len(results) == 1

    def test_search_with_filters(self, logger_inst):
        logger_inst.log_operation(action=AuditAction.FILE_READ, target="a.py", actor="admin")
        filters = AuditFilter(actor="admin")
        results = logger_inst.search(filters=filters)
        assert len(results) == 1

    def test_export_report_json(self, logger_inst):
        logger_inst.log_operation(action=AuditAction.CUSTOM, target="x")
        report = logger_inst.export_report(fmt="json")
        assert isinstance(report, dict)
        assert report["total_entries"] >= 1

    def test_export_report_csv(self, logger_inst):
        logger_inst.log_operation(action=AuditAction.CUSTOM, target="x")
        report = logger_inst.export_report(fmt="csv")
        assert isinstance(report, str)
        assert "entry_id" in report

    def test_export_report_markdown(self, logger_inst):
        logger_inst.log_operation(action=AuditAction.CUSTOM, target="x")
        report = logger_inst.export_report(fmt="markdown")
        assert isinstance(report, str)
        assert "# " in report

    def test_get_statistics(self, logger_inst):
        logger_inst.log_operation(action=AuditAction.FILE_READ, target="a.py")
        stats = logger_inst.get_statistics()
        assert "total_entries" in stats

    def test_cleanup(self, logger_inst):
        logger_inst.log_operation(action=AuditAction.CUSTOM, target="old")
        removed = logger_inst.cleanup(max_age_days=0)
        assert removed >= 0

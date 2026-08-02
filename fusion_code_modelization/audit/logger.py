# GateGuard: Importers: audit/__init__.py, tests/test_audit.py. Affected API: AuditLogger.log_operation/search/export_report/get_statistics/cleanup. Data schemas: delegates to AuditStore. User instruction: "开始阶段3".

from __future__ import annotations

import logging
from typing import Any

from .models import AuditAction, AuditEntry, AuditFilter, AuditReport, AuditSeverity
from .store import AuditStore

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, store_dir: str = ".fusion/audit"):
        self._store = AuditStore(store_dir=store_dir)

    def log_operation(
        self,
        action: AuditAction,
        target: str,
        actor: str = "system",
        severity: AuditSeverity = AuditSeverity.INFO,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            action=action,
            target=target,
            actor=actor,
            severity=severity,
            details=details or {},
        )
        self._store.append(entry)
        logger.info("audit: %s %s by %s [%s]", action.value, target, actor, severity.value)
        return entry

    def search(self, query: str = "", filters: AuditFilter | None = None, limit: int = 100) -> list[AuditEntry]:
        if filters:
            return self._store.search(
                action=filters.action,
                actor=filters.actor,
                target=filters.target or query,
                severity=filters.severity,
                start_time=filters.start_time,
                end_time=filters.end_time,
                limit=filters.limit or limit,
            )
        if query:
            all_entries = self._store.read_all(limit=limit)
            return [e for e in all_entries if query in e.target or query in e.actor or query in e.action.value]
        return self._store.read_all(limit=limit)

    def export_report(
        self,
        title: str = "Audit Report",
        fmt: str = "json",
        filters: AuditFilter | None = None,
    ) -> str | dict[str, Any]:
        entries = self.search(filters=filters)
        stats = self._store.get_statistics(
            start_time=filters.start_time if filters else "",
            end_time=filters.end_time if filters else "",
        )
        report = AuditReport(title=title, entries=entries, statistics=stats)
        if fmt == "csv":
            return report.to_csv()
        if fmt == "markdown":
            return report.to_markdown()
        return report.to_json()

    def get_statistics(self, start_time: str = "", end_time: str = "") -> dict[str, Any]:
        return self._store.get_statistics(start_time=start_time, end_time=end_time)

    def cleanup(self, max_age_days: int = 90) -> int:
        return self._store.cleanup(max_age_days=max_age_days)

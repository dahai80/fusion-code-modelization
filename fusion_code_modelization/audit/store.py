# GateGuard: New file. Importers: audit/__init__.py, audit/logger.py, tests/test_audit.py. Affected API: AuditStore.append(), read_all(), search(), get_statistics(), cleanup(). Data schemas: JSONL lines of AuditEntry.to_dict(). User instruction: "开始阶段3".

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .models import AuditAction, AuditEntry, AuditSeverity

logger = logging.getLogger(__name__)


class AuditStore:
    def __init__(self, store_dir: str = ".fusion/audit"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.store_dir / "audit.jsonl"
        self._max_file_size = 10 * 1024 * 1024
        self._max_files = 10

    def append(self, entry: AuditEntry) -> None:
        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        self._rotate_if_needed()
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        logger.debug("audit entry appended: %s %s", entry.action.value, entry.target)

    def read_all(self, limit: int = 0) -> list[AuditEntry]:
        entries = []
        for f in sorted(self.store_dir.glob("audit*.jsonl"), reverse=True):
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entries.append(AuditEntry.from_dict(data))
                    except (json.JSONDecodeError, ValueError):
                        continue
            if limit and len(entries) >= limit:
                break
        if limit:
            entries = entries[:limit]
        return entries

    def search(
        self,
        action: AuditAction | None = None,
        actor: str = "",
        target: str = "",
        severity: AuditSeverity | None = None,
        start_time: str = "",
        end_time: str = "",
        limit: int = 100,
    ) -> list[AuditEntry]:
        all_entries = self.read_all()
        results = []
        for entry in all_entries:
            if action and entry.action != action:
                continue
            if actor and entry.actor != actor:
                continue
            if target and target not in entry.target:
                continue
            if severity and entry.severity != severity:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def get_statistics(self, start_time: str = "", end_time: str = "") -> dict[str, Any]:
        all_entries = self.read_all()
        filtered = all_entries
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]

        action_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}
        actor_counts: dict[str, int] = {}
        for entry in filtered:
            action_counts[entry.action.value] = action_counts.get(entry.action.value, 0) + 1
            severity_counts[entry.severity.value] = severity_counts.get(entry.severity.value, 0) + 1
            actor_counts[entry.actor] = actor_counts.get(entry.actor, 0) + 1

        return {
            "total_entries": len(filtered),
            "action_counts": action_counts,
            "severity_counts": severity_counts,
            "actor_counts": actor_counts,
        }

    def _rotate_if_needed(self) -> None:
        if not self._log_file.exists():
            return
        if self._log_file.stat().st_size < self._max_file_size:
            return
        for i in range(self._max_files - 1, 0, -1):
            src = self.store_dir / f"audit.{i}.jsonl"
            dst = self.store_dir / f"audit.{i + 1}.jsonl"
            if src.exists():
                if dst.exists():
                    dst.unlink()
                src.rename(dst)
        rotated = self.store_dir / "audit.1.jsonl"
        self._log_file.rename(rotated)
        logger.info("audit log rotated: %s -> %s", self._log_file, rotated)

    def cleanup(self, max_age_days: int = 90) -> int:
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        all_entries = self.read_all()
        kept = [e for e in all_entries if e.timestamp >= cutoff]
        removed = len(all_entries) - len(kept)
        if removed > 0:
            self._rewrite(kept)
            logger.info("audit cleanup: removed %d entries older than %d days", removed, max_age_days)
        return removed

    def _rewrite(self, entries: list[AuditEntry]) -> None:
        tmp = self._log_file.with_suffix(".jsonl.new")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                for entry in entries:
                    line = json.dumps(entry.to_dict(), ensure_ascii=False)
                    f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(self._log_file)
            for old in self.store_dir.glob("audit.*.jsonl"):
                old.unlink()
            logger.info("audit log rewritten atomically: %d entries", len(entries))
        except OSError as e:
            logger.error("audit _rewrite failed, history preserved: %s", e)
            if tmp.exists():
                tmp.unlink(missing_ok=True)

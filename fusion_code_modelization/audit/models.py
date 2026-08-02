# GateGuard: New file. Importers: audit/__init__.py, audit/logger.py, tests/test_audit.py. Affected API: AuditEntry, AuditFilter, AuditReport, AuditAction, AuditSeverity. Data schemas: AuditEntry(entry_id, timestamp, action, target, actor, severity, details). User instruction: "开始阶段3" — implement V1.5 differentiation per enhancement doc.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class AuditAction(StrEnum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    COMMAND_EXEC = "command_exec"
    SESSION_CREATE = "session_create"
    SESSION_START = "session_start"
    SESSION_PAUSE = "session_pause"
    SESSION_COMPLETE = "session_complete"
    SNAPSHOT_CREATE = "snapshot_create"
    SNAPSHOT_RESTORE = "snapshot_restore"
    SNAPSHOT_DELETE = "snapshot_delete"
    PLUGIN_INSTALL = "plugin_install"
    PLUGIN_EXECUTE = "plugin_execute"
    CLUSTER_DISPATCH = "cluster_dispatch"
    CLUSTER_MIGRATE = "cluster_migrate"
    MODEL_SWITCH = "model_switch"
    SECURITY_SCAN = "security_scan"
    CUSTOM = "custom"


class AuditSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    action: AuditAction
    target: str
    actor: str = "system"
    severity: AuditSeverity = AuditSeverity.INFO
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    entry_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.entry_id:
            import uuid

            self.entry_id = uuid.uuid4().hex[:12]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "action": self.action.value,
            "target": self.target,
            "actor": self.actor,
            "severity": self.severity.value,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEntry:
        return cls(
            entry_id=data.get("entry_id", ""),
            timestamp=data.get("timestamp", ""),
            action=AuditAction(data.get("action", "custom")),
            target=data.get("target", ""),
            actor=data.get("actor", "system"),
            severity=AuditSeverity(data.get("severity", "info")),
            details=data.get("details", {}),
        )


@dataclass
class AuditFilter:
    action: AuditAction | None = None
    actor: str = ""
    target: str = ""
    severity: AuditSeverity | None = None
    start_time: str = ""
    end_time: str = ""
    limit: int = 100

    def matches(self, entry: AuditEntry) -> bool:
        if self.action and entry.action != self.action:
            return False
        if self.actor and entry.actor != self.actor:
            return False
        if self.target and self.target not in entry.target:
            return False
        if self.severity and entry.severity != self.severity:
            return False
        if self.start_time and entry.timestamp < self.start_time:
            return False
        return not (self.end_time and entry.timestamp > self.end_time)


@dataclass
class AuditReport:
    title: str
    generated_at: str = ""
    entries: list[AuditEntry] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()

    def to_json(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "total_entries": len(self.entries),
            "statistics": self.statistics,
            "entries": [e.to_dict() for e in self.entries],
        }

    def to_csv(self) -> str:
        lines = ["entry_id,timestamp,action,target,actor,severity,details"]
        for e in self.entries:
            details_str = str(e.details).replace(",", ";")
            lines.append(
                f"{e.entry_id},{e.timestamp},{e.action.value},{e.target},{e.actor},{e.severity.value},{details_str}"
            )
        return "\n".join(lines)

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", f"Generated: {self.generated_at}", f"Total entries: {len(self.entries)}", ""]
        if self.statistics:
            lines.append("## Statistics")
            for k, v in self.statistics.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")
        lines.append("## Entries")
        lines.append("| ID | Timestamp | Action | Target | Actor | Severity |")
        lines.append("|----|-----------|--------|--------|-------|----------|")
        for e in self.entries:
            lines.append(
                f"| {e.entry_id} | {e.timestamp} | {e.action.value} | {e.target} | {e.actor} | {e.severity.value} |"
            )
        return "\n".join(lines)

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    action: str
    target: str
    allowed: bool
    reason: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "allowed": self.allowed,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class SandboxAudit:
    def __init__(self, persist_path: str | Path | None = None):
        self._entries: list[AuditEntry] = []
        self._persist_path = Path(persist_path).expanduser().resolve() if persist_path else None

    def log(self, action: str, target: str, allowed: bool, reason: str = "") -> None:
        entry = AuditEntry(action=action, target=target, allowed=allowed, reason=reason)
        self._entries.append(entry)
        logger.debug("Audit: %s %s allowed=%s reason=%s", action, target, allowed, reason)
        if self._persist_path:
            self._append_to_file(entry)

    def get_log(self, limit: int = 100) -> list[dict[str, Any]]:
        entries = self._entries[-limit:]
        return [e.to_dict() for e in entries]

    def count(self) -> int:
        return len(self._entries)

    def count_blocked(self) -> int:
        return sum(1 for e in self._entries if not e.allowed)

    def export(self, path: str | Path | None = None) -> str:
        data = [e.to_dict() for e in self._entries]
        output = json.dumps(data, indent=2, ensure_ascii=False)
        if path:
            p = Path(path).expanduser().resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(output, encoding="utf-8")
        return output

    def _append_to_file(self, entry: AuditEntry) -> None:
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("Failed to persist audit entry: %s", e)

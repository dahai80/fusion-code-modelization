# GateGuard: New file. Importers: pipeline/__init__.py, pipeline/scorer.py. Affected API: none (AuditLog extracted from __init__.py). Data schemas: AuditLog dataclass. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AuditLog:
    action: str
    module: str
    file: str
    status: str
    timestamp: float = 0.0
    details: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "module": self.module,
            "file": self.file,
            "status": self.status,
            "timestamp": self.timestamp,
            "details": self.details,
        }

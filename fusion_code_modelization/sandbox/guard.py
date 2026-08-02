from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .audit import SandboxAudit
from .policy import SandboxPolicy, SecurityMode

logger = logging.getLogger(__name__)


class SandboxGuard:
    def __init__(self, policy: SandboxPolicy | None = None, audit: SandboxAudit | None = None):
        self.policy = policy or SandboxPolicy()
        self.audit = audit or SandboxAudit()

    def check_read(self, path: str | Path) -> tuple[bool, str]:
        allowed, reason = self.policy.is_path_allowed(path)
        self.audit.log(
            action="read",
            target=str(path),
            allowed=allowed,
            reason=reason,
        )
        if not allowed:
            logger.warning("Read blocked: %s — %s", path, reason)
        return allowed, reason

    def check_write(self, path: str | Path) -> tuple[bool, str]:
        allowed, reason = self.policy.is_write_allowed(path)
        self.audit.log(
            action="write",
            target=str(path),
            allowed=allowed,
            reason=reason,
        )
        if not allowed:
            logger.warning("Write blocked: %s — %s", path, reason)
        return allowed, reason

    def check_command(self, command: str) -> tuple[bool, str]:
        allowed, reason = self.policy.is_command_allowed(command)
        self.audit.log(
            action="command",
            target=command,
            allowed=allowed,
            reason=reason,
        )
        if not allowed:
            logger.warning("Command blocked: %s — %s", command, reason)
        return allowed, reason

    def check_delete(self, path: str | Path) -> tuple[bool, str]:
        if self.policy.mode == SecurityMode.READONLY:
            reason = "Delete blocked: sandbox in readonly mode"
            self.audit.log(action="delete", target=str(path), allowed=False, reason=reason)
            return False, reason
        if self.policy.mode == SecurityMode.MANUAL:
            reason = "Delete requires manual approval"
            self.audit.log(action="delete", target=str(path), allowed=False, reason=reason)
            return False, reason
        allowed, reason = self.policy.is_path_allowed(path)
        self.audit.log(action="delete", target=str(path), allowed=allowed, reason=reason)
        return allowed, reason

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.audit.get_log(limit=limit)

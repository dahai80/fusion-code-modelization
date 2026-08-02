from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SecurityMode(enum.Enum):
    READONLY = "readonly"
    MANUAL = "manual"
    AUTO = "auto"


DANGEROUS_COMMANDS: set[str] = {
    "rm",
    "rmdir",
    "del",
    "format",
    "fdisk",
    "mkfs",
    "sudo",
    "su",
    "chmod",
    "chown",
    "curl",
    "wget",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "kill",
    "killall",
    "dd",
    "mv /",
    "cp -r /",
}

SENSITIVE_FILE_PATTERNS: list[str] = [
    ".env",
    ".env.local",
    ".env.production",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    ".ssh/",
    ".gnupg/",
    "credentials.json",
    "service-account.json",
    ".htpasswd",
    ".netrc",
]

DEFAULT_IGNORE_PATTERNS: list[str] = [
    ".git/",
    ".svn/",
    ".hg/",
    "node_modules/",
    "__pycache__/",
    ".venv/",
    "venv/",
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    ".fusion/",
    ".claude/",
]


@dataclass
class SandboxPolicy:
    mode: SecurityMode = SecurityMode.MANUAL
    allowed_dirs: list[str] = field(default_factory=list)
    denied_files: list[str] = field(default_factory=list)
    denied_commands: set[str] = field(default_factory=lambda: DANGEROUS_COMMANDS.copy())
    ignore_patterns: list[str] = field(default_factory=lambda: DEFAULT_IGNORE_PATTERNS.copy())
    sensitive_patterns: list[str] = field(default_factory=lambda: SENSITIVE_FILE_PATTERNS.copy())

    def is_path_allowed(self, path: str | Path) -> tuple[bool, str]:
        p = Path(path).expanduser().resolve()
        if self._is_ignored(p):
            return False, f"Path matches ignore pattern: {p}"
        if self._is_sensitive(p):
            return False, f"Path matches sensitive pattern: {p}"
        if self._is_denied(p):
            return False, f"Path explicitly denied: {p}"
        if not self.allowed_dirs:
            return True, ""
        for allowed in self.allowed_dirs:
            allowed_path = Path(allowed).expanduser().resolve()
            try:
                p.relative_to(allowed_path)
                return True, ""
            except ValueError:
                continue
        return False, f"Path outside allowed directories: {p}"

    def is_write_allowed(self, path: str | Path) -> tuple[bool, str]:
        if self.mode == SecurityMode.READONLY:
            return False, "Write blocked: sandbox in readonly mode"
        allowed, reason = self.is_path_allowed(path)
        if not allowed:
            return False, reason
        return True, ""

    def is_command_allowed(self, command: str) -> tuple[bool, str]:
        parts = command.strip().split()
        if not parts:
            return True, ""
        base_cmd = Path(parts[0]).name
        if base_cmd in self.denied_commands:
            return False, f"Command blocked: {base_cmd} is in denied list"
        if self.mode == SecurityMode.READONLY:
            write_cmds = {"touch", "mkdir", "cp", "mv", "tee", "echo >", "cat >", "sed -i"}
            if base_cmd in write_cmds:
                return False, f"Write command blocked in readonly mode: {base_cmd}"
        return True, ""

    def _is_ignored(self, path: Path) -> bool:
        path_str = str(path)
        for pattern in self.ignore_patterns:
            clean = pattern.rstrip("/")
            if clean in path_str:
                return True
        return False

    def _is_sensitive(self, path: Path) -> bool:
        path_str = str(path)
        for pattern in self.sensitive_patterns:
            clean = pattern.rstrip("/")
            if clean in path_str:
                return True
        return False

    def _is_denied(self, path: Path) -> bool:
        path_str = str(path)
        return any(denied in path_str for denied in self.denied_files)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "allowed_dirs": self.allowed_dirs,
            "denied_files": self.denied_files,
            "denied_commands": sorted(self.denied_commands),
            "ignore_patterns": self.ignore_patterns,
            "sensitive_patterns": self.sensitive_patterns,
        }

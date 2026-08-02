from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FileDelta:
    path: str
    old_hash: str = ""
    new_hash: str = ""
    diff: str = ""
    is_new: bool = False
    is_deleted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "diff": self.diff,
            "is_new": self.is_new,
            "is_deleted": self.is_deleted,
        }


@dataclass
class Snapshot:
    snapshot_id: str
    label: str = ""
    deltas: list[FileDelta] = field(default_factory=list)
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "label": self.label,
            "deltas": [d.to_dict() for d in self.deltas],
            "created_at": self.created_at,
        }


def compute_delta(old_content: str, new_content: str, path: str) -> FileDelta:
    diff_lines = list(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
    return FileDelta(
        path=path,
        diff="".join(diff_lines),
    )


def apply_delta(content: str, delta: FileDelta) -> str:
    if delta.is_deleted:
        return ""
    if delta.is_new or not delta.diff:
        return content
    patched = list(difflib.restore(delta.diff.splitlines(keepends=True), which=2))
    return "".join(patched) if patched else content

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryTier(Enum):
    GLOBAL = "global"
    PROJECT = "project"
    DIRECTORY = "directory"


MEMORY_FILENAME = "FUSION.md"

GLOBAL_DIR = Path.home() / ".fusion"

DEFAULT_GLOBAL_TEMPLATE = """# Fusion Global Rules

This file applies to ALL projects on this machine.

## Preferences
- Language: Python 3.12+
- Style: 4-space indentation, no docstrings

## Model Defaults
- Default model: local (fusion-mlx)

## Security
- Default mode: manual
"""

DEFAULT_PROJECT_TEMPLATE = """# {project_name} Project Rules

This file is committed to Git and shared with the team.

## Architecture
- Describe your project architecture here

## Conventions
- Code style rules
- Naming conventions
- Testing requirements

## Dependencies
- Key dependencies and versions
"""

DEFAULT_DIRECTORY_TEMPLATE = """# {directory_name} Module Rules

Module-specific conventions that override project-level rules.

## Special Rules
- Add module-specific rules here
"""


@dataclass
class MemoryEntry:
    tier: MemoryTier
    path: Path
    content: str = ""
    exists: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "path": str(self.path),
            "content": self.content,
            "exists": self.exists,
        }


class MemoryTierManager:
    def __init__(self, project_dir: str | Path | None = None):
        self.project_dir = Path(project_dir).resolve() if project_dir else Path.cwd()
        logger.info("MemoryTierManager init: project=%s", self.project_dir)

    def get_global_path(self) -> Path:
        return GLOBAL_DIR / MEMORY_FILENAME

    def get_project_path(self) -> Path:
        return self.project_dir / MEMORY_FILENAME

    def get_directory_path(self, subdir: str | Path) -> Path:
        return self.project_dir / subdir / MEMORY_FILENAME

    def load_tier(self, tier: MemoryTier, subdir: str | Path = "") -> MemoryEntry:
        if tier == MemoryTier.GLOBAL:
            path = self.get_global_path()
        elif tier == MemoryTier.PROJECT:
            path = self.get_project_path()
        else:
            path = self.get_directory_path(subdir)

        exists = path.exists()
        content = path.read_text(encoding="utf-8") if exists else ""
        logger.debug("Loaded %s memory: %s (exists=%s)", tier.value, path, exists)
        return MemoryEntry(tier=tier, path=path, content=content, exists=exists)

    def load_all(self, subdir: str | Path = "") -> list[MemoryEntry]:
        entries = []
        entries.append(self.load_tier(MemoryTier.GLOBAL))
        entries.append(self.load_tier(MemoryTier.PROJECT))
        if subdir:
            entries.append(self.load_tier(MemoryTier.DIRECTORY, subdir))
        logger.info("Loaded %d memory tiers", len(entries))
        return entries

    def save_tier(self, tier: MemoryTier, content: str, subdir: str | Path = "") -> MemoryEntry:
        if tier == MemoryTier.GLOBAL:
            path = self.get_global_path()
        elif tier == MemoryTier.PROJECT:
            path = self.get_project_path()
        else:
            path = self.get_directory_path(subdir)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Saved %s memory to %s", tier.value, path)
        return MemoryEntry(tier=tier, path=path, content=content, exists=True)

    def init_project(self, project_name: str = "") -> list[MemoryEntry]:
        name = project_name or self.project_dir.name
        logger.info("Initializing project memory for: %s", name)

        entries = []

        global_path = self.get_global_path()
        if not global_path.exists():
            entries.append(self.save_tier(MemoryTier.GLOBAL, DEFAULT_GLOBAL_TEMPLATE.strip()))

        project_content = DEFAULT_PROJECT_TEMPLATE.format(project_name=name).strip()
        entries.append(self.save_tier(MemoryTier.PROJECT, project_content))

        logger.info("Project memory initialized: %d entries", len(entries))
        return entries

    def init_directory(self, subdir: str | Path) -> MemoryEntry:
        dir_name = Path(subdir).name
        content = DEFAULT_DIRECTORY_TEMPLATE.format(directory_name=dir_name).strip()
        logger.info("Initializing directory memory for: %s", subdir)
        return self.save_tier(MemoryTier.DIRECTORY, content, subdir=subdir)

    def resolve_context(self, subdir: str | Path = "") -> str:
        entries = self.load_all(subdir=subdir)
        parts = []
        for entry in entries:
            if not entry.exists or not entry.content:
                continue
            parts.append(f"## [{entry.tier.value.upper()}] {entry.path}\n\n{entry.content}")
        combined = "\n\n---\n\n".join(parts)
        logger.info("Resolved context: %d chars from %d tiers", len(combined), len([e for e in entries if e.exists]))
        return combined

    def list_directory_memories(self) -> list[Path]:
        memories = []
        for p in self.project_dir.rglob(MEMORY_FILENAME):
            if p.parent == self.project_dir:
                continue
            memories.append(p)
        logger.debug("Found %d directory-level memories", len(memories))
        return sorted(memories)

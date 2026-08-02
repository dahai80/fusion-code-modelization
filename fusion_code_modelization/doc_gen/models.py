# GateGuard: New file. Importers: doc_gen/__init__.py, doc_gen/generator.py. Affected API: none (DocSection extracted from __init__.py). Data schemas: DocSection. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DocSection:
    title: str
    content: str = ""
    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "content": self.content, "order": self.order}

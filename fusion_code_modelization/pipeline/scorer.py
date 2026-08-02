# GateGuard: New file. Importers: pipeline/__init__.py. Affected API: none (PriorityScorer extracted from __init__.py). Data schemas: none. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PriorityScorer:
    @staticmethod
    def score_file(file_info: dict) -> dict[str, Any]:
        score = 0
        factors = []

        size = file_info.get("size_bytes", 0)
        if size > 100000:
            score += 30
            factors.append("large_file")
        elif size > 10000:
            score += 15
            factors.append("medium_file")

        deps = len(file_info.get("dependencies", []))
        if deps > 10:
            score += 25
            factors.append("highly_dependent")
        elif deps > 5:
            score += 10
            factors.append("moderately_dependent")

        legacy_langs = {"cobol": 40, "vb6": 35, "vba": 30, "cics": 35}
        lang = file_info.get("language", "")
        score += legacy_langs.get(lang, 5)
        if lang in legacy_langs:
            factors.append(f"legacy_{lang}")

        if file_info.get("is_dead", False):
            score -= 50
            factors.append("dead_code")

        return {
            "score": max(0, score),
            "factors": factors,
            "priority": "high" if score >= 50 else "medium" if score >= 20 else "low",
        }

# GateGuard: New file. Importers: pr_gen/__init__.py. Affected API: none (PRGenerator extracted from __init__.py). Data schemas: none. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

import logging
from typing import Any

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig

logger = logging.getLogger(__name__)


class PRGenerator:
    def __init__(self, mlx_url: str = DEFAULT_GATEWAY_URL, client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    async def generate_pr_description(self, changes: list[dict]) -> dict[str, Any]:
        summary = "\n".join(
            f"- {c.get('path', '?')}: {c.get('summary', c.get('action', 'modified'))}" for c in changes[:50]
        )
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a PR description for these code changes:\n{summary}\n\n"
                        f"Include: 1) What changed, 2) Why, 3) Testing notes, 4) Breaking changes."
                    ),
                }
            ],
            max_tokens=1024,
            temperature=0.3,
        )
        if result["status"] == "completed":
            return {"description": result["content"], "summary": summary}
        logger.warning("PR generation failed: %s", result.get("error"))
        return {"description": f"Code changes:\n{summary}", "error": result.get("error")}

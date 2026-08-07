# GateGuard: New file. Importers: pr_gen/__init__.py. Affected API: none (DocGenerator extracted from __init__.py). Data schemas: none. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

import logging

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig

logger = logging.getLogger(__name__)


class DocGenerator:
    def __init__(self, mlx_url: str = DEFAULT_GATEWAY_URL, client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    async def generate_migration_report(self, analysis: dict, results: list[dict]) -> str:
        lines = [
            "# Code Modernization Report",
            "",
            "## Summary",
            f"- Total files analyzed: {analysis.get('total_files', 0)}",
            f"- Files migrated: {len(results)}",
            f"- Languages: {analysis.get('languages', [])}",
            "",
            "## Migration Details",
            "",
        ]
        for r in results:
            lines.append(f"### {r.get('file', '?')}")
            lines.append(f"- Status: {r.get('status', '?')}")
            lines.append(f"- Source: {r.get('source_lang', '?')} → {r.get('target_lang', '?')}")
            lines.append("")
        return "\n".join(lines)

    async def generate_api_docs(self, code: str, language: str) -> str:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Generate API documentation for this {language} code. "
                        f"Document all public functions, classes, and parameters.\n\n"
                        f"```{language}\n{code[:4000]}\n```"
                    ),
                }
            ],
            max_tokens=4096,
            temperature=0.1,
        )
        if result["status"] == "completed":
            return result["content"]
        logger.warning("API doc generation failed: %s", result.get("error"))
        return f"Error generating docs: {result.get('error')}"

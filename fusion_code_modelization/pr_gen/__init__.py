from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import ModelConfig

logger = logging.getLogger(__name__)


class PRGenerator:
    def __init__(self, mlx_url: str = "http://localhost:11434/v1", client: MLXClient | None = None):
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


class DocGenerator:
    def __init__(self, mlx_url: str = "http://localhost:11434/v1", client: MLXClient | None = None):
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


class MicroserviceDecomposer:
    def __init__(self, mlx_url: str = "http://localhost:11434/v1", client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    def analyze_boundaries(self, graph: dict) -> list[dict]:
        clusters = defaultdict(list)
        for node_id, _node in graph.get("nodes", {}).items():
            module = node_id.split("/")[0] if "/" in node_id else "root"
            clusters[module].append(node_id)
        services = []
        for module, files in clusters.items():
            if len(files) >= 2:
                services.append({"name": module, "files": files, "size": len(files)})
        return services

    async def suggest_decomposition(self, code: str, language: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Analyze this {language} codebase and suggest how to split it into microservices. "
                        f"Identify bounded contexts, service boundaries, and API contracts.\n\n"
                        f"```{language}\n{code[:4000]}\n```"
                    ),
                }
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        if result["status"] == "completed":
            return {"suggestions": result["content"], "language": language}
        logger.warning("Decomposition suggestion failed: %s", result.get("error"))
        return {"error": result.get("error")}

"""PR and documentation generation — creates code review PRs and migration docs."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PRGenerator:
    """Generates code review PR descriptions and changelogs."""

    def __init__(self, mlx_url: str = "http://localhost:11434/v1"):
        self.mlx_url = mlx_url.rstrip("/")

    async def generate_pr_description(self, changes: list[dict]) -> dict[str, Any]:
        """Generate a PR description from a list of changes."""
        summary = "\n".join(f"- {c.get('path', '?')}: {c.get('summary', c.get('action', 'modified'))}" for c in changes[:50])
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{"role": "user", "content": (
                        f"Write a PR description for these code changes:\n{summary}\n\n"
                        f"Include: 1) What changed, 2) Why, 3) Testing notes, 4) Breaking changes."
                    )}],
                    "max_tokens": 1024, "temperature": 0.3,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return {"description": content, "summary": summary}
        except Exception as e:
            return {"description": f"Code changes:\n{summary}", "error": str(e)}


class DocGenerator:
    """Generates migration documentation and API docs."""

    def __init__(self, mlx_url: str = "http://localhost:11434/v1"):
        self.mlx_url = mlx_url.rstrip("/")

    async def generate_migration_report(self, analysis: dict, results: list[dict]) -> str:
        """Generate a complete migration report."""
        lines = [
            "# Code Modernization Report",
            "",
            f"## Summary",
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
        """Generate API documentation from code."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{"role": "user", "content": (
                        f"Generate API documentation for this {language} code. "
                        f"Document all public functions, classes, and parameters.\n\n"
                        f"```{language}\n{code[:4000]}\n```"
                    )}],
                    "max_tokens": 4096, "temperature": 0.1,
                })
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error generating docs: {e}"


class MicroserviceDecomposer:
    """Analyzes monoliths and suggests microservice boundaries."""

    def __init__(self, mlx_url: str = "http://localhost:11434/v1"):
        self.mlx_url = mlx_url.rstrip("/")

    def analyze_boundaries(self, graph: dict) -> list[dict]:
        """Analyze dependency graph to identify service boundaries."""
        from collections import defaultdict
        clusters = defaultdict(list)
        for node_id, node in graph.get("nodes", {}).items():
            module = node_id.split("/")[0] if "/" in node_id else "root"
            clusters[module].append(node_id)
        services = []
        for module, files in clusters.items():
            if len(files) >= 2:
                services.append({"name": module, "files": files, "size": len(files)})
        return services

    async def suggest_decomposition(self, code: str, language: str) -> dict[str, Any]:
        """Suggest microservice decomposition using LLM."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{"role": "user", "content": (
                        f"Analyze this {language} codebase and suggest how to split it into microservices. "
                        f"Identify bounded contexts, service boundaries, and API contracts.\n\n"
                        f"```{language}\n{code[:4000]}\n```"
                    )}],
                    "max_tokens": 2048, "temperature": 0.1,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return {"suggestions": content, "language": language}
        except Exception as e:
            return {"error": str(e)}
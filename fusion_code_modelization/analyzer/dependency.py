from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class DependencyGraph:
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "edges": self.edges}


class DependencyAnalyzer:
    def __init__(self, mlx_url: str = DEFAULT_GATEWAY_URL, client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    def scan_directory(self, path: str | Path, language: str = "auto") -> DependencyGraph:
        root = Path(path).expanduser().resolve()
        if not root.is_dir():
            logger.warning("Directory not found: %s", root)
            return DependencyGraph()

        graph = DependencyGraph()
        for f in root.rglob("*"):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            lang = self._detect_language(ext)
            if not lang:
                continue
            rel_path = str(f.relative_to(root))
            deps = self._extract_imports(f.read_text(encoding="utf-8", errors="replace"), lang)
            graph.nodes[rel_path] = {
                "path": rel_path,
                "language": lang,
                "size_bytes": f.stat().st_size,
                "dependencies": deps,
            }
            for dep in deps:
                graph.edges.append({"source": rel_path, "target": dep, "type": "import"})
        return graph

    def identify_dead_code(self, graph: DependencyGraph) -> list[str]:
        all_targets = {e["target"] for e in graph.edges}
        dead = []
        for node_id in graph.nodes:
            if node_id not in all_targets:
                dead.append(node_id)
        return dead

    def estimate_tech_debt(self, graph: DependencyGraph) -> dict[str, Any]:
        total_size = sum(n.get("size_bytes", 0) for n in graph.nodes.values())
        return {
            "total_files": len(graph.nodes),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "dead_files": len(self.identify_dead_code(graph)),
        }

    async def analyze_with_llm(self, code: str, language: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Analyze this {language} code. Identify: 1) purpose, "
                        f"2) inputs/outputs, 3) dependencies, 4) potential issues. "
                        f"Return as JSON.\n\n```{language}\n{code[:3000]}\n```"
                    ),
                }
            ],
            max_tokens=1024,
            temperature=0.1,
        )
        if result["status"] == "completed":
            import json

            content = result["content"]
            if content.startswith("{"):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass
            return {"analysis": content}
        return {"error": result.get("error", "Unknown"), "language": language}

    @staticmethod
    def _detect_language(ext: str) -> str:
        lang_map = {
            ".py": "python",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cs": "csharp",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".cbl": "cobol",
            ".cpy": "cobol",
            ".vba": "vb6",
            ".bas": "vb6",
        }
        return lang_map.get(ext, "")

    @staticmethod
    def _extract_imports(code: str, language: str) -> list[str]:
        patterns = {
            "python": [r"^import\s+(\S+)", r"^from\s+(\S+)\s+import"],
            "java": [r"^import\s+([\w.]+)"],
            "c": [r'^#include\s+[<"](\S+)[>"]'],
            "cpp": [r'^#include\s+[<"](\S+)[>"]'],
            "csharp": [r"^using\s+([\w.]+)"],
            "javascript": [r'^(import|require)\s+.*?[\'"](.+?)[\'"]'],
            "go": [r'^import\s+["](.+?)["]'],
        }
        deps = []
        for pattern in patterns.get(language, []):
            for match in re.finditer(pattern, code, re.MULTILINE):
                dep = match.group(1) if match.lastindex == 1 else match.group(2)
                if dep and dep not in deps:
                    deps.append(dep)
        return deps

    @staticmethod
    def generate_report(graph: DependencyGraph, tech_debt: dict) -> str:
        lines = [
            "# Code Modernization Analysis Report",
            "",
            "## Summary",
            f"- Total files: {tech_debt['total_files']}",
            f"- Total size: {tech_debt['total_size_mb']} MB",
            f"- Dead files: {tech_debt['dead_files']}",
            "",
            "## Language Distribution",
        ]
        langs = {}
        for n in graph.nodes.values():
            lang = n.get("language", "unknown")
            langs[lang] = langs.get(lang, 0) + 1
        for lang, count in sorted(langs.items(), key=lambda x: -x[1]):
            lines.append(f"- {lang}: {count} files")
        return "\n".join(lines)

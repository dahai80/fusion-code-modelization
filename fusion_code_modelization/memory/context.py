from __future__ import annotations

import logging
from pathlib import Path

from ..core.client import MLXClient
from ..core.config import DEFAULT_GATEWAY_URL, ModelConfig
from .tier import MemoryEntry, MemoryTier, MemoryTierManager

logger = logging.getLogger(__name__)

CONTEXT_PROMPT = """Summarize the following project memory rules into a concise context block for an AI coding assistant.
Focus on actionable rules, constraints, and conventions.
Return only the summary, no preamble.

Memory content:
{content}"""


class MemoryContext:
    def __init__(
        self,
        project_dir: str | Path | None = None,
        mlx_url: str = DEFAULT_GATEWAY_URL,
        client: MLXClient | None = None,
    ):
        self._client = client or MLXClient(config=ModelConfig(base_url=mlx_url))
        self._manager = MemoryTierManager(project_dir=project_dir)

    def build(self, subdir: str | Path = "") -> str:
        return self._manager.resolve_context(subdir=subdir)

    async def summarize(self, subdir: str | Path = "") -> str:
        content = self.build(subdir=subdir)
        if not content:
            return ""
        logger.info("Summarizing memory context (%d chars)", len(content))
        try:
            prompt = CONTEXT_PROMPT.format(content=content)
            summary = await self._client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            if summary.get("status") == "completed":
                return str(summary.get("content", ""))
            logger.warning("memory summarize returned failed status: %s", summary.get("error"))
            return content
        except Exception as e:
            logger.error("Memory summarize failed: %s", e)
            return content

    async def query(self, question: str, subdir: str | Path = "") -> str:
        content = self.build(subdir=subdir)
        if not content:
            return "No project memory found."
        logger.info("Querying memory: %s", question[:80])
        try:
            prompt = (
                f"Based on the following project memory, answer the question.\n\n"
                f"Memory:\n{content}\n\n"
                f"Question: {question}"
            )
            response = await self._client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            if response.get("status") == "completed":
                return str(response.get("content", ""))
            logger.warning("memory query returned failed status: %s", response.get("error"))
            return content
        except Exception as e:
            logger.error("Memory query failed: %s", e)
            return f"Error: {e}"

    def load(self, tier: MemoryTier, subdir: str | Path = "") -> MemoryEntry:
        return self._manager.load_tier(tier, subdir=subdir)

    def save(self, tier: MemoryTier, content: str, subdir: str | Path = "") -> MemoryEntry:
        return self._manager.save_tier(tier, content, subdir=subdir)

    def init_project(self, project_name: str = "") -> list[MemoryEntry]:
        return self._manager.init_project(project_name=project_name)

    def init_directory(self, subdir: str | Path) -> MemoryEntry:
        return self._manager.init_directory(subdir=subdir)

    def list_directory_memories(self) -> list[Path]:
        return self._manager.list_directory_memories()

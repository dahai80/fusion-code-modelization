from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.memory import (
    MemoryContext,
    MemoryEntry,
    MemoryTier,
    MemoryTierManager,
)


class TestMemoryTier:
    def test_values(self):
        assert MemoryTier.GLOBAL.value == "global"
        assert MemoryTier.PROJECT.value == "project"
        assert MemoryTier.DIRECTORY.value == "directory"


class TestMemoryEntry:
    def test_to_dict(self):
        entry = MemoryEntry(tier=MemoryTier.PROJECT, path=Path("/tmp/FUSION.md"), content="rules", exists=True)
        d = entry.to_dict()
        assert d["tier"] == "project"
        assert d["path"] == "/tmp/FUSION.md"
        assert d["content"] == "rules"
        assert d["exists"] is True

    def test_defaults(self):
        entry = MemoryEntry(tier=MemoryTier.GLOBAL, path=Path("/x"))
        assert entry.content == ""
        assert entry.exists is False


class TestMemoryTierManager:
    @pytest.fixture
    def project_dir(self, tmp_path):
        p = tmp_path / "myproject"
        p.mkdir()
        return p

    @pytest.fixture
    def global_dir(self, tmp_path, monkeypatch):
        g = tmp_path / "home" / ".fusion"
        g.mkdir(parents=True)
        monkeypatch.setattr("fusion_code_modelization.memory.tier.GLOBAL_DIR", g)
        return g

    @pytest.fixture
    def manager(self, project_dir, global_dir):
        return MemoryTierManager(project_dir=project_dir)

    def test_load_tier_missing(self, manager):
        entry = manager.load_tier(MemoryTier.PROJECT)
        assert entry.exists is False
        assert entry.content == ""

    def test_save_and_load_project(self, manager):
        manager.save_tier(MemoryTier.PROJECT, "# Rules\nUse 4 spaces")
        entry = manager.load_tier(MemoryTier.PROJECT)
        assert entry.exists is True
        assert "4 spaces" in entry.content

    def test_save_and_load_global(self, manager, global_dir):
        manager.save_tier(MemoryTier.GLOBAL, "# Global Rules")
        entry = manager.load_tier(MemoryTier.GLOBAL)
        assert entry.exists is True
        assert "Global Rules" in entry.content

    def test_save_and_load_directory(self, manager, project_dir):
        subdir = project_dir / "mymod"
        subdir.mkdir()
        manager.save_tier(MemoryTier.DIRECTORY, "# Module Rules", subdir="mymod")
        entry = manager.load_tier(MemoryTier.DIRECTORY, subdir="mymod")
        assert entry.exists is True
        assert "Module Rules" in entry.content

    def test_load_all(self, manager):
        manager.save_tier(MemoryTier.GLOBAL, "global")
        manager.save_tier(MemoryTier.PROJECT, "project")
        entries = manager.load_all()
        assert len(entries) == 2
        assert entries[0].tier == MemoryTier.GLOBAL
        assert entries[1].tier == MemoryTier.PROJECT

    def test_load_all_with_subdir(self, manager, project_dir):
        subdir = project_dir / "mod"
        subdir.mkdir()
        manager.save_tier(MemoryTier.PROJECT, "project")
        manager.save_tier(MemoryTier.DIRECTORY, "mod rules", subdir="mod")
        entries = manager.load_all(subdir="mod")
        assert len(entries) == 3

    def test_resolve_context(self, manager):
        manager.save_tier(MemoryTier.GLOBAL, "Global rules here")
        manager.save_tier(MemoryTier.PROJECT, "Project rules here")
        ctx = manager.resolve_context()
        assert "Global rules here" in ctx
        assert "Project rules here" in ctx
        assert "[GLOBAL]" in ctx
        assert "[PROJECT]" in ctx

    def test_resolve_context_empty(self, manager):
        ctx = manager.resolve_context()
        assert ctx == ""

    def test_init_project(self, manager):
        entries = manager.init_project(project_name="TestProj")
        assert len(entries) >= 1
        project_entry = manager.load_tier(MemoryTier.PROJECT)
        assert project_entry.exists is True
        assert "TestProj" in project_entry.content

    def test_init_directory(self, manager, project_dir):
        (project_dir / "submod").mkdir()
        entry = manager.init_directory(subdir="submod")
        assert entry.exists is True
        assert "submod" in entry.content

    def test_list_directory_memories(self, manager, project_dir):
        (project_dir / "a").mkdir()
        (project_dir / "b").mkdir()
        manager.save_tier(MemoryTier.DIRECTORY, "a rules", subdir="a")
        manager.save_tier(MemoryTier.DIRECTORY, "b rules", subdir="b")
        mems = manager.list_directory_memories()
        assert len(mems) == 2


class TestMemoryContext:
    @pytest.fixture
    def project_dir(self, tmp_path):
        p = tmp_path / "proj"
        p.mkdir()
        return p

    @pytest.fixture
    def global_dir(self, tmp_path, monkeypatch):
        g = tmp_path / "home" / ".fusion"
        g.mkdir(parents=True)
        monkeypatch.setattr("fusion_code_modelization.memory.tier.GLOBAL_DIR", g)
        return g

    @pytest.fixture
    def ctx(self, project_dir, global_dir):
        client = MLXClient()
        return MemoryContext(project_dir=project_dir, client=client)

    def test_build(self, ctx, project_dir):
        ctx.save(MemoryTier.PROJECT, "# Rules\nNo docstrings")
        content = ctx.build()
        assert "No docstrings" in content

    def test_build_empty(self, ctx):
        content = ctx.build()
        assert content == ""

    @pytest.mark.asyncio
    async def test_summarize(self, ctx, project_dir):
        ctx.save(MemoryTier.PROJECT, "# Rules\nUse Python 3.12")
        with patch.object(ctx._client, "chat", new=AsyncMock(return_value="Use Python 3.12, no docstrings")):
            summary = await ctx.summarize()
        assert "Python 3.12" in summary

    @pytest.mark.asyncio
    async def test_summarize_empty(self, ctx):
        summary = await ctx.summarize()
        assert summary == ""

    @pytest.mark.asyncio
    async def test_query(self, ctx, project_dir):
        ctx.save(MemoryTier.PROJECT, "# Rules\nAlways use logging")
        with patch.object(ctx._client, "chat", new=AsyncMock(return_value="You should always use logging")):
            answer = await ctx.query("What are the rules?")
        assert "logging" in answer

    @pytest.mark.asyncio
    async def test_query_empty(self, ctx):
        answer = await ctx.query("What?")
        assert "No project memory" in answer

    def test_save_and_load(self, ctx):
        ctx.save(MemoryTier.PROJECT, "My rules")
        entry = ctx.load(MemoryTier.PROJECT)
        assert entry.content == "My rules"
        assert entry.exists is True

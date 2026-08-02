# Importers: test runner. Affected API: PluginAction, PluginManifest, PluginRegistry, PluginManager, PluginCategory, PluginStatus. Data schemas: PluginManifest.to_dict/from_dict. User instruction: "开始阶段3"

from __future__ import annotations

import pytest

from fusion_code_modelization.plugin import (
    PluginAction,
    PluginCategory,
    PluginManager,
    PluginManifest,
    PluginRegistry,
    PluginStatus,
)


class TestPluginCategory:
    def test_all_categories(self):
        assert PluginCategory.DATABASE.value == "database"
        assert PluginCategory.CUSTOM.value == "custom"
        assert len(PluginCategory) == 9


class TestPluginStatus:
    def test_all_statuses(self):
        assert PluginStatus.REGISTERED.value == "registered"
        assert PluginStatus.LOADED.value == "loaded"
        assert len(PluginStatus) == 5


class TestPluginAction:
    def test_to_dict(self):
        a = PluginAction(name="run", description="Run something", params_schema={"type": "object"})
        d = a.to_dict()
        assert d["name"] == "run"
        assert d["description"] == "Run something"

    def test_from_dict(self):
        data = {"name": "scan", "description": "Scan", "params_schema": {}}
        a = PluginAction.from_dict(data)
        assert a.name == "scan"
        assert a.description == "Scan"

    def test_defaults(self):
        a = PluginAction(name="test")
        assert a.description == ""
        assert a.params_schema == {}


class TestPluginManifest:
    def test_to_dict(self):
        actions = [PluginAction(name="exec")]
        m = PluginManifest(
            plugin_id="p1", name="Plugin1", version="2.0.0", category=PluginCategory.VCS, actions=actions
        )
        d = m.to_dict()
        assert d["plugin_id"] == "p1"
        assert d["name"] == "Plugin1"
        assert d["version"] == "2.0.0"
        assert d["category"] == "vcs"
        assert len(d["actions"]) == 1

    def test_from_dict(self):
        data = {
            "plugin_id": "p2",
            "name": "Plugin2",
            "version": "1.0.0",
            "category": "testing",
            "description": "desc",
            "actions": [{"name": "run", "description": "", "params_schema": {}}],
            "status": "installed",
        }
        m = PluginManifest.from_dict(data)
        assert m.plugin_id == "p2"
        assert m.category == PluginCategory.TESTING
        assert m.status == PluginStatus.INSTALLED
        assert len(m.actions) == 1

    def test_defaults(self):
        m = PluginManifest(plugin_id="p3", name="P3")
        assert m.version == "1.0.0"
        assert m.category == PluginCategory.CUSTOM
        assert m.status == PluginStatus.REGISTERED
        assert m.installed_at != ""

    def test_roundtrip(self):
        m = PluginManifest(plugin_id="p4", name="P4", actions=[PluginAction(name="do_it")])
        d = m.to_dict()
        restored = PluginManifest.from_dict(d)
        assert restored.plugin_id == m.plugin_id
        assert len(restored.actions) == 1
        assert restored.actions[0].name == "do_it"


class TestPluginRegistry:
    @pytest.fixture
    def registry(self, tmp_path):
        return PluginRegistry(registry_dir=str(tmp_path / "plugins"))

    def test_register(self, registry):
        m = PluginManifest(plugin_id="r1", name="R1")
        result = registry.register(m)
        assert result.plugin_id == "r1"
        assert registry.get("r1") is not None

    def test_register_updates_existing(self, registry):
        m1 = PluginManifest(plugin_id="r1", name="R1 v1")
        registry.register(m1)
        m2 = PluginManifest(plugin_id="r1", name="R1 v2")
        registry.register(m2)
        assert registry.get("r1").name == "R1 v2"

    def test_unregister(self, registry):
        registry.register(PluginManifest(plugin_id="r1", name="R1"))
        assert registry.unregister("r1") is True
        assert registry.get("r1") is None

    def test_unregister_nonexistent(self, registry):
        assert registry.unregister("nope") is False

    def test_list_plugins(self, registry):
        registry.register(PluginManifest(plugin_id="p1", name="P1", category=PluginCategory.VCS))
        registry.register(PluginManifest(plugin_id="p2", name="P2", category=PluginCategory.TESTING))
        all_plugins = registry.list_plugins()
        assert len(all_plugins) == 2
        vcs_plugins = registry.list_plugins(category=PluginCategory.VCS)
        assert len(vcs_plugins) == 1

    def test_search_plugins(self, registry):
        registry.register(PluginManifest(plugin_id="p1", name="GitHelper", description="Git integration"))
        registry.register(PluginManifest(plugin_id="p2", name="DBSync", description="Database sync"))
        results = registry.search_plugins("git")
        assert len(results) == 1
        assert results[0].plugin_id == "p1"

    def test_install(self, registry):
        registry.register(PluginManifest(plugin_id="p1", name="P1"))
        result = registry.install("p1")
        assert result is not None
        assert result.status == PluginStatus.INSTALLED

    def test_install_nonexistent(self, registry):
        result = registry.install("nope")
        assert result is None

    def test_update(self, registry):
        registry.register(PluginManifest(plugin_id="p1", name="P1", version="1.0.0"))
        result = registry.update("p1", version="2.0.0")
        assert result is not None
        assert result.version == "2.0.0"

    def test_disable(self, registry):
        registry.register(PluginManifest(plugin_id="p1", name="P1"))
        assert registry.disable("p1") is True
        assert registry.get("p1").status == PluginStatus.DISABLED

    def test_disable_nonexistent(self, registry):
        assert registry.disable("nope") is False

    def test_persistence(self, tmp_path):
        dir_path = str(tmp_path / "plugins")
        r1 = PluginRegistry(registry_dir=dir_path)
        r1.register(PluginManifest(plugin_id="persist1", name="Persist"))
        r2 = PluginRegistry(registry_dir=dir_path)
        assert r2.get("persist1") is not None
        assert r2.get("persist1").name == "Persist"


class TestPluginManager:
    @pytest.fixture
    def manager(self, tmp_path):
        registry = PluginRegistry(registry_dir=str(tmp_path / "plugins"))
        return PluginManager(registry=registry)

    def test_load(self, manager):
        manager.registry.register(PluginManifest(plugin_id="m1", name="M1", actions=[PluginAction(name="run")]))
        manager.registry.install("m1")
        assert manager.load("m1") is True
        assert manager.registry.get("m1").status == PluginStatus.LOADED

    def test_load_not_found(self, manager):
        assert manager.load("nope") is False

    def test_load_disabled(self, manager):
        manager.registry.register(PluginManifest(plugin_id="m1", name="M1"))
        manager.registry.disable("m1")
        assert manager.load("m1") is False

    def test_unload(self, manager):
        manager.registry.register(PluginManifest(plugin_id="m1", name="M1", actions=[PluginAction(name="run")]))
        manager.registry.install("m1")
        manager.load("m1")
        assert manager.unload("m1") is True
        assert manager.registry.get("m1").status == PluginStatus.INSTALLED

    def test_unload_not_loaded(self, manager):
        assert manager.unload("nope") is False

    def test_execute(self, manager):
        manager.registry.register(PluginManifest(plugin_id="m1", name="M1", actions=[PluginAction(name="run")]))
        manager.registry.install("m1")
        manager.load("m1")
        result = manager.execute("m1", "run")
        assert result["status"] == "completed"
        assert result["action"] == "run"

    def test_execute_not_loaded(self, manager):
        manager.registry.register(PluginManifest(plugin_id="m1", name="M1"))
        result = manager.execute("m1", "run")
        assert result["status"] == "failed"

    def test_execute_invalid_action(self, manager):
        manager.registry.register(PluginManifest(plugin_id="m1", name="M1", actions=[PluginAction(name="run")]))
        manager.registry.install("m1")
        manager.load("m1")
        result = manager.execute("m1", "nonexistent")
        assert result["status"] == "failed"
        assert "not available" in result["error"]

    def test_get_plugin_status(self, manager):
        manager.registry.register(PluginManifest(plugin_id="m1", name="M1", actions=[PluginAction(name="go")]))
        status = manager.get_plugin_status()
        assert "m1" in status
        assert status["m1"]["name"] == "M1"
        assert "go" in status["m1"]["actions"]

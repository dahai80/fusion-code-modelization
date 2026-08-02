from __future__ import annotations

import tempfile
from pathlib import Path

from fusion_code_modelization.offline.cache import OfflineCache
from fusion_code_modelization.offline.manager import OfflineManager
from fusion_code_modelization.offline.models import (
    CAPABILITY_MATRIX,
    OfflineCapability,
    OfflineMode,
    OfflinePackage,
)


class TestOfflineMode:
    def test_enum_values(self):
        assert OfflineMode.FULL_OFFLINE.value == "full_offline"
        assert OfflineMode.SEMI_OFFLINE.value == "semi_offline"
        assert OfflineMode.ONLINE.value == "online"
        assert len(OfflineMode) == 3


class TestCapabilityMatrix:
    def test_full_offline_has_nine_capabilities(self):
        caps = CAPABILITY_MATRIX[OfflineMode.FULL_OFFLINE]
        assert len(caps) == 9
        assert OfflineCapability.CLOUD_MODEL not in caps
        assert OfflineCapability.CLUSTER not in caps
        assert OfflineCapability.PLUGIN_MARKETPLACE not in caps

    def test_online_has_all_capabilities(self):
        caps = CAPABILITY_MATRIX[OfflineMode.ONLINE]
        assert len(caps) == len(OfflineCapability)
        for cap in OfflineCapability:
            assert cap in caps


class TestOfflinePackage:
    def test_to_dict(self):
        pkg = OfflinePackage(
            name="test_pkg",
            mode=OfflineMode.SEMI_OFFLINE,
            model_ids=["m1"],
            plugin_ids=["p1"],
            size_mb=10.5,
        )
        d = pkg.to_dict()
        assert d["name"] == "test_pkg"
        assert d["mode"] == "semi_offline"
        assert d["model_ids"] == ["m1"]
        assert d["plugin_ids"] == ["p1"]
        assert d["size_mb"] == 10.5

    def test_from_dict_roundtrip(self):
        pkg = OfflinePackage(
            name="roundtrip",
            mode=OfflineMode.FULL_OFFLINE,
            model_ids=["m1", "m2"],
            plugin_ids=[],
        )
        d = pkg.to_dict()
        restored = OfflinePackage.from_dict(d)
        assert restored.name == pkg.name
        assert restored.mode == pkg.mode
        assert restored.model_ids == pkg.model_ids
        assert restored.plugin_ids == pkg.plugin_ids
        assert restored.size_mb == pkg.size_mb


class TestOfflineCache:
    def test_cache_model_creates_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = OfflineCache(cache_dir=tmp)
            result = cache.cache_model("qwen3.5-9b")
            assert result["status"] == "completed"
            assert result["model_id"] == "qwen3.5-9b"
            assert Path(result["path"]).exists()
            cached = cache.list_cached()
            assert any(e["resource_id"] == "qwen3.5-9b" and e["resource_type"] == "model" for e in cached)

    def test_cache_plugin_creates_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = OfflineCache(cache_dir=tmp)
            result = cache.cache_plugin("analyzer-plugin")
            assert result["status"] == "completed"
            assert result["plugin_id"] == "analyzer-plugin"
            cached = cache.list_cached()
            assert any(e["resource_id"] == "analyzer-plugin" and e["resource_type"] == "plugin" for e in cached)

    def test_cleanup_cache_evicts_oldest(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = OfflineCache(cache_dir=tmp)
            src1 = Path(tmp) / "model_a.bin"
            src1.write_bytes(b"x" * (2 * 1024 * 1024))
            cache.cache_model("model_a", source_path=src1)
            src2 = Path(tmp) / "model_b.bin"
            src2.write_bytes(b"y" * (3 * 1024 * 1024))
            cache.cache_model("model_b", source_path=src2)
            total_before = sum(e["size_mb"] for e in cache.list_cached())
            assert total_before > 4.0
            result = cache.cleanup_cache(max_size_mb=3.0)
            assert result["removed"] >= 1
            assert result["freed_mb"] > 0.0


class TestOfflineManager:
    def test_get_available_capabilities_returns_sorted_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = OfflineManager(cache_dir=tmp)
            mgr._current_mode = OfflineMode.FULL_OFFLINE
            caps = mgr.get_available_capabilities()
            assert caps == sorted(caps)
            assert "local_model" in caps
            assert "cloud_model" not in caps

    def test_prepare_offline_package_creates_directory_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = OfflineManager(cache_dir=tmp)
            result = mgr.prepare_offline_package(
                output_dir=tmp,
                name="test_pkg",
                model_ids=["m1"],
                plugin_ids=["p1"],
            )
            assert result["status"] == "completed"
            pkg_path = Path(result["package_path"])
            assert (pkg_path / "manifest.json").exists()
            assert (pkg_path / "models" / "m1").exists()
            assert (pkg_path / "plugins" / "p1").exists()

    def test_validate_package_checks_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = OfflineManager(cache_dir=tmp)
            mgr.prepare_offline_package(
                output_dir=tmp,
                name="valid_pkg",
                model_ids=["m1"],
                plugin_ids=["p1"],
            )
            result = mgr.validate_package(Path(tmp) / "valid_pkg")
            assert result["valid"] is True
            assert result["errors"] == []

    def test_validate_package_missing_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = OfflineManager(cache_dir=tmp)
            empty = Path(tmp) / "empty_pkg"
            empty.mkdir()
            result = mgr.validate_package(empty)
            assert result["valid"] is False
            assert "manifest.json not found" in result["errors"]

    def test_restore_from_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = OfflineManager(cache_dir=tmp)
            mgr.prepare_offline_package(
                output_dir=tmp,
                name="restore_pkg",
                model_ids=["m1"],
                plugin_ids=["p1"],
            )
            result = mgr.restore_from_package(Path(tmp) / "restore_pkg")
            assert result["status"] == "completed"
            assert result["models_restored"] == 1
            assert result["plugins_restored"] == 1

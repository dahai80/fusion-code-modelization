# GateGuard: New file. Importers: offline/manager.py, offline/__init__.py, cli/__init__.py, tests/test_offline.py. Affected API: none. Data schemas: none. User instruction: Phase 4 V2.0 — OfflineCache per enhancement doc.

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".fusion" / "offline_cache"


class CacheEntry:
    def __init__(self, resource_type: str, resource_id: str, path: Path, size_mb: float = 0.0) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.path = path
        self.size_mb = size_mb
        self.cached_at: float = time.time()

    def to_dict(self) -> dict:
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "path": str(self.path),
            "size_mb": self.size_mb,
            "cached_at": self.cached_at,
        }


class OfflineCache:
    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.cache_dir / "index.json"
        self._entries: dict[str, CacheEntry] = {}
        self._load_index()
        logger.info("OfflineCache initialized, cache_dir=%s", self.cache_dir)

    def cache_model(self, model_id: str, source_path: str | Path | None = None) -> dict:
        model_dir = self.cache_dir / "models" / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        if source_path:
            src = Path(source_path)
            if src.exists():
                marker = model_dir / ".downloaded"
                marker.write_text(f"{model_id}\n{src}")
                size_mb = src.stat().st_size / (1024 * 1024) if src.is_file() else 0.0
            else:
                size_mb = 0.0
        else:
            marker = model_dir / ".cached"
            marker.write_text(model_id)
            size_mb = 0.0
        entry = CacheEntry("model", model_id, model_dir, size_mb)
        self._entries[f"model:{model_id}"] = entry
        self._save_index()
        logger.info("Cached model: %s (%.1f MB)", model_id, size_mb)
        return {"status": "completed", "model_id": model_id, "path": str(model_dir), "size_mb": size_mb}

    def cache_plugin(self, plugin_id: str, source_path: str | Path | None = None) -> dict:
        plugin_dir = self.cache_dir / "plugins" / plugin_id
        plugin_dir.mkdir(parents=True, exist_ok=True)
        if source_path:
            src = Path(source_path)
            if src.exists():
                marker = plugin_dir / ".downloaded"
                marker.write_text(f"{plugin_id}\n{src}")
                size_mb = src.stat().st_size / (1024 * 1024) if src.is_file() else 0.0
            else:
                size_mb = 0.0
        else:
            marker = plugin_dir / ".cached"
            marker.write_text(plugin_id)
            size_mb = 0.0
        entry = CacheEntry("plugin", plugin_id, plugin_dir, size_mb)
        self._entries[f"plugin:{plugin_id}"] = entry
        self._save_index()
        logger.info("Cached plugin: %s (%.1f MB)", plugin_id, size_mb)
        return {"status": "completed", "plugin_id": plugin_id, "path": str(plugin_dir), "size_mb": size_mb}

    def list_cached(self) -> list[dict]:
        return [e.to_dict() for e in self._entries.values()]

    def cleanup_cache(self, max_size_mb: float = 1024.0) -> dict:
        total_size = sum(e.size_mb for e in self._entries.values())
        removed = 0
        freed_mb = 0.0
        if total_size <= max_size_mb:
            return {"status": "completed", "removed": 0, "freed_mb": 0.0, "total_mb": total_size}
        sorted_entries = sorted(self._entries.values(), key=lambda e: e.cached_at)
        for entry in sorted_entries:
            if total_size <= max_size_mb:
                break
            key = f"{entry.resource_type}:{entry.resource_id}"
            if key in self._entries:
                del self._entries[key]
                total_size -= entry.size_mb
                freed_mb += entry.size_mb
                removed += 1
        self._save_index()
        logger.info("Cache cleanup: removed=%d, freed=%.1f MB", removed, freed_mb)
        return {"status": "completed", "removed": removed, "freed_mb": freed_mb, "total_mb": total_size}

    def _save_index(self) -> None:
        data = {k: v.to_dict() for k, v in self._entries.items()}
        self._index_path.write_text(json.dumps(data, indent=2))

    def _load_index(self) -> None:
        if not self._index_path.exists():
            return
        try:
            data = json.loads(self._index_path.read_text())
            for key, val in data.items():
                self._entries[key] = CacheEntry(
                    resource_type=val["resource_type"],
                    resource_id=val["resource_id"],
                    path=Path(val["path"]),
                    size_mb=val.get("size_mb", 0.0),
                )
                self._entries[key].cached_at = val.get("cached_at", 0.0)
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("Failed to load cache index")

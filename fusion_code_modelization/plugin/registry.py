from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import PluginCategory, PluginManifest, PluginStatus

logger = logging.getLogger(__name__)


class PluginRegistry:
    def __init__(self, registry_dir: str = ".fusion/plugins"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self._registry_file = self.registry_dir / "registry.json"
        self._plugins: dict[str, PluginManifest] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        if not self._registry_file.exists():
            return
        try:
            data = json.loads(self._registry_file.read_text(encoding="utf-8"))
            for pid, pdata in data.items():
                self._plugins[pid] = PluginManifest.from_dict(pdata)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("failed to load plugin registry: %s", e)

    def _save_registry(self) -> None:
        data = {pid: p.to_dict() for pid, p in self._plugins.items()}
        self._registry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def register(self, manifest: PluginManifest) -> PluginManifest:
        if manifest.plugin_id in self._plugins:
            logger.warning("plugin %s already registered, updating", manifest.plugin_id)
        self._plugins[manifest.plugin_id] = manifest
        self._save_registry()
        logger.info("registered plugin: %s (%s)", manifest.plugin_id, manifest.name)
        return manifest

    def unregister(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            logger.warning("plugin %s not found for unregister", plugin_id)
            return False
        del self._plugins[plugin_id]
        self._save_registry()
        logger.info("unregistered plugin: %s", plugin_id)
        return True

    def get(self, plugin_id: str) -> PluginManifest | None:
        return self._plugins.get(plugin_id)

    def list_plugins(self, category: PluginCategory | None = None) -> list[PluginManifest]:
        plugins = list(self._plugins.values())
        if category:
            plugins = [p for p in plugins if p.category == category]
        return plugins

    def search_plugins(self, query: str) -> list[PluginManifest]:
        query_lower = query.lower()
        results = []
        for p in self._plugins.values():
            if (
                query_lower in p.name.lower()
                or query_lower in p.description.lower()
                or query_lower in p.plugin_id.lower()
            ):
                results.append(p)
        return results

    def install(self, plugin_id: str) -> PluginManifest | None:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            logger.error("install: plugin %s not found", plugin_id)
            return None
        plugin.status = PluginStatus.INSTALLED
        self._save_registry()
        logger.info("installed plugin: %s", plugin_id)
        return plugin

    def update(self, plugin_id: str, version: str = "") -> PluginManifest | None:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            logger.error("update: plugin %s not found", plugin_id)
            return None
        if version:
            plugin.version = version
        plugin.installed_at = __import__("datetime").datetime.now().isoformat()
        self._save_registry()
        logger.info("updated plugin: %s to %s", plugin_id, plugin.version)
        return plugin

    def disable(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        plugin.status = PluginStatus.DISABLED
        self._save_registry()
        logger.info("disabled plugin: %s", plugin_id)
        return True

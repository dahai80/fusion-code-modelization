from __future__ import annotations

import logging
from typing import Any

from .models import PluginStatus
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginManager:
    def __init__(self, registry: PluginRegistry | None = None):
        self._registry = registry or PluginRegistry()
        self._loaded: dict[str, dict[str, Any]] = {}

    def load(self, plugin_id: str) -> bool:
        plugin = self._registry.get(plugin_id)
        if not plugin:
            logger.error("load: plugin %s not found", plugin_id)
            return False
        if plugin.status == PluginStatus.DISABLED:
            logger.error("load: plugin %s is disabled", plugin_id)
            return False
        self._loaded[plugin_id] = {"manifest": plugin, "runtime": {}}
        plugin.status = PluginStatus.LOADED
        logger.info("loaded plugin: %s", plugin_id)
        return True

    def unload(self, plugin_id: str) -> bool:
        if plugin_id not in self._loaded:
            logger.warning("unload: plugin %s not loaded", plugin_id)
            return False
        del self._loaded[plugin_id]
        plugin = self._registry.get(plugin_id)
        if plugin:
            plugin.status = PluginStatus.INSTALLED
        logger.info("unloaded plugin: %s", plugin_id)
        return True

    def execute(self, plugin_id: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if plugin_id not in self._loaded:
            logger.error("execute: plugin %s not loaded", plugin_id)
            return {"status": "failed", "error": f"plugin {plugin_id} not loaded"}
        plugin = self._registry.get(plugin_id)
        if not plugin:
            return {"status": "failed", "error": f"plugin {plugin_id} not in registry"}
        valid_actions = [a.name for a in plugin.actions]
        if action not in valid_actions:
            logger.error("execute: action '%s' not found in plugin %s", action, plugin_id)
            return {"status": "failed", "error": f"action '{action}' not available"}
        logger.info("executing plugin %s action %s", plugin_id, action)
        return {
            "status": "completed",
            "plugin_id": plugin_id,
            "action": action,
            "result": f"executed {action} on {plugin.name}",
            "params": params or {},
        }

    def get_plugin_status(self) -> dict[str, Any]:
        all_plugins = self._registry.list_plugins()
        status_map = {}
        for p in all_plugins:
            status_map[p.plugin_id] = {
                "name": p.name,
                "status": p.status.value,
                "loaded": p.plugin_id in self._loaded,
                "actions": [a.name for a in p.actions],
            }
        return status_map

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

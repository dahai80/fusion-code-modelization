from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class PluginCategory(StrEnum):
    DATABASE = "database"
    VCS = "vcs"
    PROJECT_MANAGEMENT = "project_management"
    DESIGN = "design"
    TESTING = "testing"
    CI_CD = "ci_cd"
    CLOUD = "cloud"
    SECURITY = "security"
    CUSTOM = "custom"


class PluginStatus(StrEnum):
    REGISTERED = "registered"
    INSTALLED = "installed"
    LOADED = "loaded"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginAction:
    name: str
    description: str = ""
    params_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "params_schema": self.params_schema,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginAction:
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            params_schema=data.get("params_schema", {}),
        )


@dataclass
class PluginManifest:
    plugin_id: str
    name: str
    version: str = "1.0.0"
    category: PluginCategory = PluginCategory.CUSTOM
    description: str = ""
    author: str = ""
    homepage: str = ""
    actions: list[PluginAction] = field(default_factory=list)
    installed_at: str = ""
    status: PluginStatus = PluginStatus.REGISTERED
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.installed_at:
            self.installed_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "category": self.category.value,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "actions": [a.to_dict() for a in self.actions],
            "installed_at": self.installed_at,
            "status": self.status.value,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        actions = [PluginAction.from_dict(a) for a in data.get("actions", [])]
        return cls(
            plugin_id=data.get("plugin_id", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            category=PluginCategory(data.get("category", "custom")),
            description=data.get("description", ""),
            author=data.get("author", ""),
            homepage=data.get("homepage", ""),
            actions=actions,
            installed_at=data.get("installed_at", ""),
            status=PluginStatus(data.get("status", "registered")),
            config=data.get("config", {}),
        )

# GateGuard: New file. Importers: offline/__init__.py, offline/manager.py, offline/cache.py, cli/__init__.py, tests/test_offline.py. Affected API: none. Data schemas: OfflineMode, OfflineCapability, OfflinePackage. User instruction: Phase 4 V2.0 — offline models per enhancement doc.

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime


class OfflineMode(enum.StrEnum):
    FULL_OFFLINE = "full_offline"
    SEMI_OFFLINE = "semi_offline"
    ONLINE = "online"


class OfflineCapability(enum.StrEnum):
    LOCAL_MODEL = "local_model"
    CLOUD_MODEL = "cloud_model"
    CLUSTER = "cluster"
    AUDIT = "audit"
    PLUGIN_MARKETPLACE = "plugin_marketplace"
    PLUGIN_LOCAL = "plugin_local"
    TRACE = "trace"
    BENCHMARK = "benchmark"
    SESSION = "session"
    SNAPSHOT = "snapshot"
    SECURITY = "security"
    MIGRATION = "migration"


CAPABILITY_MATRIX: dict[OfflineMode, set[OfflineCapability]] = {
    OfflineMode.FULL_OFFLINE: {
        OfflineCapability.LOCAL_MODEL,
        OfflineCapability.AUDIT,
        OfflineCapability.PLUGIN_LOCAL,
        OfflineCapability.TRACE,
        OfflineCapability.BENCHMARK,
        OfflineCapability.SESSION,
        OfflineCapability.SNAPSHOT,
        OfflineCapability.SECURITY,
        OfflineCapability.MIGRATION,
    },
    OfflineMode.SEMI_OFFLINE: {
        OfflineCapability.LOCAL_MODEL,
        OfflineCapability.CLOUD_MODEL,
        OfflineCapability.AUDIT,
        OfflineCapability.PLUGIN_LOCAL,
        OfflineCapability.PLUGIN_MARKETPLACE,
        OfflineCapability.TRACE,
        OfflineCapability.BENCHMARK,
        OfflineCapability.SESSION,
        OfflineCapability.SNAPSHOT,
        OfflineCapability.SECURITY,
        OfflineCapability.MIGRATION,
    },
    OfflineMode.ONLINE: set(OfflineCapability),
}


@dataclass
class OfflinePackage:
    package_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    mode: OfflineMode = OfflineMode.FULL_OFFLINE
    model_ids: list[str] = field(default_factory=list)
    plugin_ids: list[str] = field(default_factory=list)
    config_path: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    size_mb: float = 0.0
    checksum: str = ""

    def to_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "name": self.name,
            "mode": self.mode.value,
            "model_ids": self.model_ids,
            "plugin_ids": self.plugin_ids,
            "config_path": self.config_path,
            "created_at": self.created_at,
            "size_mb": self.size_mb,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OfflinePackage:
        return cls(
            package_id=data.get("package_id", uuid.uuid4().hex[:12]),
            name=data.get("name", ""),
            mode=OfflineMode(data.get("mode", "full_offline")),
            model_ids=data.get("model_ids", []),
            plugin_ids=data.get("plugin_ids", []),
            config_path=data.get("config_path", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            size_mb=data.get("size_mb", 0.0),
            checksum=data.get("checksum", ""),
        )

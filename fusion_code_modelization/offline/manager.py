# GateGuard: New file. Importers: offline/__init__.py, cli/__init__.py, tests/test_offline.py. Affected API: none. Data schemas: none. User instruction: Phase 4 V2.0 — OfflineManager class per enhancement doc.

from __future__ import annotations

import hashlib
import json
import logging
import socket
from pathlib import Path

from ..core.config import GATEWAY_PORT
from .cache import OfflineCache
from .models import CAPABILITY_MATRIX, OfflineMode, OfflinePackage

logger = logging.getLogger(__name__)

PACKAGE_DIR = Path.home() / ".fusion" / "offline_packages"


class OfflineManager:
    def __init__(self, cache_dir: str | Path | None = None, package_dir: str | Path | None = None) -> None:
        self.cache = OfflineCache(cache_dir)
        self.package_dir = Path(package_dir) if package_dir else PACKAGE_DIR
        self.package_dir.mkdir(parents=True, exist_ok=True)
        self._current_mode: OfflineMode | None = None
        logger.info("OfflineManager initialized")

    def detect_mode(self) -> OfflineMode:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            has_cloud = self._check_cloud_api()
            if has_cloud:
                self._current_mode = OfflineMode.ONLINE
            else:
                self._current_mode = OfflineMode.SEMI_OFFLINE
        except OSError:
            has_local = self._check_gateway()
            if has_local:
                self._current_mode = OfflineMode.SEMI_OFFLINE
            else:
                self._current_mode = OfflineMode.FULL_OFFLINE
        logger.info("Detected offline mode: %s", self._current_mode.value)
        return self._current_mode

    def _check_cloud_api(self) -> bool:
        try:
            socket.create_connection(("api.anthropic.com", 443), timeout=3)
            return True
        except OSError:
            return False

    def _check_gateway(self) -> bool:
        try:
            sock = socket.create_connection(("localhost", GATEWAY_PORT), timeout=2)
            sock.close()
            return True
        except OSError:
            return False

    def get_available_capabilities(self) -> list[str]:
        mode = self._current_mode or self.detect_mode()
        capabilities = CAPABILITY_MATRIX.get(mode, set())
        return sorted(c.value for c in capabilities)

    def prepare_offline_package(
        self,
        output_dir: str | Path,
        name: str = "offline_package",
        model_ids: list[str] | None = None,
        plugin_ids: list[str] | None = None,
    ) -> dict:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        model_ids = model_ids or []
        plugin_ids = plugin_ids or []
        pkg_dir = out / name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "models").mkdir(exist_ok=True)
        for mid in model_ids:
            (pkg_dir / "models" / mid).mkdir(exist_ok=True)
            (pkg_dir / "models" / mid / ".model_id").write_text(mid)
        (pkg_dir / "plugins").mkdir(exist_ok=True)
        for pid in plugin_ids:
            (pkg_dir / "plugins" / pid).mkdir(exist_ok=True)
            (pkg_dir / "plugins" / pid / ".plugin_id").write_text(pid)
        pkg = OfflinePackage(
            name=name,
            mode=OfflineMode.FULL_OFFLINE,
            model_ids=model_ids,
            plugin_ids=plugin_ids,
            config_path=str(pkg_dir),
        )
        manifest = pkg.to_dict()
        manifest.pop("checksum", "")
        manifest["checksum"] = self._compute_checksum(manifest)
        (pkg_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        size_mb = self._dir_size_mb(pkg_dir)
        logger.info("Prepared offline package: %s at %s (%.1f MB)", name, pkg_dir, size_mb)
        return {
            "status": "completed",
            "package_path": str(pkg_dir),
            "package_id": pkg.package_id,
            "mode": pkg.mode.value,
            "size_mb": size_mb,
            "model_count": len(model_ids),
            "plugin_count": len(plugin_ids),
        }

    @staticmethod
    def _dir_size_mb(path: Path) -> float:
        total = 0
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
        return round(total / (1024 * 1024), 1)

    def restore_from_package(self, package_dir: str | Path) -> dict:
        pkg_path = Path(package_dir)
        manifest_path = pkg_path / "manifest.json"
        if not manifest_path.exists():
            logger.error("No manifest.json in package: %s", package_dir)
            return {"status": "failed", "error": "manifest_not_found"}
        try:
            data = json.loads(manifest_path.read_text())
            pkg = OfflinePackage.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Invalid manifest: %s", e)
            return {"status": "failed", "error": f"invalid_manifest: {e}"}
        for mid in pkg.model_ids:
            self.cache.cache_model(mid)
        for pid in pkg.plugin_ids:
            self.cache.cache_plugin(pid)
        logger.info("Restored package %s: %d models, %d plugins", pkg.name, len(pkg.model_ids), len(pkg.plugin_ids))
        return {
            "status": "completed",
            "package_id": pkg.package_id,
            "models_restored": len(pkg.model_ids),
            "plugins_restored": len(pkg.plugin_ids),
        }

    def validate_package(self, package_dir: str | Path) -> dict:
        pkg_path = Path(package_dir)
        manifest_path = pkg_path / "manifest.json"
        if not manifest_path.exists():
            return {"valid": False, "errors": ["manifest.json not found"]}
        try:
            data = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            return {"valid": False, "errors": ["manifest.json is not valid JSON"]}
        errors = []
        stored_checksum = data.pop("checksum", "")
        if stored_checksum:
            computed = self._compute_checksum(data)
            if computed != stored_checksum:
                errors.append("checksum_mismatch")
        for mid in data.get("model_ids", []):
            if not (pkg_path / "models" / mid).exists():
                errors.append(f"model_dir_missing: {mid}")
        for pid in data.get("plugin_ids", []):
            if not (pkg_path / "plugins" / pid).exists():
                errors.append(f"plugin_dir_missing: {pid}")
        valid = len(errors) == 0
        logger.info("Package validation: valid=%s, errors=%d", valid, len(errors))
        return {"valid": valid, "errors": errors}

    def _compute_checksum(self, data: dict) -> str:
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

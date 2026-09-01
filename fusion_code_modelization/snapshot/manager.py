from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any

from ..core.hooks import HookRegistry
from ..core.safe_writer import SafeWriter, UnsafePathError
from .delta import FileDelta, Snapshot, compute_delta

logger = logging.getLogger(__name__)

_SNAPSHOT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")
_MAX_SCAN_FILE_BYTES = 5 * 1024 * 1024


def _validate_snapshot_id(snapshot_id: str) -> str:
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID_RE.match(snapshot_id):
        logger.warning("rejected invalid snapshot_id: %r", snapshot_id)
        raise ValueError(f"invalid snapshot_id: {snapshot_id!r}")
    return snapshot_id


class SnapshotManager:
    def __init__(
        self,
        project_dir: str | Path,
        snapshot_dir: str | Path | None = None,
        hooks: HookRegistry | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else self.project_dir / ".fusion" / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._writer = SafeWriter(self.project_dir, registry=hooks)
        logger.info("SnapshotManager init: project=%s snapshot_dir=%s", self.project_dir, self.snapshot_dir)

    def _file_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _read_file(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def _safe_write(self, target: Path, content: str) -> bool:
        if target.is_symlink():
            logger.error("refusing write through symlink: %s", target)
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return True

    def _collect_files(self) -> dict[str, str]:
        files: dict[str, str] = {}
        ignore_dirs = {
            ".git",
            ".fusion",
            "__pycache__",
            "node_modules",
            ".venv",
            ".mypy_cache",
            "build",
            "dist",
            "target",
            ".pytest_cache",
            ".ruff_cache",
            ".tox",
        }
        import os

        skipped_large = 0
        for root, dirs, fnames in os.walk(self.project_dir, followlinks=False):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for fname in fnames:
                p = Path(root) / fname
                if p.is_symlink():
                    logger.warning("skipping symlink in snapshot: %s", p)
                    continue
                if not p.is_file():
                    continue
                try:
                    if p.stat().st_size > _MAX_SCAN_FILE_BYTES:
                        skipped_large += 1
                        continue
                except OSError:
                    continue
                rel = str(p.relative_to(self.project_dir))
                content = self._read_file(p)
                if content is not None:
                    files[rel] = content
        if skipped_large:
            logger.warning("skipped %d files exceeding %d bytes during scan", skipped_large, _MAX_SCAN_FILE_BYTES)
        return files

    def create_snapshot(self, label: str = "") -> Snapshot:
        logger.info("Creating snapshot label=%s", label)
        current_files = self._collect_files()
        previous = self._load_latest_snapshot()
        deltas: list[FileDelta] = []

        previous_map: dict[str, str] = {}
        if previous:
            for d in previous.deltas:
                previous_map[d.path] = d.diff if not d.is_deleted else ""

        all_paths = set(current_files.keys()) | set(previous_map.keys())

        for path in sorted(all_paths):
            old_content = previous_map.get(path, "")
            new_content = current_files.get(path)

            if new_content is None:
                delta = FileDelta(path=path, is_deleted=True)
                old_hash = self._file_hash(old_content) if old_content else ""
                delta.old_hash = old_hash
                deltas.append(delta)
                continue

            new_hash = self._file_hash(new_content)

            if path not in previous_map:
                delta = FileDelta(path=path, new_hash=new_hash, is_new=True)
                deltas.append(delta)
                continue

            if old_content != new_content:
                delta = compute_delta(old_content, new_content, path)
                delta.old_hash = self._file_hash(old_content)
                delta.new_hash = new_hash
                deltas.append(delta)
                continue

        snapshot_id = f"snap_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            label=label,
            deltas=deltas,
            created_at=time.time(),
        )
        self._save_snapshot(snapshot)
        logger.info("Snapshot created: %s with %d deltas", snapshot_id, len(deltas))
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> bool:
        logger.info("Restoring snapshot: %s", snapshot_id)
        snapshot = self.load_snapshot(snapshot_id)
        if not snapshot:
            logger.error("Snapshot not found: %s", snapshot_id)
            return False

        rollback_id = f"rollback_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        try:
            current_files = self._collect_files()
            rollback = Snapshot(
                snapshot_id=rollback_id,
                label=f"rollback-before-{snapshot_id}",
                deltas=[],
                created_at=time.time(),
                files=current_files,
            )
            self._save_snapshot(rollback)
            logger.info("rollback snapshot saved: %s (%d files)", rollback_id, len(current_files))
        except Exception as e:
            logger.warning("rollback snapshot failed, proceeding non-atomic: %s", e)

        applied: list[str] = []
        try:
            for delta in snapshot.deltas:
                try:
                    resolved = self._writer.resolve_within(delta.path)
                except UnsafePathError as e:
                    logger.error("restore blocked unsafe path %s: %s", delta.path, e)
                    continue
                target = resolved
                if delta.is_deleted:
                    if target.exists():
                        target.unlink()
                        logger.info("Deleted: %s", delta.path)
                    applied.append(delta.path)
                    continue

                if delta.is_new:
                    content = self._reconstruct_from_diff(delta)
                    if self._safe_write(target, content):
                        logger.info("Restored new file: %s", delta.path)
                        applied.append(delta.path)
                    continue

                if delta.diff:
                    current = self._read_file(target) or ""
                    from .delta import apply_delta

                    restored = apply_delta(current, delta)
                    if self._safe_write(target, restored):
                        logger.info("Restored modified: %s", delta.path)
                        applied.append(delta.path)
        except Exception as e:
            logger.error(
                "restore failed mid-way at %d/%d deltas, rolling back: %s", len(applied), len(snapshot.deltas), e
            )
            if rollback_id:
                self._rollback_from(rollback_id)
            return False

        logger.info("Snapshot %s restored", snapshot_id)
        if rollback_id:
            self.delete_snapshot(rollback_id)
            logger.info("rollback snapshot %s cleaned up", rollback_id)
        return True

    def _rollback_from(self, rollback_id: str) -> None:
        rollback = self.load_snapshot(rollback_id)
        if not rollback or not getattr(rollback, "files", None):
            logger.error("rollback snapshot %s missing files, manual recovery needed", rollback_id)
            return
        rollback_files = rollback.files
        if rollback_files is None:
            logger.error("rollback snapshot %s files resolved None", rollback_id)
            return
        try:
            current_files = self._collect_files()
            for rel in current_files:
                if rel not in rollback_files:
                    p = self._writer.resolve_within(rel)
                    if p.exists():
                        p.unlink()
            for rel, content in rollback_files.items():
                target = self._writer.resolve_within(rel)
                self._safe_write(target, content)
            logger.info("rollback complete from %s", rollback_id)
        except Exception as e:
            logger.error("rollback itself failed: %s", e)

    def list_snapshots(self) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        for f in self.snapshot_dir.glob("snap_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                snapshots.append(
                    {
                        "snapshot_id": data.get("snapshot_id", f.stem),
                        "label": data.get("label", ""),
                        "created_at": data.get("created_at", 0),
                        "delta_count": len(data.get("deltas", [])),
                    }
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read snapshot %s: %s", f, e)
        snapshots.sort(key=lambda s: s["created_at"])
        return snapshots

    def rewind(self, steps: int = 1) -> Snapshot | None:
        snapshots = self.list_snapshots()
        if len(snapshots) < steps + 1:
            logger.error("Cannot rewind %d steps, only %d snapshots", steps, len(snapshots))
            return None
        target = snapshots[-(steps + 1)]
        logger.info("Rewinding %d steps to %s", steps, target["snapshot_id"])
        self.restore_snapshot(target["snapshot_id"])
        return self.load_snapshot(target["snapshot_id"])

    def load_snapshot(self, snapshot_id: str) -> Snapshot | None:
        try:
            fpath = self.snapshot_dir / f"{_validate_snapshot_id(snapshot_id)}.json"
        except ValueError:
            return None
        if not fpath.exists():
            return None
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            deltas = [FileDelta(**d) for d in data.get("deltas", [])]
            return Snapshot(
                snapshot_id=data["snapshot_id"],
                label=data.get("label", ""),
                deltas=deltas,
                created_at=data.get("created_at", 0),
                files=data.get("files"),
            )
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.error("Failed to load snapshot %s: %s", snapshot_id, e)
            return None

    def delete_snapshot(self, snapshot_id: str) -> bool:
        try:
            fpath = self.snapshot_dir / f"{_validate_snapshot_id(snapshot_id)}.json"
        except ValueError:
            return False
        if fpath.exists():
            fpath.unlink()
            logger.info("Deleted snapshot: %s", snapshot_id)
            return True
        return False

    def _save_snapshot(self, snapshot: Snapshot) -> None:
        fpath = self.snapshot_dir / f"{snapshot.snapshot_id}.json"
        fpath.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug("Saved snapshot to %s", fpath)

    def _load_latest_snapshot(self) -> Snapshot | None:
        snapshots = self.list_snapshots()
        if not snapshots:
            return None
        latest = snapshots[-1]
        return self.load_snapshot(latest["snapshot_id"])

    def get_storage_stats(self) -> dict[str, Any]:
        snapshot_files = list(self.snapshot_dir.glob("snap_*.json"))
        total_size = sum(f.stat().st_size for f in snapshot_files if f.is_file())
        compressed_files = list(self.snapshot_dir.glob("snap_*.json.gz"))
        compressed_size = sum(f.stat().st_size for f in compressed_files if f.is_file())
        return {
            "snapshot_count": len(snapshot_files),
            "compressed_count": len(compressed_files),
            "total_size_bytes": total_size + compressed_size,
            "total_size_mb": round((total_size + compressed_size) / (1024 * 1024), 2),
            "snapshot_dir": str(self.snapshot_dir),
        }

    def auto_cleanup(self, max_age_days: int = 30, max_snapshots: int = 50) -> int:
        import time as _time

        removed = 0
        snapshots = self.list_snapshots()
        cutoff = _time.time() - (max_age_days * 86400)
        for s in snapshots:
            if s["created_at"] < cutoff:
                self.delete_snapshot(s["snapshot_id"])
                removed += 1
        if len(snapshots) - removed > max_snapshots:
            remaining = [s for s in snapshots if s["created_at"] >= cutoff]
            remaining.sort(key=lambda s: s["created_at"])
            excess = len(remaining) - max_snapshots
            for s in remaining[:excess]:
                self.delete_snapshot(s["snapshot_id"])
                removed += 1
        logger.info(
            "auto_cleanup: removed %d snapshots (max_age=%d days, max_count=%d)", removed, max_age_days, max_snapshots
        )
        return removed

    def compress_snapshot(self, snapshot_id: str) -> bool:
        import gzip
        import shutil

        try:
            sid = _validate_snapshot_id(snapshot_id)
        except ValueError:
            return False
        src = self.snapshot_dir / f"{sid}.json"
        dst = self.snapshot_dir / f"{sid}.json.gz"
        if not src.exists():
            logger.error("compress_snapshot: %s not found", snapshot_id)
            return False
        with open(src, "rb") as f_in, gzip.open(dst, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        src.unlink()
        logger.info("compressed snapshot %s: %s -> %s", snapshot_id, src, dst)
        return True

    def verify_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        snapshot = self.load_snapshot(snapshot_id)
        if not snapshot:
            return {"valid": False, "error": "snapshot not found"}
        issues: list[str] = []
        for delta in snapshot.deltas:
            if delta.is_deleted:
                continue
            target = self.project_dir / delta.path
            if delta.is_new:
                if not target.exists():
                    issues.append(f"new file missing: {delta.path}")
            elif delta.diff:
                current = self._read_file(target)
                if current is None:
                    issues.append(f"modified file missing: {delta.path}")
        return {
            "valid": len(issues) == 0,
            "snapshot_id": snapshot_id,
            "delta_count": len(snapshot.deltas),
            "issues": issues,
        }

    def _reconstruct_from_diff(self, delta: FileDelta) -> str:
        if delta.diff:
            from .delta import apply_delta

            return apply_delta("", delta)
        return ""

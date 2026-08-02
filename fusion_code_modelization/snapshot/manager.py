from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from .delta import FileDelta, Snapshot, compute_delta

logger = logging.getLogger(__name__)


class SnapshotManager:
    def __init__(self, project_dir: str | Path, snapshot_dir: str | Path | None = None):
        self.project_dir = Path(project_dir).resolve()
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else self.project_dir / ".fusion" / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        logger.info("SnapshotManager init: project=%s snapshot_dir=%s", self.project_dir, self.snapshot_dir)

    def _file_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _read_file(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def _collect_files(self) -> dict[str, str]:
        files: dict[str, str] = {}
        ignore_dirs = {".git", ".fusion", "__pycache__", "node_modules", ".venv", ".mypy_cache"}
        for p in self.project_dir.rglob("*"):
            if not p.is_file():
                continue
            if any(part in ignore_dirs for part in p.parts):
                continue
            rel = str(p.relative_to(self.project_dir))
            content = self._read_file(p)
            if content is not None:
                files[rel] = content
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

        for delta in snapshot.deltas:
            target = self.project_dir / delta.path
            if delta.is_deleted:
                if target.exists():
                    target.unlink()
                    logger.info("Deleted: %s", delta.path)
                continue

            if delta.is_new:
                target.parent.mkdir(parents=True, exist_ok=True)
                content = self._reconstruct_from_diff(delta)
                target.write_text(content, encoding="utf-8")
                logger.info("Restored new file: %s", delta.path)
                continue

            if delta.diff:
                current = self._read_file(target) or ""
                from .delta import apply_delta

                restored = apply_delta(current, delta)
                target.write_text(restored, encoding="utf-8")
                logger.info("Restored modified: %s", delta.path)

        logger.info("Snapshot %s restored", snapshot_id)
        return True

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
        fpath = self.snapshot_dir / f"{snapshot_id}.json"
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
            )
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.error("Failed to load snapshot %s: %s", snapshot_id, e)
            return None

    def delete_snapshot(self, snapshot_id: str) -> bool:
        fpath = self.snapshot_dir / f"{snapshot_id}.json"
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

    def _reconstruct_from_diff(self, delta: FileDelta) -> str:
        if delta.diff:
            from .delta import apply_delta

            return apply_delta("", delta)
        return ""

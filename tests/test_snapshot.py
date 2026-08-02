from __future__ import annotations

import json

import pytest

from fusion_code_modelization.snapshot import (
    FileDelta,
    Snapshot,
    SnapshotManager,
    apply_delta,
    compute_delta,
)


class TestFileDelta:
    def test_to_dict(self):
        d = FileDelta(path="a.py", old_hash="h1", new_hash="h2", diff="@@ -1 +1 @@", is_new=False, is_deleted=False)
        result = d.to_dict()
        assert result["path"] == "a.py"
        assert result["old_hash"] == "h1"
        assert result["new_hash"] == "h2"
        assert result["diff"] == "@@ -1 +1 @@"
        assert result["is_new"] is False
        assert result["is_deleted"] is False

    def test_defaults(self):
        d = FileDelta(path="b.py")
        assert d.old_hash == ""
        assert d.new_hash == ""
        assert d.diff == ""
        assert d.is_new is False
        assert d.is_deleted is False


class TestSnapshot:
    def test_to_dict(self):
        d = FileDelta(path="a.py", is_new=True)
        s = Snapshot(snapshot_id="snap_1", label="test", deltas=[d], created_at=1.0)
        result = s.to_dict()
        assert result["snapshot_id"] == "snap_1"
        assert result["label"] == "test"
        assert len(result["deltas"]) == 1
        assert result["created_at"] == 1.0

    def test_defaults(self):
        s = Snapshot(snapshot_id="snap_2")
        assert s.label == ""
        assert s.deltas == []
        assert s.created_at == 0.0


class TestComputeDelta:
    def test_identical_content(self):
        delta = compute_delta("hello\n", "hello\n", "a.py")
        assert delta.diff == ""
        assert delta.path == "a.py"

    def test_modified_content(self):
        old = "line1\nline2\n"
        new = "line1\nline3\n"
        delta = compute_delta(old, new, "a.py")
        assert delta.path == "a.py"
        assert delta.diff != ""
        assert "-line2" in delta.diff
        assert "+line3" in delta.diff

    def test_empty_old(self):
        delta = compute_delta("", "new\n", "a.py")
        assert delta.diff != ""
        assert "+new" in delta.diff


class TestApplyDelta:
    def test_deleted_file(self):
        delta = FileDelta(path="a.py", is_deleted=True)
        result = apply_delta("content", delta)
        assert result == ""

    def test_new_file_no_diff(self):
        delta = FileDelta(path="a.py", is_new=True)
        result = apply_delta("new content", delta)
        assert result == "new content"

    def test_apply_patch(self):
        old = "line1\nline2\n"
        new = "line1\nline3\n"
        delta = compute_delta(old, new, "a.py")
        restored = apply_delta(new, delta)
        assert "line3" in restored

    def test_empty_diff_returns_content(self):
        delta = FileDelta(path="a.py", diff="")
        result = apply_delta("unchanged", delta)
        assert result == "unchanged"


class TestSnapshotManager:
    @pytest.fixture
    def project_dir(self, tmp_path):
        p = tmp_path / "project"
        p.mkdir()
        (p / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (p / "util.py").write_text("def util(): pass\n", encoding="utf-8")
        return p

    @pytest.fixture
    def manager(self, project_dir, tmp_path):
        snap_dir = tmp_path / "snaps"
        return SnapshotManager(project_dir, snapshot_dir=snap_dir)

    def test_create_first_snapshot(self, manager):
        snap = manager.create_snapshot(label="initial")
        assert snap.snapshot_id.startswith("snap_")
        assert snap.label == "initial"
        assert len(snap.deltas) >= 2
        assert all(d.is_new for d in snap.deltas)

    def test_create_snapshot_saves_to_disk(self, manager):
        snap = manager.create_snapshot(label="v1")
        loaded = manager.load_snapshot(snap.snapshot_id)
        assert loaded is not None
        assert loaded.snapshot_id == snap.snapshot_id
        assert loaded.label == "v1"

    def test_list_snapshots(self, manager):
        manager.create_snapshot(label="first")
        manager.create_snapshot(label="second")
        snaps = manager.list_snapshots()
        assert len(snaps) == 2
        assert snaps[0]["label"] == "first"
        assert snaps[1]["label"] == "second"

    def test_delete_snapshot(self, manager):
        snap = manager.create_snapshot(label="to_delete")
        assert manager.delete_snapshot(snap.snapshot_id) is True
        assert manager.load_snapshot(snap.snapshot_id) is None

    def test_delete_nonexistent(self, manager):
        assert manager.delete_snapshot("snap_999") is False

    def test_second_snapshot_detects_changes(self, manager, project_dir):
        manager.create_snapshot(label="v1")
        (project_dir / "main.py").write_text("print('changed')\n", encoding="utf-8")
        snap2 = manager.create_snapshot(label="v2")
        changed = [d for d in snap2.deltas if d.diff]
        assert len(changed) >= 1

    def test_rewind(self, manager, project_dir):
        manager.create_snapshot(label="v1")
        (project_dir / "main.py").write_text("print('changed')\n", encoding="utf-8")
        manager.create_snapshot(label="v2")
        result = manager.rewind(steps=1)
        assert result is not None

    def test_rewind_too_far(self, manager):
        manager.create_snapshot(label="v1")
        result = manager.rewind(steps=5)
        assert result is None

    def test_snapshot_to_dict_roundtrip(self, manager):
        snap = manager.create_snapshot(label="roundtrip")
        data = snap.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert parsed["snapshot_id"] == snap.snapshot_id
        assert len(parsed["deltas"]) == len(snap.deltas)

    def test_ignores_hidden_dirs(self, tmp_path):
        p = tmp_path / "proj"
        p.mkdir()
        (p / "main.py").write_text("code\n", encoding="utf-8")
        git_dir = p / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("gitdata", encoding="utf-8")
        snap_dir = tmp_path / "snaps"
        mgr = SnapshotManager(p, snapshot_dir=snap_dir)
        snap = mgr.create_snapshot()
        paths = [d.path for d in snap.deltas]
        assert "main.py" in paths
        assert not any(".git" in pa for pa in paths)

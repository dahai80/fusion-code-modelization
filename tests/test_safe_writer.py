from __future__ import annotations

import os
from pathlib import Path

import pytest

from fusion_code_modelization.core.safe_writer import SafeWriter, UnsafePathError


class TestSafeWriterTraversal:
    def test_blocks_dotdot_escape(self, tmp_path):
        writer = SafeWriter(tmp_path)
        with pytest.raises(UnsafePathError, match="escapes project_root"):
            writer.write_text("../evil.txt", "data")

    def test_blocks_absolute_outside_root(self, tmp_path):
        writer = SafeWriter(tmp_path)
        with pytest.raises(UnsafePathError, match="escapes project_root"):
            writer.write_text("/etc/evil.txt", "data")

    def test_blocks_symlink_escape(self, tmp_path):
        writer = SafeWriter(tmp_path)
        link = tmp_path / "link.txt"
        target = tmp_path.parent / "outside.txt"
        os.symlink(target, link)
        with pytest.raises(UnsafePathError, match="escapes project_root"):
            writer.write_text("link.txt", "data")

    def test_allows_path_inside_root(self, tmp_path):
        writer = SafeWriter(tmp_path)
        p = writer.write_text("sub/inner.txt", "data")
        assert p.read_text() == "data"
        assert p.resolve().is_relative_to(tmp_path.resolve())

    def test_unlink_blocks_traversal(self, tmp_path):
        writer = SafeWriter(tmp_path)
        with pytest.raises(UnsafePathError, match="escapes project_root"):
            writer.unlink("../evil.txt")

    def test_non_strict_allows_outside(self, tmp_path):
        writer = SafeWriter(tmp_path, strict=False)
        # non-strict resolve does not raise; used for export paths
        resolved = writer.resolve_within("/tmp/some_export.json")
        assert resolved == Path("/tmp/some_export.json").resolve()

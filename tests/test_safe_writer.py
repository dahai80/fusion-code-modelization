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

    def test_write_bytes_roundtrip(self, tmp_path):
        writer = SafeWriter(tmp_path)
        p = writer.write_bytes("bin.dat", b"\x00\x01\x02")
        assert p.read_bytes() == b"\x00\x01\x02"

    def test_write_json_roundtrip(self, tmp_path):
        import json

        writer = SafeWriter(tmp_path)
        p = writer.write_json("out.json", {"k": 1})
        assert json.loads(p.read_text()) == {"k": 1}

    def test_mkdir_creates_dir(self, tmp_path):
        writer = SafeWriter(tmp_path)
        p = writer.mkdir("nested/deep")
        assert p.is_dir()

    def test_unlink_missing_returns_false(self, tmp_path):
        writer = SafeWriter(tmp_path)
        assert writer.unlink("nope.txt") is False

    def test_hook_deny_blocks_write(self, tmp_path):
        from fusion_code_modelization.core.hooks import (
            HookAction,
            HookDecision,
            HookEvent,
            HookHandler,
            HookRegistry,
        )

        def _deny(payload):
            return HookDecision(action=HookAction.DENY, reason="blocked")

        handler = HookHandler(name="deny", event=HookEvent.PRE_WRITE, execute=_deny)
        reg = HookRegistry()
        reg.register(handler)
        reg.enabled = True
        writer = SafeWriter(tmp_path, registry=reg)
        with pytest.raises(UnsafePathError, match="hook denied"):
            writer.write_text("ok.txt", "data")

    def test_async_pre_write_deny_blocks_sync_write(self, tmp_path):
        from fusion_code_modelization.core.hooks import (
            HookAction,
            HookDecision,
            HookEvent,
            HookHandler,
            HookRegistry,
        )

        async def _deny(payload):
            return HookDecision(action=HookAction.DENY, reason="async_blocked")

        reg = HookRegistry()
        reg.register(HookHandler(name="async_deny", event=HookEvent.PRE_WRITE, execute=_deny))
        writer = SafeWriter(tmp_path, registry=reg)
        with pytest.raises(UnsafePathError, match="async_blocked"):
            writer.write_text("ok.txt", "data")

    async def test_async_pre_write_deny_blocks_write_inside_event_loop(self, tmp_path):
        from fusion_code_modelization.core.hooks import (
            HookAction,
            HookDecision,
            HookEvent,
            HookHandler,
            HookRegistry,
        )

        async def _deny(payload):
            return HookDecision(action=HookAction.DENY, reason="loop_async_blocked")

        reg = HookRegistry()
        reg.register(HookHandler(name="async_deny", event=HookEvent.PRE_WRITE, execute=_deny))
        writer = SafeWriter(tmp_path, registry=reg)
        with pytest.raises(UnsafePathError, match="loop_async_blocked"):
            writer.write_text("ok.txt", "data")

    def test_async_pre_write_modify_applied_sync(self, tmp_path):
        from fusion_code_modelization.core.hooks import (
            HookAction,
            HookDecision,
            HookEvent,
            HookHandler,
            HookRegistry,
        )

        async def _modify(payload):
            return HookDecision(action=HookAction.MODIFY, reason="rewrite", modified_content="scrubbed")

        reg = HookRegistry()
        reg.register(HookHandler(name="async_modify", event=HookEvent.PRE_WRITE, execute=_modify))
        writer = SafeWriter(tmp_path, registry=reg)
        writer.write_text("ok.txt", "secret")
        assert (tmp_path / "ok.txt").read_text() == "scrubbed"

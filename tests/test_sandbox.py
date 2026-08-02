from __future__ import annotations

import tempfile
from pathlib import Path

from fusion_code_modelization.sandbox import (
    SandboxAudit,
    SandboxGuard,
    SandboxPolicy,
    SecurityMode,
)


class TestSandboxPolicy:
    def test_readonly_blocks_write(self):
        p = SandboxPolicy(mode=SecurityMode.READONLY)
        ok, reason = p.is_write_allowed("/tmp/test.py")
        assert not ok
        assert "readonly" in reason

    def test_manual_allows_write_in_allowed_dir(self):
        p = SandboxPolicy(mode=SecurityMode.MANUAL, allowed_dirs=["/tmp"])
        ok, _ = p.is_write_allowed("/tmp/test.py")
        assert ok

    def test_manual_blocks_write_outside_allowed(self):
        p = SandboxPolicy(mode=SecurityMode.MANUAL, allowed_dirs=["/tmp"])
        ok, reason = p.is_write_allowed("/etc/passwd")
        assert not ok
        assert "outside" in reason

    def test_auto_allows_write(self):
        p = SandboxPolicy(mode=SecurityMode.AUTO)
        ok, _ = p.is_write_allowed("/tmp/test.py")
        assert ok

    def test_blocks_sensitive_file(self):
        p = SandboxPolicy()
        ok, reason = p.is_path_allowed("/project/.env")
        assert not ok
        assert "sensitive" in reason

    def test_blocks_dangerous_command(self):
        p = SandboxPolicy()
        ok, reason = p.is_command_allowed("rm -rf /")
        assert not ok
        assert "denied" in reason

    def test_allows_safe_command(self):
        p = SandboxPolicy()
        ok, _ = p.is_command_allowed("ls -la")
        assert ok

    def test_readonly_blocks_write_command(self):
        p = SandboxPolicy(mode=SecurityMode.READONLY)
        ok, reason = p.is_command_allowed("touch file.txt")
        assert not ok

    def test_ignored_path_blocked(self):
        p = SandboxPolicy()
        ok, reason = p.is_path_allowed("/project/.git/config")
        assert not ok
        assert "ignore" in reason

    def test_denied_file_blocked(self):
        p = SandboxPolicy(denied_files=["/secret/data.json"])
        ok, reason = p.is_path_allowed("/secret/data.json")
        assert not ok

    def test_to_dict(self):
        p = SandboxPolicy(mode=SecurityMode.MANUAL)
        d = p.to_dict()
        assert d["mode"] == "manual"
        assert "allowed_dirs" in d


class TestSandboxAudit:
    def test_log_and_get(self):
        audit = SandboxAudit()
        audit.log("read", "/tmp/a.py", True)
        audit.log("write", "/etc/passwd", False, "outside allowed")
        entries = audit.get_log()
        assert len(entries) == 2
        assert entries[0]["action"] == "read"
        assert entries[1]["allowed"] is False

    def test_count(self):
        audit = SandboxAudit()
        audit.log("read", "f1", True)
        audit.log("write", "f2", False, "blocked")
        assert audit.count() == 2
        assert audit.count_blocked() == 1

    def test_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = SandboxAudit()
            audit.log("read", "f1", True)
            out = str(Path(tmpdir) / "audit.json")
            result = audit.export(out)
            assert Path(out).exists()
            assert "read" in result

    def test_persist_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.log"
            audit = SandboxAudit(persist_path=str(path))
            audit.log("read", "f1", True)
            assert path.exists()
            content = path.read_text()
            assert "read" in content


class TestSandboxGuard:
    def test_check_read_allowed(self):
        guard = SandboxGuard(policy=SandboxPolicy(mode=SecurityMode.AUTO))
        ok, _ = guard.check_read("/tmp/test.py")
        assert ok

    def test_check_read_blocked_sensitive(self):
        guard = SandboxGuard(policy=SandboxPolicy())
        ok, _ = guard.check_read("/project/.env")
        assert not ok

    def test_check_write_readonly(self):
        guard = SandboxGuard(policy=SandboxPolicy(mode=SecurityMode.READONLY))
        ok, reason = guard.check_write("/tmp/test.py")
        assert not ok
        assert "readonly" in reason

    def test_check_command_blocked(self):
        guard = SandboxGuard(policy=SandboxPolicy())
        ok, _ = guard.check_command("rm -rf /")
        assert not ok

    def test_check_delete_readonly(self):
        guard = SandboxGuard(policy=SandboxPolicy(mode=SecurityMode.READONLY))
        ok, _ = guard.check_delete("/tmp/test.py")
        assert not ok

    def test_check_delete_manual_needs_approval(self):
        guard = SandboxGuard(policy=SandboxPolicy(mode=SecurityMode.MANUAL))
        ok, reason = guard.check_delete("/tmp/test.py")
        assert not ok
        assert "approval" in reason

    def test_check_delete_auto(self):
        guard = SandboxGuard(policy=SandboxPolicy(mode=SecurityMode.AUTO))
        ok, _ = guard.check_delete("/tmp/test.py")
        assert ok

    def test_audit_log_populated(self):
        guard = SandboxGuard()
        guard.check_read("/tmp/a.py")
        guard.check_write("/etc/passwd")
        log = guard.get_audit_log()
        assert len(log) == 2

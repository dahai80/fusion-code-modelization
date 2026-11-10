from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.recon import ParityChecker, ReconEngine
from fusion_code_modelization.recon.mcp_client import (
    STDIO_ALLOW_ENV,
    ReconUnavailableError,
    stdio_allowed,
)


def _mcp_result(tool: str, text: str, is_error: bool = False):
    return {"tool": tool, "text": text, "content": [{"type": "text", "text": text}], "isError": is_error}


@pytest.fixture(autouse=True)
def _no_spawn(monkeypatch):
    monkeypatch.delenv(STDIO_ALLOW_ENV, raising=False)


def test_stdio_allowed_fail_closed_without_env():
    assert stdio_allowed("npx") is False


def test_stdio_allowed_exact_basename_match(monkeypatch):
    monkeypatch.setenv(STDIO_ALLOW_ENV, "npx, node")
    assert stdio_allowed("npx") is True
    assert stdio_allowed("/usr/local/bin/npx") is True
    assert stdio_allowed("curl") is False


async def test_engine_skips_when_allowlist_empty(tmp_path):
    engine = ReconEngine(data_dir=str(tmp_path))
    result = await engine.run("/targets/legacy.bin")
    assert result["status"] == "skipped"
    assert "allowlist" in result["reason"]
    assert not list(tmp_path.rglob("manifest.json"))


async def test_engine_completed_writes_versioned_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv(STDIO_ALLOW_ENV, "npx")
    calls = AsyncMock(
        return_value=[
            _mcp_result("binary_overview", "overview evidence"),
            _mcp_result("get_call_graph", "callgraph evidence"),
        ]
    )
    with patch("fusion_code_modelization.recon.engine.mcp_tool_calls", calls):
        engine = ReconEngine(data_dir=str(tmp_path))
        result = await engine.run("/targets/legacy.bin")
    assert result["status"] == "completed"
    assert result["findings"][0]["evidence"] == "overview evidence"
    assert "Recon evidence" in result["context_section"]
    sent_calls = calls.call_args.args[2]
    assert sent_calls[0] == {"tool": "open_binary", "arguments": {"path": "/targets/legacy.bin"}}
    artifact = tmp_path / "recon" / result["run_id"] / "manifest.json"
    assert artifact.exists()
    manifest = json.loads(artifact.read_text())
    assert manifest["artifact_version"] == 1
    assert manifest["target"] == "/targets/legacy.bin"
    assert manifest["findings"][1]["tool"] == "get_call_graph"


async def test_engine_degrades_on_mcp_failure(tmp_path):
    with patch(
        "fusion_code_modelization.recon.engine.mcp_tool_calls",
        AsyncMock(side_effect=ReconUnavailableError("spawn failed")),
    ):
        engine = ReconEngine(data_dir=str(tmp_path))
        result = await engine.run("/targets/legacy.bin")
    assert result["status"] == "skipped"
    assert "spawn failed" in result["reason"]
    assert not list(tmp_path.rglob("manifest.json"))


async def test_parity_skips_without_probes(tmp_path):
    checker = ParityChecker(data_dir=str(tmp_path))
    result = await checker.check("/legacy", "/modernized")
    assert result["status"] == "skipped"
    assert "no parity probes" in result["reason"]


async def test_parity_match_cites_probe_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv(STDIO_ALLOW_ENV, "npx")
    evidence = "trace_feature: wrote output file /tmp/x, exit 0"
    side = [
        _mcp_result("open_binary", "mounted"),
        _mcp_result("trace_feature", evidence),
        _mcp_result("trace_call_path", "path a->b"),
    ]
    probes = [{"tool": "trace_feature", "arguments": {"query": "login"}}]
    with patch(
        "fusion_code_modelization.recon.parity.mcp_tool_calls",
        AsyncMock(return_value=side),
    ):
        checker = ParityChecker(data_dir=str(tmp_path))
        result = await checker.check("/legacy", "/modernized", probes=probes)
    assert result["status"] == "completed"
    assert result["verdict"] == "match"
    assert result["comparison"][0]["legacy_evidence"] == evidence
    report = json.loads((tmp_path / "recon" / result["report_id"] / "manifest.json").read_text())
    assert report["verdict"] == "match"
    assert report["total_probes"] == 2


async def test_parity_reports_divergence(tmp_path, monkeypatch):
    monkeypatch.setenv(STDIO_ALLOW_ENV, "npx")
    mount = _mcp_result("open_binary", "mounted")
    sides = [
        [mount, _mcp_result("trace_feature", "legacy wrote /tmp/a")],
        [mount, _mcp_result("trace_feature", "modernized wrote /tmp/b")],
    ]
    probes = [{"tool": "trace_feature", "arguments": {"query": "login"}}]

    async def _varying(command, args, calls, timeout=120.0):
        return sides.pop(0)

    with patch("fusion_code_modelization.recon.parity.mcp_tool_calls", _varying):
        checker = ParityChecker(data_dir=str(tmp_path))
        result = await checker.check("/legacy", "/modernized", probes=probes)
    assert result["verdict"] == "divergence"
    assert result["matched_probes"] == 0


async def test_parity_skips_when_mount_fails(tmp_path, monkeypatch):
    monkeypatch.setenv(STDIO_ALLOW_ENV, "npx")
    with patch(
        "fusion_code_modelization.recon.parity.mcp_tool_calls",
        AsyncMock(return_value=[_mcp_result("open_binary", "no such file", is_error=True)]),
    ):
        checker = ParityChecker(data_dir=str(tmp_path))
        result = await checker.check(
            "/legacy", "/modernized", probes=[{"tool": "trace_feature", "arguments": {"query": "x"}}]
        )
    assert result["status"] == "skipped"
    assert "mount failed" in result["reason"]


async def test_parity_skips_when_one_side_unavailable(tmp_path):
    with patch(
        "fusion_code_modelization.recon.parity.mcp_tool_calls",
        AsyncMock(side_effect=ReconUnavailableError("server died")),
    ):
        checker = ParityChecker(data_dir=str(tmp_path))
        result = await checker.check(
            "/legacy", "/modernized", probes=[{"tool": "trace_feature", "arguments": {"query": "x"}}]
        )
    assert result["status"] == "skipped"
    assert "server died" in result["reason"]

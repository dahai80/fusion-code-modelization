# ReconEngine (issue #37): runs a REA MCP tool plan against a customer-owned
# target and writes versioned evidence artifacts consumable by the coder
# toolset. Every failure degrades to status="skipped" — the pipeline continues
# without recon; nothing here ever raises outward.

import logging
import os
import time
from typing import Any

from ..core.safe_writer import SafeWriter
from .mcp_client import mcp_tool_calls, stdio_allowlist

logger = logging.getLogger(__name__)

# Default tool plan against a newly mounted target. REA keeps per-finding
# evidence attached to every tool result, so each call below produces an
# auditable evidence block. The engine injects open_binary (target mount) in
# front of the plan at run time and fills export_evidence_bundle's path from
# the artifact directory; callers override per-tool arguments when needed.
# Tool names verified against `rea-agents` 6.7.0 tools/list (207 tools).
DEFAULT_RECON_PLAN: list[dict[str, Any]] = [
    {"tool": "inspect_macho", "arguments": {}},
    {"tool": "batch_decompile", "arguments": {}},
    {"tool": "export_evidence_bundle", "arguments": {}},
]


class ReconEngine:
    def __init__(
        self,
        data_dir: str | None = None,
        command: str = "npx",
        args: list[str] | None = None,
        timeout: float = 120.0,
    ):
        self._data_dir = data_dir or os.path.expanduser("~/.fusion/code_mod")
        self._command = command
        self._args = list(args) if args is not None else ["-y", "rea-agents", "mcp"]
        self._timeout = timeout

    async def run(self, target: str, plan: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        plan = plan or DEFAULT_RECON_PLAN
        run_id = time.strftime("recon-%Y%m%d-%H%M%S")
        effective = [dict(call) for call in plan]
        effective.insert(0, {"tool": "open_binary", "arguments": {"path": os.path.abspath(target)}})
        run_dir = os.path.join(os.path.abspath(self._data_dir), "recon", run_id)
        for call in effective:
            if call["tool"] == "export_evidence_bundle" and not call.get("arguments"):
                call["arguments"] = {
                    "path": os.path.join(run_dir, "evidence-bundle.json"),
                    "overwrite": True,
                }
        # export_evidence_bundle requires the output directory to already exist
        os.makedirs(run_dir, exist_ok=True)
        logger.info(
            "recon: start target=%s run_id=%s plan=%s command=%s",
            target,
            run_id,
            [c.get("tool") for c in plan],
            self._command,
        )
        try:
            results = await mcp_tool_calls(self._command, self._args, effective, timeout=self._timeout)
        except Exception as exc:
            logger.warning("recon: MCP unavailable — degrade to no-recon (target=%s): %s", target, exc)
            return {"status": "skipped", "reason": f"REA MCP unavailable: {exc}", "run_id": run_id, "target": target}

        findings = []
        for item in results:
            findings.append(
                {
                    "tool": item["tool"],
                    "isError": item["isError"],
                    "evidence": item["text"],
                }
            )
        context_section = self._context_section(target, findings)
        manifest = {
            "artifact_version": 1,
            "run_id": run_id,
            "target": target,
            "command": self._command,
            "args": self._args,
            "allowlist": stdio_allowlist(),
            "tool_plan": [c.get("tool") for c in effective],
            "findings": findings,
            "context_section": context_section,
        }
        path = self._write_artifact(run_id, manifest)
        if path:
            manifest["artifact_path"] = path
        logger.info("recon: completed run_id=%s tools=%d artifact=%s", run_id, len(findings), path or "(not written)")
        return {
            "status": "completed",
            "run_id": run_id,
            "target": target,
            "findings": findings,
            "context_section": context_section,
            "artifact_path": path,
        }

    def _context_section(self, target: str, findings: list[dict[str, Any]]) -> str:
        # Injection-ready block for the coder toolset prompt: each finding keeps
        # its evidence verbatim so parity claims stay auditable downstream.
        lines = ["", f"## Recon evidence (target: {target}, captured via REA MCP)", ""]
        for item in findings:
            marker = "[error]" if item["isError"] else "[ok]"
            lines.append(f"### {item['tool']} {marker}")
            lines.append(item["evidence"])
            lines.append("")
        return "\n".join(lines)

    def _write_artifact(self, run_id: str, manifest: dict[str, Any]) -> str | None:
        try:
            writer = SafeWriter(self._data_dir)
            rel = os.path.join("recon", run_id, "manifest.json")
            writer.write_json(rel, manifest, indent=4)
            return os.path.join(self._data_dir, rel)
        except Exception as exc:
            logger.warning("recon: artifact write failed run_id=%s: %s", run_id, exc)
            return None

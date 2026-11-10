# ParityChecker (issue #37): compares modernized-build behavior against the
# legacy target using REA runtime probes, so a parity claim cites probe
# evidence instead of a bare source diff. Same degradation contract as
# ReconEngine: any MCP problem yields status="skipped" and the pipeline
# continues (parity stays unproven — reported loudly, never silently assumed).

import logging
import os
import time
from typing import Any

from .engine import ReconEngine
from .mcp_client import mcp_tool_calls

logger = logging.getLogger(__name__)


class ParityChecker:
    def __init__(
        self,
        data_dir: str | None = None,
        command: str = "npx",
        args: list[str] | None = None,
        timeout: float = 120.0,
    ):
        self._engine = ReconEngine(data_dir=data_dir, command=command, args=args, timeout=timeout)
        self._command = command
        self._args = list(args) if args is not None else ["-y", "rea-agents", "mcp"]
        self._timeout = timeout

    async def check(
        self,
        legacy_target: str,
        modernized_target: str,
        probes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        report_id = time.strftime("parity-%Y%m%d-%H%M%S")
        # Probes are domain-specific (trace_feature needs a query, trace_call_path
        # a start symbol) — never guess them. No probes = skip loudly.
        if not probes:
            reason = "no parity probes configured — pass probes with tool+arguments (e.g. trace_feature query)"
            logger.warning("parity: skipped — %s", reason)
            return {
                "status": "skipped",
                "reason": reason,
                "report_id": report_id,
                "legacy": {"status": "skipped", "reason": reason},
                "modernized": {"status": "skipped", "reason": reason},
            }
        logger.info("parity: start legacy=%s modernized=%s report_id=%s", legacy_target, modernized_target, report_id)
        legacy_side = await self._probe_side(legacy_target, probes, "legacy")
        modern_side = await self._probe_side(modernized_target, probes, "modernized")
        if legacy_side["status"] != "completed" or modern_side["status"] != "completed":
            reason = str(legacy_side.get("reason") or modern_side.get("reason") or "parity unavailable")
            logger.warning("parity: skipped — %s", reason)
            return {
                "status": "skipped",
                "reason": reason,
                "report_id": report_id,
                "legacy": legacy_side,
                "modernized": modern_side,
            }
        comparison = []
        matched = 0
        for lp, mp in zip(legacy_side["probes"], modern_side["probes"], strict=False):
            same = (not lp["isError"]) and (not mp["isError"]) and lp["evidence"].strip() == mp["evidence"].strip()
            matched += 1 if same else 0
            comparison.append(
                {
                    "probe": lp["tool"],
                    "match": same,
                    "legacy_evidence": lp["evidence"],
                    "modernized_evidence": mp["evidence"],
                }
            )
        verdict = "match" if matched == len(comparison) and comparison else "divergence"
        report = {
            "artifact_version": 1,
            "report_id": report_id,
            "legacy_target": legacy_target,
            "modernized_target": modernized_target,
            "verdict": verdict,
            "matched_probes": matched,
            "total_probes": len(comparison),
            "comparison": comparison,
        }
        path = self._engine._write_artifact(report_id, report)
        if path:
            report["artifact_path"] = path
        logger.info(
            "parity: verdict=%s matched=%d/%d artifact=%s", verdict, matched, len(comparison), path or "(not written)"
        )
        return {
            "status": "completed",
            "report_id": report_id,
            "verdict": verdict,
            "matched_probes": matched,
            "total_probes": len(comparison),
            "comparison": comparison,
            "artifact_path": path,
        }

    async def _probe_side(self, target: str, probes: list[dict[str, Any]], label: str) -> dict[str, Any]:
        # Mount the target first — REA probes run against the open session. A
        # failed mount makes this side unavailable (skip loudly, never guess).
        calls = [{"tool": "open_binary", "arguments": {"path": os.path.abspath(target)}}] + list(probes)
        try:
            results = await mcp_tool_calls(self._command, self._args, calls, timeout=self._timeout)
        except Exception as exc:
            logger.warning("parity: %s probes unavailable (target=%s): %s", label, target, exc)
            return {"status": "skipped", "reason": f"REA MCP unavailable: {exc}", "target": target}
        mount = results[0] if results else None
        if mount is None or mount["isError"]:
            reason = f"target mount failed ({label}): {mount['text'][:200] if mount else 'no results'}"
            logger.warning("parity: skipped — %s", reason)
            return {"status": "skipped", "reason": reason, "target": target}
        return {
            "status": "completed",
            "target": target,
            "probes": [
                {"tool": item["tool"], "isError": item["isError"], "evidence": item["text"]} for item in results[1:]
            ],
        }

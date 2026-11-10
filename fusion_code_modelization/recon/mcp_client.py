# stdio MCP client for the recon engine (issue #37).
#
# Newline-delimited JSON-RPC over a subprocess — same transport shape as the
# fusion-cowork desigma integration, re-owned here (cross-repo import of
# fusion_cowork is not allowed). Spawn is gated by FUSION_FCM_MCP_STDIO_ALLOW
# (comma/semicolon-separated binary basenames, exact match on basename);
# empty/unset allowlist = deny all (fail-closed), so the recon engine can never
# spawn a process the operator did not put on the allowlist.

import asyncio
import contextlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

STDIO_ALLOW_ENV = "FUSION_FCM_MCP_STDIO_ALLOW"
_MCP_PROTOCOL_VERSION = "2025-03-26"


class ReconUnavailableError(RuntimeError):
    pass


def stdio_allowlist() -> list[str]:
    raw = os.environ.get(STDIO_ALLOW_ENV, "")
    return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]


def stdio_allowed(command: str) -> bool:
    allowed = stdio_allowlist()
    if not allowed:
        return False
    return os.path.basename(str(command).strip()) in allowed


async def _request(
    proc: asyncio.subprocess.Process, req_id: int, payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    if proc.stdin is None or proc.stdout is None:
        raise ReconUnavailableError("MCP subprocess created without stdio pipes")
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    proc.stdin.write(line.encode("utf-8"))
    await proc.stdin.drain()
    deadline = asyncio.get_event_loop().time() + timeout
    # Skip blank/foreign stdout lines (npm notices, banners) until a JSON body
    # arrives — but never wait past the deadline and never spin unbounded.
    for _ in range(200):
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise ReconUnavailableError(f"stdio MCP server timed out after {timeout}s (req id={req_id})")
        try:
            raw = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
        except TimeoutError as exc:
            raise ReconUnavailableError(f"stdio MCP server timed out after {timeout}s (req id={req_id})") from exc
        if not raw:
            raise ReconUnavailableError(f"stdio MCP server closed stdout early (req id={req_id})")
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            logger.warning("stdio MCP non-JSON stdout line skipped (req id=%s): %r", req_id, raw[:80])
            continue
        break
    else:
        raise ReconUnavailableError(f"stdio MCP server sent 200+ non-JSON lines (req id={req_id})")
    if isinstance(body, dict) and "error" in body and body["error"]:
        raise ReconUnavailableError(f"stdio MCP error on req {req_id}: {body['error']}")
    return body if isinstance(body, dict) else {}


async def mcp_tool_calls(
    command: str,
    args: list[Any],
    calls: list[dict[str, Any]],
    timeout: float = 120.0,
) -> list[dict[str, Any]]:
    # Spawn the MCP stdio server, initialize handshake, run the tools/call
    # sequence, return [{"tool", "text", "content", "isError"}]. Always tears
    # the subprocess down; every protocol problem raises ReconUnavailableError.
    if not stdio_allowed(command):
        raise ReconUnavailableError(
            f"command {command!r} not in {STDIO_ALLOW_ENV} allowlist (current: {stdio_allowlist() or ['(empty — deny all)']})"
        )
    try:
        proc = await asyncio.create_subprocess_exec(
            command,
            *[str(a) for a in (args or [])],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            # DEVNULL: a chatty stderr must not fill the pipe and deadlock the server
            stderr=asyncio.subprocess.DEVNULL,
            # 16MB line limit: asyncio's 64KB default makes readline() raise
            # ValueError on large tool outputs (tools/list, batch_decompile)
            limit=2**24,
            # own process group: npx spawns a node child — killing the wrapper
            # alone leaves the child holding the pipes and proc.wait() hanging
            start_new_session=True,
        )
    except OSError as exc:
        raise ReconUnavailableError(f"failed to spawn MCP server {command!r}: {exc}") from exc
    if proc.stdin is None or proc.stdout is None:
        raise ReconUnavailableError("MCP subprocess created without stdio pipes")
    results: list[dict[str, Any]] = []
    try:
        await _request(
            proc,
            1,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": _MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "fusion-code-modelization-recon", "version": "1.0"},
                },
            },
            timeout,
        )
        # notifications carry no id and get no response — write only, never wait
        proc.stdin.write(
            (json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n").encode("utf-8")
        )
        await proc.stdin.drain()
        for idx, call in enumerate(calls, start=3):
            body = await _request(
                proc,
                idx,
                {
                    "jsonrpc": "2.0",
                    "id": idx,
                    "method": "tools/call",
                    "params": {"name": call.get("tool", ""), "arguments": call.get("arguments") or {}},
                },
                timeout,
            )
            result = body.get("result") or {}
            content = result.get("content") or []
            text = "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
            results.append(
                {"tool": call.get("tool", ""), "text": text, "content": content, "isError": bool(result.get("isError"))}
            )
    finally:
        await _kill_group(proc)
    return results


async def _kill_group(proc: asyncio.subprocess.Process) -> None:
    # Kill the whole process group (wrapper + node child), then reap with a
    # bounded wait — an orphaned child can hold the stdout pipe open forever.
    import signal

    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except TimeoutError:
        logger.warning("MCP subprocess %d did not reap after SIGKILL", proc.pid)

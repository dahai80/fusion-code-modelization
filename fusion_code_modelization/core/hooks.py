# GateGuard: New file. Importers: core/agent_loop.py, pipeline/, server/app.py, cli/__init__.py, tests/test_hooks.py. Affected API: HookEvent, HookDecision, HookRegistry, builtin guards. Data schemas: none. User instruction: M2 — Hook deterministic interception layer, guard-backed with regex fallback.

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

_DANGEROUS_CMD_RE = re.compile(
    r"(?:rm\s+-rf\s+/(?:\s|$)|rm\s+-rf\s+~|:\s*\(\)\s*\{\s*:\s*\|\s*:&\s*\}\s*;|mkfs\b|dd\s+.*of=/dev/|>\s*/etc/|curl\s+.*\|\s*sh|wget\s+.*\|\s*sh)",
    re.IGNORECASE,
)
_SECRET_RE = re.compile(
    r"(?:AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)",
)
_PATH_TRAVERSAL_RE = re.compile(r"(?:\.\./){2,}|/etc/|/var/log/|/root/")


class HookEvent(StrEnum):
    PRE_WRITE = "pre_write"
    POST_LLM = "post_llm"
    PRE_EXEC = "pre_exec"
    POST_EXEC = "post_exec"


class HookAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    MODIFY = "modify"


@dataclass
class HookDecision:
    action: HookAction = HookAction.ALLOW
    reason: str = ""
    modified_content: str | None = None

    @property
    def allowed(self) -> bool:
        return self.action != HookAction.DENY


@dataclass
class HookHandler:
    name: str
    event: HookEvent
    execute: Any  # Callable[[dict], Awaitable[HookDecision] | HookDecision]
    description: str = ""


@dataclass
class HookRegistry:
    handlers: dict[HookEvent, list[HookHandler]] = field(default_factory=dict)
    enabled: bool = True

    def register(self, handler: HookHandler) -> None:
        self.handlers.setdefault(handler.event, []).append(handler)
        logger.debug("hook registered: %s on %s", handler.name, handler.event.value)

    async def emit(self, event: HookEvent, payload: dict[str, Any]) -> HookDecision:
        if not self.enabled:
            return HookDecision(action=HookAction.ALLOW, reason="hooks_disabled")
        final_modify: HookDecision | None = None
        for handler in self.handlers.get(event, []):
            try:
                decision = handler.execute(payload)
                if hasattr(decision, "__await__"):
                    decision = await decision
            except Exception as e:
                logger.error("hook %s raised: %s", handler.name, e)
                return HookDecision(action=HookAction.DENY, reason=f"hook_exception:{handler.name}:{e}")
            if decision.action == HookAction.DENY:
                logger.warning("hook %s denied %s: %s", handler.name, event.value, decision.reason)
                return decision
            if decision.action == HookAction.MODIFY and decision.modified_content is not None:
                payload = {**payload, "content": decision.modified_content}
                final_modify = decision
        if final_modify is not None:
            return final_modify
        return HookDecision(action=HookAction.ALLOW)


def path_guard(payload: dict[str, Any]) -> HookDecision:
    target = str(payload.get("path", ""))
    if not target:
        return HookDecision(action=HookAction.ALLOW, reason="no_path")
    if _PATH_TRAVERSAL_RE.search(target):
        return HookDecision(action=HookAction.DENY, reason=f"path_guard:blocked_path:{target}")
    return HookDecision(action=HookAction.ALLOW)


def dangerous_cmd_guard(payload: dict[str, Any]) -> HookDecision:
    cmd = str(payload.get("command", payload.get("content", "")))
    if _DANGEROUS_CMD_RE.search(cmd):
        return HookDecision(action=HookAction.DENY, reason="dangerous_cmd_guard:destructive_command")
    return HookDecision(action=HookAction.ALLOW)


def secret_scrub(payload: dict[str, Any]) -> HookDecision:
    content = str(payload.get("content", ""))
    if not content:
        return HookDecision(action=HookAction.ALLOW, reason="no_content")
    scrubbed, count = _SECRET_RE.subn("[REDACTED:SECRET]", content)
    if count:
        logger.info("secret_scrub redacted %d secret(s)", count)
        return HookDecision(action=HookAction.MODIFY, reason=f"secret_scrub:{count}_secrets", modified_content=scrubbed)
    return HookDecision(action=HookAction.ALLOW)


def audit_log(payload: dict[str, Any]) -> HookDecision:
    logger.info(
        "audit_hook event=%s action=%s target=%s",
        payload.get("event", "?"),
        payload.get("action", "?"),
        str(payload.get("path", payload.get("command", "")))[:120],
    )
    return HookDecision(action=HookAction.ALLOW)


class GuardBridge:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._client = None
        self._unavailable_logged = False

    def _get_client(self):
        if not self.enabled:
            return None
        if self._client is None:
            try:
                from fusion_core.guard_client import FusionGuardClient

                self._client = FusionGuardClient()
            except Exception as e:
                if not self._unavailable_logged:
                    logger.warning("fusion-guard unavailable, falling back to builtin regex guards: %s", e)
                    self._unavailable_logged = True
                self._client = None
        return self._client

    async def evaluate(self, content: str, category_hint: str | None = None) -> HookDecision:
        client = self._get_client()
        if client is None:
            return HookDecision(action=HookAction.ALLOW, reason="guard_unavailable_fallback_regex")
        try:
            verdict = client.evaluate(content, category_hint=category_hint)
            if verdict.action == "block":
                return HookDecision(action=HookAction.DENY, reason=f"guard:block:{verdict.reason}")
            if verdict.redacted_content:
                return HookDecision(
                    action=HookAction.MODIFY, reason="guard:redact", modified_content=verdict.redacted_content
                )
            return HookDecision(action=HookAction.ALLOW, reason="guard:allow")
        except Exception as e:
            logger.warning("guard.evaluate failed, fallback to regex: %s", e)
            return HookDecision(action=HookAction.ALLOW, reason=f"guard_error_fallback_regex:{e}")


def default_registry(guard_enabled: bool = True) -> HookRegistry:
    registry = HookRegistry(enabled=True)
    registry.register(HookHandler("path_guard", HookEvent.PRE_WRITE, path_guard, "block path traversal / system dirs"))
    registry.register(
        HookHandler("dangerous_cmd_guard", HookEvent.PRE_EXEC, dangerous_cmd_guard, "block destructive shell commands")
    )
    registry.register(
        HookHandler("secret_scrub", HookEvent.POST_LLM, secret_scrub, "redact leaked secrets in LLM output")
    )
    registry.register(HookHandler("audit_log", HookEvent.POST_EXEC, audit_log, "record executed actions"))
    bridge = GuardBridge(enabled=guard_enabled)
    registry.register(
        HookHandler("guard_evaluate", HookEvent.POST_LLM, bridge.evaluate, "fusion-guard content verdict")
    )
    registry.register(
        HookHandler("guard_evaluate_write", HookEvent.PRE_WRITE, bridge.evaluate, "fusion-guard write verdict")
    )
    return registry

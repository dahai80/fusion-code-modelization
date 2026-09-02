# GateGuard: New file. Importers: core/agent_loop.py, pipeline/, server/app.py, cli/__init__.py, tests/test_hooks.py. Affected API: HookEvent, HookDecision, HookRegistry, builtin guards. Data schemas: none. User instruction: M2 — Hook deterministic interception layer, guard-backed with regex fallback.

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

_DANGEROUS_CMD_RE = re.compile(
    r"(?:"
    r"rm\s+-rf?\s+(?:/(?:\s|$)|~|\$HOME|/home|/root|/etc|/var|/usr)"  # rm -rf destructive targets
    r"|:\s*\(\)\s*\{\s*:\s*\|\s*:&\s*\}\s*;"  # fork bomb
    r"|mkfs\b"
    r"|dd\s+.*of=/dev/"
    r"|>\s*/dev/(?:sd|nvme|disk)"
    r"|>\s*/etc/"
    r"|chmod\s+-R\b"
    r"|chown\s+-R\b.*\s/"
    r"|shutdown\b|reboot\b|halt\b|poweroff\b"
    r"|curl\s+.*\|\s*(?:sh|bash)\b"
    r"|wget\s+.*\|\s*(?:sh|bash)\b"
    r"|bash\s+-c\b.*(?:rm|mkfs|dd|>|shutdown)"
    r"|find\s+/\s+.*-delete\b"
    r")",
    re.IGNORECASE,
)
_SECRET_RE = re.compile(
    r"(?:"
    r"AKIA[0-9A-Z]{16}"  # AWS access key id
    r"|sk-[a-zA-Z0-9]{20,}"  # OpenAI-style
    r"|ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}"  # GitHub classic + fine-grained
    r"|glpat-[a-zA-Z0-9_\-]{20}"  # GitLab
    r"|xox[baprs]-[a-zA-Z0-9\-]{10,}"  # Slack
    r"|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"  # PEM blocks
    r"|AIza[0-9A-Za-z_\-]{35}"  # Google API key
    r")",
)
_REDACTED = "[REDACTED:SECRET]"


def scrub_secrets(text: str) -> str:
    if not text:
        return text
    scrubbed, count = _SECRET_RE.subn(_REDACTED, text)
    if count:
        logger.info("scrub_secrets redacted %d secret(s)", count)
    return scrubbed


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
    scrubbed, count = _SECRET_RE.subn(_REDACTED, content)
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
            action = getattr(verdict, "action", None)
            if action == "block":
                return HookDecision(action=HookAction.DENY, reason=f"guard:block:{verdict.reason}")
            if action == "redact":
                redacted = getattr(verdict, "redacted_content", None)
                if redacted is None:
                    logger.warning("guard redact verdict without redacted_content, fail-closed DENY")
                    return HookDecision(action=HookAction.DENY, reason="guard:redact_missing_content")
                return HookDecision(action=HookAction.MODIFY, reason="guard:redact", modified_content=redacted)
            if action == "allow":
                return HookDecision(action=HookAction.ALLOW, reason="guard:allow")
            logger.warning("guard returned unknown action %r, fail-closed DENY", action)
            return HookDecision(action=HookAction.DENY, reason=f"guard:unknown_action:{action}")
        except Exception as e:
            logger.warning("guard.evaluate failed, fail-closed DENY: %s", e)
            return HookDecision(action=HookAction.DENY, reason=f"guard_error_fail_closed:{e}")


def default_registry(guard_enabled: bool = True) -> HookRegistry:
    registry = HookRegistry(enabled=True)
    registry.register(HookHandler("path_guard", HookEvent.PRE_WRITE, path_guard, "block path traversal / system dirs"))
    registry.register(
        HookHandler("dangerous_cmd_guard", HookEvent.PRE_EXEC, dangerous_cmd_guard, "block destructive shell commands")
    )
    registry.register(
        HookHandler("secret_scrub", HookEvent.POST_LLM, secret_scrub, "redact leaked secrets in LLM output")
    )
    registry.register(
        HookHandler("secret_scrub_write", HookEvent.PRE_WRITE, secret_scrub, "redact secrets before disk persistence")
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

# GateGuard: New file. Importers: pipeline/integrator.py, snapshot/manager.py, session/store.py, audit/store.py, cli/__init__.py. Affected API: SafeWriter. Data schemas: none. User instruction: S-C1/S-C2 — unify write sites, emit PRE_WRITE, enforce resolved-path containment.

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any, cast

from .hooks import HookAction, HookDecision, HookEvent, HookRegistry

logger = logging.getLogger(__name__)


class UnsafePathError(PermissionError):
    pass


class SafeWriter:
    def __init__(self, project_root: str | Path, registry: HookRegistry | None = None, strict: bool = True) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.registry = registry
        self.strict = strict
        logger.debug("SafeWriter init: project_root=%s strict=%s", self.project_root, strict)

    def resolve_within(self, path: str | Path) -> Path:
        target = Path(path)
        if not target.is_absolute():
            target = self.project_root / target
        resolved = target.expanduser().resolve()
        if not self.strict:
            return resolved
        try:
            resolved.relative_to(self.project_root)
        except ValueError as ve:
            logger.error("path escapes project_root: %s (resolved=%s, root=%s)", path, resolved, self.project_root)
            raise UnsafePathError(f"path escapes project_root: {path} -> {resolved}") from ve
        return resolved

    def _emit(self, action: str, rel_path: str, content: str | None = None) -> HookDecision:
        if self.registry is None or not self.registry.enabled:
            return HookDecision(action=HookAction.ALLOW, reason="no_registry")
        payload: dict[str, Any] = {"event": HookEvent.PRE_WRITE.value, "action": action, "path": rel_path}
        if content is not None:
            payload["content"] = content
        final_modify: HookDecision | None = None
        for handler in self.registry.handlers.get(HookEvent.PRE_WRITE, []):
            try:
                decision = handler.execute(payload)
                if inspect.isawaitable(decision):
                    logger.debug("skipping async PRE_WRITE handler in sync path: %s", handler.name)
                    cast("Any", decision).close()
                    continue
            except Exception as e:
                logger.error("hook %s raised: %s", handler.name, e)
                raise UnsafePathError(f"hook_exception:{handler.name}:{e}") from e
            if decision.action == HookAction.DENY:
                logger.warning("PRE_WRITE denied %s %s: %s", action, rel_path, decision.reason)
                raise UnsafePathError(f"hook denied {action} {rel_path}: {decision.reason}")
            if decision.action == HookAction.MODIFY and decision.modified_content is not None:
                payload = {**payload, "content": decision.modified_content}
                final_modify = decision
        if final_modify is not None:
            return final_modify
        return HookDecision(action=HookAction.ALLOW)

    def _apply_modify(self, decision: HookDecision, content: str) -> str:
        if decision.action == HookAction.MODIFY and decision.modified_content is not None:
            return decision.modified_content
        return content

    def _rel(self, resolved: Path) -> str:
        try:
            return str(resolved.relative_to(self.project_root))
        except ValueError:
            return str(resolved)

    def _path_str(self, path: str | Path) -> str:
        return str(path)

    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> Path:
        resolved = self.resolve_within(path)
        rel = self._rel(resolved)
        decision = self._emit("write", rel, content)
        final_content = self._apply_modify(decision, content)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(final_content, encoding=encoding)
        logger.info("SafeWriter wrote %d bytes to %s", len(final_content), rel)
        return resolved

    def write_bytes(self, path: str | Path, data: bytes) -> Path:
        resolved = self.resolve_within(path)
        rel = self._rel(resolved)
        self._emit("write", rel)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_bytes(data)
        logger.info("SafeWriter wrote %d bytes to %s", len(data), rel)
        return resolved

    def write_json(self, path: str | Path, obj: Any, indent: int = 2, ensure_ascii: bool = False) -> Path:
        import json

        return self.write_text(path, json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii))

    def unlink(self, path: str | Path) -> bool:
        resolved = self.resolve_within(path)
        rel = self._rel(resolved)
        self._emit("delete", rel)
        if resolved.exists():
            resolved.unlink()
            logger.info("SafeWriter deleted %s", rel)
            return True
        logger.debug("SafeWriter delete noop (missing): %s", rel)
        return False

    def mkdir(self, path: str | Path, parents: bool = True, exist_ok: bool = True) -> Path:
        resolved = self.resolve_within(path)
        rel = self._rel(resolved)
        self._emit("mkdir", rel)
        resolved.mkdir(parents=parents, exist_ok=exist_ok)
        return resolved

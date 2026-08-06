# core/progress.py — lightweight progress callback protocol for long-running operations
# Fact: new file. Callers: SessionEngine.chat(), WorkflowExecutor.run_workflow(), BoundaryDetector.detect_boundaries_llm().
# No existing file serves this purpose (no callback/event patterns found in codebase).
# No data files read/written. User instruction: "启动下一个阶段的实施"

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    event_type: str
    operation: str
    detail: str = ""
    percent: float | None = None
    metadata: dict = field(default_factory=dict)

    VALID_TYPES = frozenset({"start", "progress", "complete", "error"})

    def __post_init__(self):
        if self.event_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid event_type '{self.event_type}', must be one of {sorted(self.VALID_TYPES)}")


class ProgressCallback(Protocol):
    def __call__(self, event: ProgressEvent) -> None: ...


class LoggingProgressCallback:
    def __call__(self, event: ProgressEvent) -> None:
        pct = f" ({event.percent:.0f}%)" if event.percent is not None else ""
        logger.info("[%s] %s%s: %s", event.event_type, event.operation, pct, event.detail)


class CompositeProgressCallback:
    def __init__(self, *callbacks: Callable[[ProgressEvent], None]):
        self._callbacks = list(callbacks)

    def add(self, callback: Callable[[ProgressEvent], None]) -> None:
        self._callbacks.append(callback)

    def __call__(self, event: ProgressEvent) -> None:
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as exc:
                logger.warning("progress callback error: %s", exc)


def emit_start(operation: str, detail: str = "", callback: Callable[[ProgressEvent], None] | None = None) -> None:
    if callback:
        callback(ProgressEvent(event_type="start", operation=operation, detail=detail))


def emit_progress(
    operation: str,
    detail: str = "",
    percent: float | None = None,
    callback: Callable[[ProgressEvent], None] | None = None,
) -> None:
    if callback:
        callback(ProgressEvent(event_type="progress", operation=operation, detail=detail, percent=percent))


def emit_complete(operation: str, detail: str = "", callback: Callable[[ProgressEvent], None] | None = None) -> None:
    if callback:
        callback(ProgressEvent(event_type="complete", operation=operation, detail=detail, percent=100.0))


def emit_error(operation: str, detail: str = "", callback: Callable[[ProgressEvent], None] | None = None) -> None:
    if callback:
        callback(ProgressEvent(event_type="error", operation=operation, detail=detail))

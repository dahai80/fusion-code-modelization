# GateGuard: New file. Importers: none (test file). Affected API: none. Data schemas: none. User instruction: Phase 6 — test progress callback system.

from __future__ import annotations

import logging

import pytest

from fusion_code_modelization.core.progress import (
    CompositeProgressCallback,
    LoggingProgressCallback,
    ProgressEvent,
    emit_complete,
    emit_error,
    emit_progress,
    emit_start,
)


class TestProgressEvent:
    def test_valid_event_types(self):
        for etype in ("start", "progress", "complete", "error"):
            evt = ProgressEvent(event_type=etype, operation="op")
            assert evt.event_type == etype

    def test_invalid_event_type_raises(self):
        with pytest.raises(ValueError, match="Invalid event_type"):
            ProgressEvent(event_type="unknown", operation="op")

    def test_defaults(self):
        evt = ProgressEvent(event_type="start", operation="test")
        assert evt.detail == ""
        assert evt.percent is None
        assert evt.metadata == {}

    def test_custom_fields(self):
        evt = ProgressEvent(
            event_type="progress",
            operation="scan",
            detail="scanning",
            percent=42.5,
            metadata={"key": "val"},
        )
        assert evt.percent == 42.5
        assert evt.metadata["key"] == "val"

    def test_valid_types_frozen(self):
        assert "start" in ProgressEvent.VALID_TYPES
        assert len(ProgressEvent.VALID_TYPES) == 4


class TestEmitHelpers:
    def test_emit_start_no_callback(self):
        emit_start("op", "detail", None)

    def test_emit_progress_no_callback(self):
        emit_progress("op", "detail", 50.0, None)

    def test_emit_complete_no_callback(self):
        emit_complete("op", "detail", None)

    def test_emit_error_no_callback(self):
        emit_error("op", "detail", None)

    def test_emit_start_with_callback(self):
        events = []
        emit_start("op1", "starting", events.append)
        assert len(events) == 1
        assert events[0].event_type == "start"
        assert events[0].operation == "op1"
        assert events[0].detail == "starting"

    def test_emit_progress_with_callback(self):
        events = []
        emit_progress("op2", "midway", 55.0, events.append)
        assert events[0].event_type == "progress"
        assert events[0].percent == 55.0

    def test_emit_complete_with_callback(self):
        events = []
        emit_complete("op3", "done", events.append)
        assert events[0].event_type == "complete"
        assert events[0].percent == 100.0

    def test_emit_error_with_callback(self):
        events = []
        emit_error("op4", "boom", events.append)
        assert events[0].event_type == "error"
        assert events[0].detail == "boom"


class TestLoggingProgressCallback:
    def test_logs_event(self, caplog):
        cb = LoggingProgressCallback()
        evt = ProgressEvent(event_type="progress", operation="scan", detail="files", percent=30)
        with caplog.at_level(logging.INFO, logger="fusion_code_modelization.core.progress"):
            cb(evt)
        assert "scan" in caplog.text
        assert "30%" in caplog.text

    def test_logs_no_percent(self, caplog):
        cb = LoggingProgressCallback()
        evt = ProgressEvent(event_type="start", operation="init", detail="begin")
        with caplog.at_level(logging.INFO, logger="fusion_code_modelization.core.progress"):
            cb(evt)
        assert "init" in caplog.text
        assert "%" not in caplog.text


class TestCompositeProgressCallback:
    def test_calls_all_callbacks(self):
        a, b = [], []
        composite = CompositeProgressCallback(a.append, b.append)
        evt = ProgressEvent(event_type="complete", operation="done")
        composite(evt)
        assert len(a) == 1
        assert len(b) == 1
        assert a[0] is evt

    def test_add_callback(self):
        a = []
        composite = CompositeProgressCallback()
        composite.add(a.append)
        evt = ProgressEvent(event_type="start", operation="go")
        composite(evt)
        assert len(a) == 1

    def test_exception_in_callback_does_not_stop_others(self):
        a = []
        def bad_cb(event):
            raise RuntimeError("oops")
        composite = CompositeProgressCallback(bad_cb, a.append)
        evt = ProgressEvent(event_type="error", operation="fail")
        composite(evt)
        assert len(a) == 1

    def test_empty_composite_noop(self):
        composite = CompositeProgressCallback()
        evt = ProgressEvent(event_type="start", operation="go")
        composite(evt)

# tests/unit/core/test_logging.py
"""Tests for ContextFilter logging."""

import logging

import pytest

from titan_chordpro.core.logging import ContextFilter, set_context


@pytest.mark.unit
class TestContextFilter:
    def test_filter_adds_default_fields(self) -> None:
        f = ContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="x",
            lineno=1,
            msg="m",
            args=(),
            exc_info=None,
        )
        f.filter(record)
        assert hasattr(record, "audio_id")
        assert record.audio_id == ""

    def test_set_context_updates_record(self) -> None:
        f = ContextFilter()
        with set_context(audio_id="abc12345", stage="transcription"):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="x",
                lineno=1,
                msg="m",
                args=(),
                exc_info=None,
            )
            f.filter(record)
            assert record.audio_id == "abc12345"
            assert record.stage == "transcription"

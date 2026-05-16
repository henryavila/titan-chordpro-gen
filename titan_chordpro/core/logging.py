# titan_chordpro/core/logging.py
"""Logging utilities for Titan ChordPro Lib.

A ContextFilter adds audio_id/stage/engine/elapsed_ms to log records via
contextvars. Use set_context() as a context manager to scope these fields.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_audio_id: ContextVar[str] = ContextVar("audio_id", default="")
_stage: ContextVar[str] = ContextVar("stage", default="")
_engine: ContextVar[str] = ContextVar("engine", default="")


class ContextFilter(logging.Filter):
    """Adds audio_id/stage/engine to each LogRecord from contextvars."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.audio_id = _audio_id.get()
        record.stage = _stage.get()
        record.engine = _engine.get()
        return True


@contextmanager
def set_context(
    audio_id: str | None = None,
    stage: str | None = None,
    engine: str | None = None,
) -> Iterator[None]:
    """Context manager scoping log fields for the wrapped block."""
    tokens = []
    if audio_id is not None:
        tokens.append(_audio_id.set(audio_id))
    if stage is not None:
        tokens.append(_stage.set(stage))
    if engine is not None:
        tokens.append(_engine.set(engine))
    try:
        yield
    finally:
        # Reset in reverse order
        for token in reversed(tokens):
            # ContextVar tokens are per-variable; reset must match
            try:
                # The variable name isn't on the token; we used setters in order.
                # Simplest: pop the token through its source ContextVar.
                if hasattr(token, "var"):
                    token.var.reset(token)
            except (LookupError, ValueError):
                pass

"""Render helpers for ChordProDocument.

Keeps the core schema ML/IO-free by providing render + write logic here,
imported lazily from ChordProDocument.to_string() / write().
"""

from __future__ import annotations

from pathlib import Path

from titan_chordpro.core.schemas import ChordProDocument
from titan_chordpro.writer.profiles import get_profile


def render(doc: ChordProDocument, profile: str = "inline_slash") -> str:
    return get_profile(profile).render(doc)


def write(doc: ChordProDocument, path: Path, profile: str = "inline_slash") -> None:
    path.write_text(render(doc, profile))

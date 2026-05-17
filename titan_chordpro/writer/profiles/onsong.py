"""OnSong-flavored ChordPro profile.

Differs from inline_slash ONLY in that the `capo` directive uses the
OnSong-specific `x_capo` extension key. Body rendering is unchanged.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 4
"""

from __future__ import annotations

from titan_chordpro.core.schemas import ChordProDocument
from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile


class OnSongProfile(InlineSlashProfile):
    """inline_slash + OnSong `{x_capo}` directive."""

    name: str = "onsong"
    description: str = "OnSong app: inline_slash + {x_capo} extension directive."

    def render(self, doc: ChordProDocument) -> str:
        rendered = super().render(doc)
        if doc.metadata.capo > 0:
            rendered = rendered.replace(
                f"{{capo: {doc.metadata.capo}}}",
                f"{{x_capo: {doc.metadata.capo}}}",
                1,
            )
        return rendered

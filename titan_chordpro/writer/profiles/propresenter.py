"""ProPresenter-flavored ChordPro profile.

Differs from inline_slash ONLY in that an `extensions["ccli"]` key is
promoted to a standalone `{ccli: <id>}` directive (rather than the generic
`{meta: ccli <id>}` form). All other rendering identical.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 4
"""

from __future__ import annotations

from titan_chordpro.core.schemas import ChordProDocument
from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile


class ProPresenterProfile(InlineSlashProfile):
    """inline_slash + {ccli} standalone directive from extensions['ccli']."""

    name: str = "propresenter"
    description: str = "ProPresenter 7: inline_slash + {ccli} directive promotion."

    def render(self, doc: ChordProDocument) -> str:
        rendered = super().render(doc)
        ccli = doc.metadata.extensions.get("ccli")
        if ccli is not None:
            rendered = rendered.replace(
                f"{{meta: ccli {ccli}}}",
                f"{{ccli: {ccli}}}",
                1,
            )
        return rendered

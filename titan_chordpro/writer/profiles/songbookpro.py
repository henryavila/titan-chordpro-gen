"""SongbookPro-flavored ChordPro profile.

Differs from inline_slash ONLY in that `metadata.extensions` keys prefixed
with `sbp_` are aggregated into a single `{x_sbp_tags: key1=val1 key2=val2}`
directive (with the `sbp_` prefix stripped). Non-`sbp_` extensions render
normally as `{meta: key val}`.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 4
"""

from __future__ import annotations

from titan_chordpro.core.schemas import ChordProDocument
from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile

_SBP_PREFIX = "sbp_"


class SongbookProProfile(InlineSlashProfile):
    """inline_slash + {x_sbp_tags} aggregation for `sbp_*` extension keys."""

    name: str = "songbookpro"
    description: str = "SongbookPro: inline_slash + {x_sbp_tags} extension aggregation."

    def render(self, doc: ChordProDocument) -> str:
        rendered = super().render(doc)

        sbp_pairs: list[tuple[str, str]] = [
            (k.removeprefix(_SBP_PREFIX), v)
            for k, v in doc.metadata.extensions.items()
            if k.startswith(_SBP_PREFIX)
        ]
        if not sbp_pairs:
            return rendered

        for original_key in [k for k in doc.metadata.extensions if k.startswith(_SBP_PREFIX)]:
            val = doc.metadata.extensions[original_key]
            rendered = rendered.replace(f"{{meta: {original_key} {val}}}\n", "", 1)

        tag_body = " ".join(f"{k}={v}" for k, v in sbp_pairs)
        aggregated = f"{{x_sbp_tags: {tag_body}}}\n"
        boundary = "\n\n"
        idx = rendered.find(boundary)
        if idx == -1:
            return rendered + aggregated
        return rendered[:idx] + "\n" + aggregated + rendered[idx + 1 :]

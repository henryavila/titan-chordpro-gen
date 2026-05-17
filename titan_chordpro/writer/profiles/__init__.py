"""Output profile registry."""

from titan_chordpro.writer.profiles.base import OutputProfile
from titan_chordpro.writer.profiles.chordpro_ref import ChordProReferenceProfile
from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile
from titan_chordpro.writer.profiles.onsong import OnSongProfile
from titan_chordpro.writer.profiles.propresenter import ProPresenterProfile
from titan_chordpro.writer.profiles.songbookpro import SongbookProProfile

PROFILES: dict[str, OutputProfile] = {
    "inline_slash": InlineSlashProfile(),
    "chordpro_ref": ChordProReferenceProfile(),
    "onsong": OnSongProfile(),
    "propresenter": ProPresenterProfile(),
    "songbookpro": SongbookProProfile(),
}


def get_profile(name: str) -> OutputProfile:
    if name not in PROFILES:
        raise ValueError(f"Unknown output profile: {name!r}. Known: {list(PROFILES)}")
    return PROFILES[name]

"""yt-dlp wrapper with disk cache for the corpus validation harness.

Cache layout:
    ~/.cache/titan-chordpro/audio/<youtube_id>.<ext>

Default format: bestaudio[ext=m4a]/bestaudio (m4a preferred — small,
universally supported by soundfile/librosa).

Re-running validation is idempotent: a cached file is returned without
contacting YouTube.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_MIN_YOUTUBE_ID_LEN = 11
_DEFAULT_EXT = "m4a"
_DEFAULT_FORMAT = "bestaudio[ext=m4a]/bestaudio"


class DownloaderError(RuntimeError):
    """Raised when yt-dlp is missing or download fails."""


def default_cache_root() -> Path:
    """Return the default audio cache root.

    Layout: ~/.cache/titan-chordpro/audio/

    The directory is NOT created here — `download_audio()` creates it
    lazily on first use.
    """
    return Path.home() / ".cache" / "titan-chordpro" / "audio"


def cached_audio_path(youtube_id: str, root: Path | None = None, ext: str = _DEFAULT_EXT) -> Path:
    """Compute the on-disk path for a cached YouTube audio file.

    Raises ValueError when youtube_id is shorter than 11 chars.
    """
    if len(youtube_id) < _MIN_YOUTUBE_ID_LEN:
        raise ValueError(
            f"youtube_id too short ({len(youtube_id)} chars); expected >= {_MIN_YOUTUBE_ID_LEN}"
        )
    base = root if root is not None else default_cache_root()
    return base / f"{youtube_id}.{ext}"


def _yt_dlp_module() -> Any:
    """Return the yt_dlp module, or None if not installed."""
    try:
        import yt_dlp
    except ImportError:
        return None
    return yt_dlp


def _yt_dlp_download(youtube_id: str, target: Path) -> None:
    """Invoke yt-dlp to download audio for `youtube_id` to `target`.

    Internal helper — tests patch this directly.
    """
    yt_dlp = _yt_dlp_module()
    if yt_dlp is None:
        raise DownloaderError("yt-dlp is not installed; pip install '.[validation]'")

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_template = str(target.with_suffix(".dl.%(ext)s"))
    opts = {
        "format": _DEFAULT_FORMAT,
        "outtmpl": tmp_template,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ignoreerrors": False,
    }
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    parent = target.parent
    candidates = sorted(parent.glob(f"{target.stem}.dl.*"))
    if not candidates:
        raise DownloaderError(f"yt-dlp produced no file for {youtube_id}")
    produced = candidates[0]
    final = parent / f"{target.stem}{produced.suffix}"
    produced.rename(final)


def download_audio(youtube_id: str, root: Path | None = None) -> Path:
    """Download YouTube audio for `youtube_id` if not cached, return path.

    Idempotent: a complete cached file is returned without contacting YouTube.
    Raises DownloaderError on yt-dlp absence or network failure.
    """
    if len(youtube_id) < _MIN_YOUTUBE_ID_LEN:
        raise ValueError(
            f"youtube_id too short ({len(youtube_id)} chars); expected >= {_MIN_YOUTUBE_ID_LEN}"
        )
    base = root if root is not None else default_cache_root()
    base.mkdir(parents=True, exist_ok=True)

    # F-005 (Codex review): exclude yt-dlp temp/partial names like
    # `<id>.dl.m4a`, `<id>.m4a.part`, `<id>.dl.m4a.part`. The suffix check
    # alone is insufficient because `.dl.m4a` has suffix `.m4a`, not `.dl`.
    existing = sorted(base.glob(f"{youtube_id}.*"))
    existing = [p for p in existing if _is_complete_audio(p)]
    if existing:
        return existing[0]

    target = cached_audio_path(youtube_id, root=base, ext=_DEFAULT_EXT)
    try:
        _yt_dlp_download(youtube_id, target)
    except DownloaderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DownloaderError(f"yt-dlp download failed for {youtube_id}: {exc}") from exc

    produced = sorted(base.glob(f"{youtube_id}.*"))
    produced = [p for p in produced if _is_complete_audio(p)]
    if not produced:
        raise DownloaderError(f"yt-dlp completed but no file present for {youtube_id}")
    return produced[0]


def _is_complete_audio(path: Path) -> bool:
    """Return True only if `path` is a complete (non-partial) audio file.

    Excludes yt-dlp interim files:
      - <stem>.part (Range/HTTP resume marker)
      - <stem>.dl.<ext> (download template before atomic rename)
      - <stem>.dl.<ext>.part (combo)
    """
    name = path.name
    if name.endswith(".part"):
        return False
    if ".dl." in name:
        return False
    return True

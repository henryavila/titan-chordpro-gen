"""Tests for benchmarks.audio_downloader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


class TestDefaultCacheRoot:
    def test_returns_xdg_cache_path(self) -> None:
        from benchmarks.audio_downloader import default_cache_root

        root = default_cache_root()
        assert root.name == "audio"
        assert root.parent.name == "titan-chordpro"


class TestCachedAudioPath:
    def test_path_format(self, tmp_path: Path) -> None:
        from benchmarks.audio_downloader import cached_audio_path

        p = cached_audio_path("abc12345678", root=tmp_path, ext="m4a")
        assert p.parent == tmp_path
        assert p.name == "abc12345678.m4a"

    def test_default_ext_is_m4a(self, tmp_path: Path) -> None:
        from benchmarks.audio_downloader import cached_audio_path

        p = cached_audio_path("xyz98765432", root=tmp_path)
        assert p.suffix == ".m4a"

    def test_invalid_youtube_id_raises(self, tmp_path: Path) -> None:
        from benchmarks.audio_downloader import cached_audio_path

        with pytest.raises(ValueError, match="youtube_id"):
            cached_audio_path("short", root=tmp_path)


class TestDownloadAudio:
    def test_returns_cached_path_when_present(self, tmp_path: Path) -> None:
        from benchmarks.audio_downloader import download_audio

        cached = tmp_path / "abc12345678.m4a"
        cached.write_bytes(b"\x00" * 100)
        result = download_audio("abc12345678", root=tmp_path)
        assert result == cached

    def test_invokes_yt_dlp_when_not_cached(self, tmp_path: Path) -> None:
        from benchmarks import audio_downloader

        with patch.object(audio_downloader, "_yt_dlp_download") as mock_dl:

            def side_effect(yt_id: str, target: Path) -> None:
                target.write_bytes(b"\x00" * 100)

            mock_dl.side_effect = side_effect
            result = audio_downloader.download_audio("xyz98765432", root=tmp_path)
            mock_dl.assert_called_once()
            assert result.exists()

    def test_raises_when_yt_dlp_unavailable(self, tmp_path: Path) -> None:
        from benchmarks import audio_downloader
        from benchmarks.audio_downloader import DownloaderError

        with patch.object(audio_downloader, "_yt_dlp_module", return_value=None):
            with pytest.raises(DownloaderError, match="yt-dlp is not installed"):
                audio_downloader.download_audio("xyz98765432", root=tmp_path)

    def test_raises_on_yt_dlp_failure(self, tmp_path: Path) -> None:
        from benchmarks import audio_downloader
        from benchmarks.audio_downloader import DownloaderError

        with patch.object(audio_downloader, "_yt_dlp_download") as mock_dl:
            mock_dl.side_effect = RuntimeError("network down")
            with pytest.raises(DownloaderError, match="download failed"):
                audio_downloader.download_audio("xyz98765432", root=tmp_path)

    def test_ignores_partial_dl_files_on_cache_lookup(self, tmp_path: Path) -> None:
        """F-005: <id>.dl.m4a and <id>.m4a.part are interim yt-dlp files;
        cache lookup must NOT treat them as valid downloads."""
        from benchmarks import audio_downloader

        (tmp_path / "abc12345678.dl.m4a").write_bytes(b"\x00" * 100)
        (tmp_path / "abc12345678.m4a.part").write_bytes(b"\x00" * 100)

        with patch.object(audio_downloader, "_yt_dlp_download") as mock_dl:

            def side_effect(yt_id: str, target: Path) -> None:
                target.write_bytes(b"\x00" * 100)

            mock_dl.side_effect = side_effect
            result = audio_downloader.download_audio("abc12345678", root=tmp_path)

        mock_dl.assert_called_once()
        assert ".dl." not in result.name
        assert not result.name.endswith(".part")

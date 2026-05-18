"""Tests for opt-in cache directory helper."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
class TestCacheDir:
    def test_default_root_is_titan_cache_in_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from titan_chordpro.core.cache import cache_dir

        monkeypatch.chdir(tmp_path)
        d = cache_dir("abc123def456")
        assert d == tmp_path / ".titan-cache" / "abc123def456"
        assert d.exists()
        assert d.is_dir()

    def test_custom_root_honored(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import cache_dir

        d = cache_dir("hash", root=tmp_path / "alt")
        assert d == tmp_path / "alt" / "hash"
        assert d.exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import cache_dir

        d1 = cache_dir("hash", root=tmp_path)
        d2 = cache_dir("hash", root=tmp_path)
        assert d1 == d2
        assert d1.exists()

    def test_short_audio_id_rejected(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import cache_dir

        with pytest.raises(ValueError, match="audio_id"):
            cache_dir("abc", root=tmp_path)


@pytest.mark.unit
class TestStageFile:
    def test_stage_file_path(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import stage_file

        p = stage_file("abc123def456", "stems", root=tmp_path)
        assert p == tmp_path / "abc123def456" / "stems.json"

    def test_unknown_stage_rejected(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import stage_file

        with pytest.raises(ValueError, match="stage"):
            stage_file("abc123def456", "unknown", root=tmp_path)

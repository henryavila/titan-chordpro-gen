"""Tests for cache.py dump_stage / load_stage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestDumpStage:
    def test_dump_creates_file(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import dump_stage

        path = dump_stage("abc123def456", "stems", {"vocals": "v.wav"}, root=tmp_path)
        assert path.exists()
        assert path.name == "stems.json"
        assert json.loads(path.read_text())["vocals"] == "v.wav"

    def test_dump_is_atomic(self, tmp_path: Path) -> None:
        """An interrupted dump must NOT leave a half-written canonical file."""
        from titan_chordpro.core.cache import dump_stage

        dump_stage("abc123def456", "chords", {"events": [1, 2, 3]}, root=tmp_path)
        tmp_files = list((tmp_path / "abc123def456").glob("*.tmp"))
        assert tmp_files == []

    def test_dump_overwrites_existing(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import dump_stage

        dump_stage("abc123def456", "beats", {"v": 1}, root=tmp_path)
        dump_stage("abc123def456", "beats", {"v": 2}, root=tmp_path)
        loaded = json.loads((tmp_path / "abc123def456" / "beats.json").read_text())
        assert loaded["v"] == 2

    def test_dump_invalid_stage_raises(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import dump_stage

        with pytest.raises(ValueError, match="unknown stage"):
            dump_stage("abc123def456", "unknown_stage", {}, root=tmp_path)

    def test_dump_document_stage(self, tmp_path: Path) -> None:
        """Spec §749 includes document.json + provenance.json."""
        from titan_chordpro.core.cache import dump_stage

        path = dump_stage("abc123def456", "document", {"sections": []}, root=tmp_path)
        assert path.name == "document.json"

    def test_dump_provenance_stage(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import dump_stage

        path = dump_stage("abc123def456", "provenance", {"titan_version": "0.1.0c0"}, root=tmp_path)
        assert path.name == "provenance.json"


class TestLoadStage:
    def test_load_returns_dict_when_present(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import dump_stage, load_stage

        dump_stage("abc123def456", "syllables", {"items": [1, 2]}, root=tmp_path)
        loaded = load_stage("abc123def456", "syllables", root=tmp_path)
        assert loaded == {"items": [1, 2]}

    def test_load_returns_none_when_absent(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import load_stage

        assert load_stage("abc123def456", "stems", root=tmp_path) is None

    def test_load_returns_none_on_invalid_json(self, tmp_path: Path) -> None:
        """Defensive: a corrupted cache file should be treated as cache-miss."""
        from titan_chordpro.core.cache import load_stage

        d = tmp_path / "abc123def456"
        d.mkdir()
        (d / "chords.json").write_text("{not json")
        assert load_stage("abc123def456", "chords", root=tmp_path) is None

    def test_load_invalid_stage_raises(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import load_stage

        with pytest.raises(ValueError, match="unknown stage"):
            load_stage("abc123def456", "unknown_stage", root=tmp_path)

    def test_load_short_audio_id_raises(self, tmp_path: Path) -> None:
        from titan_chordpro.core.cache import load_stage

        with pytest.raises(ValueError, match="audio_id"):
            load_stage("abc", "stems", root=tmp_path)


class TestStageRoundTrip:
    @pytest.mark.parametrize(
        "stage",
        [
            "stems",
            "transcription",
            "alignment",
            "chords",
            "beats",
            "syllables",
            "document",
            "provenance",
        ],
    )
    def test_round_trip_all_stages(self, tmp_path: Path, stage: str) -> None:
        from titan_chordpro.core.cache import dump_stage, load_stage

        payload = {"stage": stage, "values": [1, 2, 3]}
        dump_stage("abc123def456", stage, payload, root=tmp_path)
        loaded = load_stage("abc123def456", stage, root=tmp_path)
        assert loaded == payload

"""Unit tests for ChordinoEngine (mocked chord_extractor)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestChordinoEngineInit:
    def test_unavailable_raises(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError

        with patch.dict(
            "sys.modules",
            {"chord_extractor": None, "chord_extractor.extractors": None},
        ):
            from titan_chordpro.engines.chord.chordino import ChordinoEngine

            with pytest.raises(EngineUnavailableError, match="chord_extractor"):
                ChordinoEngine()

    def test_info_and_protocol_properties(self) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        engine = ChordinoEngine.__new__(ChordinoEngine)
        info = engine.info
        assert info.name == "chordino"
        assert info.backend == "cpu"
        assert engine.vocabulary == "majmin"
        # Phase C T64: F-004 active. Chordino still does NOT decode
        # inversions natively, but the wrapper now synthesizes slash
        # chords via bass_chroma.extract_bass_note when a bass_stem is
        # provided to detect().
        assert engine.supports_inversions is True


@pytest.mark.unit
class TestChordinoEngineDetect:
    def test_detect_translates_chord_extractor_output(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        # Fake chord_extractor.extractors.Chordino.extract returns objects
        # with .chord (e.g. "C:maj", "G:min7") and .timestamp (float seconds).
        c1 = MagicMock(chord="C:maj", timestamp=0.0)
        c2 = MagicMock(chord="G:min", timestamp=1.5)
        c3 = MagicMock(chord="N", timestamp=3.0)  # no-chord; skipped

        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(return_value=[c1, c2, c3])

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")

        chords = engine.detect(audio)
        assert len(chords) == 2
        assert chords[0].symbol == "C"
        assert chords[0].timestamp.start == 0.0
        assert chords[0].timestamp.end == 1.5
        assert chords[1].symbol == "Gm"
        assert chords[1].timestamp.start == 1.5
        assert chords[1].source_engine == "chordino"

    def test_detect_with_bass_stem_synthesizes_slash(self, tmp_path: Path) -> None:
        """When bass_stem provided, wrapper attaches bass_note from a 2nd pass.

        For Phase B, the bass_note is simply set to None (Chordino does not
        return bass info via chord_extractor). Future Phase B bug-fix may add
        a Cepstrum-based bass detection pass — out of scope here.
        """
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        c1 = MagicMock(chord="C:maj", timestamp=0.0)
        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(return_value=[c1])

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")
        bass = tmp_path / "bass.wav"
        bass.write_bytes(b"x")

        chords = engine.detect(audio, bass_stem=bass)
        assert len(chords) == 1
        assert chords[0].bass_note is None  # Phase B baseline behavior

    def test_detect_empty_chord_list(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(return_value=[])

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")

        # Empty output is acceptable per spec Section 5: percussive audio
        # produces no chords; pipeline continues with LyricLines without
        # chord markers.
        chords = engine.detect(audio)
        assert chords == []

    def test_n_marker_does_not_smear_previous_chord(self, tmp_path: Path) -> None:
        """N (no-chord) must terminate the previous chord, not extend it (F-003).

        Pre-fix bug: N events were dropped BEFORE computing end times, so a
        sequence like C@0, N@1, G@2 produced C from 0..2 instead of 0..1.
        """
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        c1 = MagicMock(chord="C:maj", timestamp=0.0)
        c2 = MagicMock(chord="N", timestamp=1.0)
        c3 = MagicMock(chord="G:maj", timestamp=2.0)
        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(return_value=[c1, c2, c3])

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")

        chords = engine.detect(audio)
        assert len(chords) == 2  # C and G; N is a boundary, not emitted
        assert chords[0].symbol == "C"
        assert chords[0].timestamp.start == 0.0
        assert chords[0].timestamp.end == 1.0, (
            f"C should end at N@1.0, not smear to G@2.0 (end was {chords[0].timestamp.end})"
        )
        assert chords[1].symbol == "G"
        assert chords[1].timestamp.start == 2.0

    def test_detect_native_failure_wrapped(self, tmp_path: Path) -> None:
        from titan_chordpro.core.exceptions import ChordRecognitionError
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(side_effect=RuntimeError("vamp boom"))

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")

        with pytest.raises(ChordRecognitionError, match="chordino"):
            engine.detect(audio)


class TestBassNoteIntegration:
    """F-004: ChordinoEngine emits bass_note when bass_chroma detects an inversion."""

    def test_supports_inversions_is_true(self) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        with patch("titan_chordpro.engines.chord.chordino._load_extractor"):
            engine = ChordinoEngine()
        assert engine.supports_inversions is True

    def test_no_bass_stem_leaves_bass_note_none(self) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        chord_a = MagicMock()
        chord_a.chord = "C:maj"
        chord_a.timestamp = 0.0
        chord_b = MagicMock()
        chord_b.chord = "G:maj"
        chord_b.timestamp = 2.0

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = [chord_a, chord_b]
        with patch(
            "titan_chordpro.engines.chord.chordino._load_extractor",
            return_value=mock_extractor,
        ):
            with patch(
                "titan_chordpro.engines.chord.chordino._probe_duration",
                return_value=4.0,
            ):
                engine = ChordinoEngine()
                events = engine.detect(Path("fake.wav"), bass_stem=None)
        assert all(e.bass_note is None for e in events)

    def test_bass_note_emitted_when_chroma_differs_from_root(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        chord = MagicMock()
        chord.chord = "F:maj"
        chord.timestamp = 0.0
        bass = tmp_path / "bass.wav"
        bass.write_bytes(b"\x00" * 100)

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = [chord]
        with patch(
            "titan_chordpro.engines.chord.chordino._load_extractor",
            return_value=mock_extractor,
        ):
            with patch("titan_chordpro.engines.chord.chordino._probe_duration", return_value=4.0):
                with patch(
                    "titan_chordpro.engines.chord.chordino.extract_bass_note",
                    return_value=("A", 0.85),
                ):
                    engine = ChordinoEngine()
                    events = engine.detect(Path("fake.wav"), bass_stem=bass)

        assert len(events) == 1
        assert events[0].symbol == "F"
        assert events[0].bass_note == "A"

    def test_bass_note_suppressed_when_matches_root(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        chord = MagicMock()
        chord.chord = "F:maj"
        chord.timestamp = 0.0
        bass = tmp_path / "bass.wav"
        bass.write_bytes(b"\x00" * 100)

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = [chord]
        with patch(
            "titan_chordpro.engines.chord.chordino._load_extractor",
            return_value=mock_extractor,
        ):
            with patch("titan_chordpro.engines.chord.chordino._probe_duration", return_value=4.0):
                with patch(
                    "titan_chordpro.engines.chord.chordino.extract_bass_note",
                    return_value=("F", 0.85),
                ):
                    engine = ChordinoEngine()
                    events = engine.detect(Path("fake.wav"), bass_stem=bass)

        assert events[0].bass_note is None

    def test_bass_note_suppressed_when_low_confidence(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        chord = MagicMock()
        chord.chord = "C:maj"
        chord.timestamp = 0.0
        bass = tmp_path / "bass.wav"
        bass.write_bytes(b"\x00" * 100)

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = [chord]
        with patch(
            "titan_chordpro.engines.chord.chordino._load_extractor",
            return_value=mock_extractor,
        ):
            with patch("titan_chordpro.engines.chord.chordino._probe_duration", return_value=4.0):
                with patch(
                    "titan_chordpro.engines.chord.chordino.extract_bass_note",
                    return_value=(None, 0.3),
                ):
                    engine = ChordinoEngine()
                    events = engine.detect(Path("fake.wav"), bass_stem=bass)

        assert events[0].bass_note is None

    def test_native_slash_symbol_is_not_overridden_by_bass_chroma(self, tmp_path: Path) -> None:
        """Phase C T70-iter2 follow-up: when chordino itself emits a slash
        chord (e.g. 'C#/E#'), the wrapper must NOT also set bass_note from
        bass_chroma. The schema validator rejects disagreement (E# vs F)
        even when the two are enharmonically equivalent. Trust the native
        slash output."""
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        chord = MagicMock()
        chord.chord = "C#/E#"  # chordino emits raw slash chord — already has bass
        chord.timestamp = 0.0
        bass = tmp_path / "bass.wav"
        bass.write_bytes(b"\x00" * 100)

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = [chord]
        with patch(
            "titan_chordpro.engines.chord.chordino._load_extractor",
            return_value=mock_extractor,
        ):
            with patch("titan_chordpro.engines.chord.chordino._probe_duration", return_value=4.0):
                with patch(
                    "titan_chordpro.engines.chord.chordino.extract_bass_note",
                    return_value=("F", 0.9),  # F is enharmonic of E# — would crash
                ):
                    engine = ChordinoEngine()
                    events = engine.detect(Path("fake.wav"), bass_stem=bass)

        assert len(events) == 1
        assert events[0].symbol == "C#/E#"
        assert events[0].bass_note is None  # bass info already in symbol; not duplicated

    def test_bass_note_chord_with_quality_extracts_root(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        chord = MagicMock()
        chord.chord = "G:min7"
        chord.timestamp = 0.0
        bass = tmp_path / "bass.wav"
        bass.write_bytes(b"\x00" * 100)

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = [chord]
        with patch(
            "titan_chordpro.engines.chord.chordino._load_extractor",
            return_value=mock_extractor,
        ):
            with patch("titan_chordpro.engines.chord.chordino._probe_duration", return_value=4.0):
                with patch(
                    "titan_chordpro.engines.chord.chordino.extract_bass_note",
                    return_value=("D", 0.8),
                ):
                    engine = ChordinoEngine()
                    events = engine.detect(Path("fake.wav"), bass_stem=bass)

        assert events[0].symbol == "Gm7"
        assert events[0].bass_note == "D"

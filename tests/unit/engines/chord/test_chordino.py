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


@pytest.mark.unit
class TestChordPostprocess:
    """Phase C T70 quality-loop: merge / key-snap / collapse helpers."""

    def _evt(self, symbol: str, start: float, end: float) -> object:
        from titan_chordpro.core.schemas import ChordEvent, TimeStamp

        return ChordEvent(
            symbol=symbol,
            timestamp=TimeStamp(start=start, end=end),
            source_engine="mock",
        )

    def test_merge_short_absorbed_into_longer_neighbour(self) -> None:
        from titan_chordpro.engines.chord.chordino import merge_short_chords

        events = [
            self._evt("C", 0.0, 2.0),
            self._evt("C#", 2.0, 2.3),  # 0.3s flutter
            self._evt("G", 2.3, 4.0),
        ]
        merged = merge_short_chords(events, min_duration=0.6)
        assert len(merged) == 2
        assert merged[0].symbol == "C"
        assert merged[0].timestamp.end == pytest.approx(2.3)
        assert merged[1].symbol == "G"

    def test_collapse_adjacent_same_majmin_root(self) -> None:
        from titan_chordpro.engines.chord.chordino import collapse_adjacent_same_root

        events = [
            self._evt("Am", 0.0, 1.0),
            self._evt("Am7", 1.0, 2.5),  # same majmin root+quality
            self._evt("F", 2.5, 4.0),
        ]
        out = collapse_adjacent_same_root(events)
        assert len(out) == 2
        assert out[0].symbol == "Am7"  # longer segment wins spelling
        assert out[0].timestamp.start == 0.0
        assert out[0].timestamp.end == 2.5
        assert out[1].symbol == "F"

    def test_estimate_key_prefers_c_major_on_c_g_am_f(self) -> None:
        from titan_chordpro.engines.chord.chordino import estimate_key

        events = [
            self._evt("C", 0, 2),
            self._evt("G", 2, 4),
            self._evt("Am", 4, 6),
            self._evt("F", 6, 8),
            self._evt("C", 8, 10),
        ]
        root, mode = estimate_key(events)
        assert root == "C"
        assert mode == "major"

    def test_snap_out_of_key_to_diatonic(self) -> None:
        from titan_chordpro.engines.chord.chordino import snap_events_to_key

        events = [
            self._evt("C", 0, 2),
            self._evt("C#", 2, 4),  # out of C major
            self._evt("G", 4, 6),
        ]
        snapped = snap_events_to_key(events, "C", "major")
        roots = [e.symbol for e in snapped]
        assert roots[0] == "C"
        assert roots[1] != "C#"  # snapped onto diatonic
        assert roots[2] == "G"

    def test_postprocess_pipeline_removes_flutter_and_chromatic(self) -> None:
        from titan_chordpro.engines.chord.chordino import postprocess_chords

        events = [
            self._evt("C", 0.0, 2.0),
            self._evt("C#", 2.0, 2.2),  # flutter + chromatic
            self._evt("G", 2.2, 4.0),
            self._evt("Ab", 4.0, 6.0),  # chromatic (near G)
            self._evt("F", 6.0, 8.0),
        ]
        out = postprocess_chords(events)
        symbols = [e.symbol for e in out]
        # No raw chromatics remain.
        assert "C#" not in symbols
        assert "Ab" not in symbols
        # Coverage preserved roughly end-to-end.
        assert out[0].timestamp.start == 0.0
        assert out[-1].timestamp.end == pytest.approx(8.0)

    def test_detect_applies_postprocess(self, tmp_path: Path) -> None:
        """detect() must run postprocess_chords (flutter gone)."""
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        # C@0, C#@2.0 (flutter to 2.2 via next), G@2.2 → after postprocess C then G.
        raw = [
            MagicMock(chord="C:maj", timestamp=0.0),
            MagicMock(chord="C#:maj", timestamp=2.0),
            MagicMock(chord="G:maj", timestamp=2.2),
        ]
        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(return_value=raw)
        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")
        with patch(
            "titan_chordpro.engines.chord.chordino._probe_duration",
            return_value=5.0,
        ):
            events = engine.detect(audio)
        symbols = [e.symbol for e in events]
        assert "C#" not in symbols
        assert symbols[0] == "C"
        assert "G" in symbols

    def test_collapse_does_not_merge_adjacent_different_roots(self) -> None:
        """RC3: C–G–Am–F mid-loop changes must survive collapse."""
        from titan_chordpro.engines.chord.chordino import collapse_adjacent_same_root

        events = [
            self._evt("C", 0.0, 2.0),
            self._evt("G", 2.0, 4.0),
            self._evt("Am", 4.0, 6.0),
            self._evt("F", 6.0, 8.0),
        ]
        out = collapse_adjacent_same_root(events)
        assert [e.symbol for e in out] == ["C", "G", "Am", "F"]

    def test_merge_does_not_absorb_legitimate_short_change(self) -> None:
        """RC3: different-root events at/above min duration are not merged away."""
        from titan_chordpro.engines.chord.chordino import merge_short_chords

        # 0.65s G between long C holds — above MIN_CHORD_DURATION_S (0.60).
        events = [
            self._evt("C", 0.0, 2.0),
            self._evt("G", 2.0, 2.65),
            self._evt("Am", 2.65, 4.5),
            self._evt("F", 4.5, 6.5),
        ]
        merged = merge_short_chords(events, min_duration=0.60)
        assert [e.symbol for e in merged] == ["C", "G", "Am", "F"]
        assert merged[1].timestamp.end - merged[1].timestamp.start == pytest.approx(0.65)

    def test_postprocess_preserves_cgamf_loop(self) -> None:
        from titan_chordpro.engines.chord.chordino import postprocess_chords

        events = [
            self._evt("C", 0.0, 1.8),
            self._evt("G", 1.8, 3.6),
            self._evt("Am", 3.6, 5.4),
            self._evt("F", 5.4, 7.2),
            self._evt("C", 7.2, 9.0),
            self._evt("G", 9.0, 10.8),
            self._evt("Am", 10.8, 12.6),
            self._evt("F", 12.6, 14.4),
        ]
        out = postprocess_chords(events)
        symbols = [e.symbol for e in out]
        assert symbols == ["C", "G", "Am", "F", "C", "G", "Am", "F"]

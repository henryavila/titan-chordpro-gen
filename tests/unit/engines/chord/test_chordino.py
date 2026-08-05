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

    def test_bass_note_suppressed_on_mid_interval_with_marginal_conf(self, tmp_path: Path) -> None:
        """H2: mid-duration post-reseg slice needs conf above raised floor.

        extract_bass_note may still return a letter with conf in (0.5, mid_floor)
        for diagnostic callers; attach must not emit slash on that band.
        """
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        chord_a = MagicMock()
        chord_a.chord = "G:maj"
        chord_a.timestamp = 0.0
        chord_b = MagicMock()
        chord_b.chord = "C:maj"
        chord_b.timestamp = 1.5  # → first event duration 1.5s (mid band)

        bass = tmp_path / "bass.wav"
        bass.write_bytes(b"\x00" * 100)

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
                with patch(
                    "titan_chordpro.engines.chord.chordino.extract_bass_note",
                    return_value=("B", 0.60),  # above old 0.5 floor, below mid floor
                ):
                    engine = ChordinoEngine()
                    events = engine.detect(Path("fake.wav"), bass_stem=bass)

        g_events = [e for e in events if e.symbol == "G"]
        assert g_events
        assert g_events[0].bass_note is None

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


@pytest.mark.unit
class TestResegmentLongHolds:
    """RC3: beat-window chroma re-check splits multi-bar tonic holds.

    Pure function tests inject a synthetic chromagram — no audio, no song
    hardcodes. Invariant: when an alternate diatonic triad dominates ≥1 beat
    inside a long hold, emit a change near the beat boundary.
    """

    def _evt(self, symbol: str, start: float, end: float) -> object:
        from titan_chordpro.core.schemas import ChordEvent, TimeStamp

        return ChordEvent(
            symbol=symbol,
            timestamp=TimeStamp(start=start, end=end),
            source_engine="mock",
        )

    def _chroma_from_segments(
        self,
        segments: list[tuple[str, str, float, float]],
        duration: float,
        hop: float = 0.1,
    ):
        """Build (chroma[12,n], times[n]) from (root, quality, t0, t1) segments."""
        import numpy as np

        from titan_chordpro.engines.chord.chordino import _triad_pitch_classes

        n = int(round(duration / hop)) + 1
        times = np.arange(n, dtype=float) * hop
        chroma = np.full((12, n), 0.05, dtype=float)
        for root, quality, t0, t1 in segments:
            pcs = _triad_pitch_classes(root, quality)
            for i, t in enumerate(times):
                if t0 <= t < t1:
                    for pc in pcs:
                        chroma[pc, i] = 1.0
        # Column-normalize lightly so scores are comparable.
        chroma = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-9)
        return chroma, times

    def test_long_c_hold_with_mid_g_chroma_splits(self) -> None:
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        # 8s C hold; chroma is C for 0-4s then G for 4-8s (classic skipped V).
        events = [self._evt("C", 0.0, 8.0)]
        chroma, times = self._chroma_from_segments(
            [("C", "maj", 0.0, 4.0), ("G", "maj", 4.0, 8.0)],
            duration=8.0,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
        )
        symbols = [e.symbol for e in out]
        assert "G" in symbols, f"expected mid-hold G insert, got {symbols}"
        assert symbols[0].startswith("C")
        # Coverage preserved.
        assert out[0].timestamp.start == pytest.approx(0.0)
        assert out[-1].timestamp.end == pytest.approx(8.0)
        # Change near 4s (±1 beat).
        g = next(e for e in out if e.symbol == "G" or e.symbol.startswith("G"))
        assert 3.0 <= g.timestamp.start <= 5.0

    def test_consistent_chroma_does_not_split(self) -> None:
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        events = [self._evt("C", 0.0, 8.0)]
        chroma, times = self._chroma_from_segments(
            [("C", "maj", 0.0, 8.0)],
            duration=8.0,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
        )
        assert len(out) == 1
        assert out[0].symbol == "C"
        assert out[0].timestamp.start == 0.0
        assert out[0].timestamp.end == 8.0

    def test_short_alternate_below_one_beat_does_not_split(self) -> None:
        """Flutter alternate shorter than one beat must not create a change."""
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        events = [self._evt("C", 0.0, 6.0)]
        # 0.3s blip of G — below beat_period=0.8.
        chroma, times = self._chroma_from_segments(
            [
                ("C", "maj", 0.0, 3.0),
                ("G", "maj", 3.0, 3.3),
                ("C", "maj", 3.3, 6.0),
            ],
            duration=6.0,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
        )
        assert len(out) == 1
        assert out[0].symbol == "C"

    def test_short_events_below_min_hold_unchanged(self) -> None:
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        events = [
            self._evt("C", 0.0, 1.6),
            self._evt("G", 1.6, 3.2),
            self._evt("Am", 3.2, 4.8),
            self._evt("F", 4.8, 6.4),
        ]
        # Even if chroma would prefer something else, short holds are not reseg'd.
        chroma, times = self._chroma_from_segments(
            [("C", "maj", 0.0, 6.4)],
            duration=6.4,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
        )
        assert [e.symbol for e in out] == ["C", "G", "Am", "F"]

    def test_resegment_then_postprocess_preserves_cgamf(self) -> None:
        """Full path: long C with G chroma mid-span → C-G-Am-F after postprocess."""
        from titan_chordpro.engines.chord.chordino import (
            postprocess_chords,
            resegment_long_holds,
        )

        # Chordino-style under-seg: C 0-4, Am 4-6, F 6-8 (skipped G).
        # Chroma has G energy 2-4 so reseg should insert G before Am.
        events = [
            self._evt("C", 0.0, 4.0),
            self._evt("Am", 4.0, 6.0),
            self._evt("F", 6.0, 8.0),
        ]
        chroma, times = self._chroma_from_segments(
            [
                ("C", "maj", 0.0, 2.0),
                ("G", "maj", 2.0, 4.0),
                ("A", "min", 4.0, 6.0),
                ("F", "maj", 6.0, 8.0),
            ],
            duration=8.0,
        )
        refined = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
        )
        out = postprocess_chords(refined)
        symbols = [e.symbol for e in out]
        assert symbols[:4] == ["C", "G", "Am", "F"] or (
            "G" in symbols and symbols[0] == "C" and "Am" in symbols and "F" in symbols
        ), f"expected C-G-Am-F-ish, got {symbols}"

    def test_weak_v_energy_mid_hold_inserts_g(self) -> None:
        """P0/P2: long I with competitive V for ≥1 full beat must insert V.

        Synthetic: C pad for 0–6s; mid window has slightly stronger G triad
        energy (weak V under pads). Primary-function margin for V is looser
        than the default, so this must split even when G only barely wins.
        """
        import numpy as np

        from titan_chordpro.engines.chord.chordino import (
            _triad_pitch_classes,
            resegment_long_holds,
        )

        events = [self._evt("C", 0.0, 6.0)]
        hop = 0.1
        duration = 6.0
        n = int(round(duration / hop)) + 1
        times = np.arange(n, dtype=float) * hop
        chroma = np.full((12, n), 0.05, dtype=float)
        c_pcs = _triad_pitch_classes("C", "maj")
        g_pcs = _triad_pitch_classes("G", "maj")
        for i, t in enumerate(times):
            if 2.0 <= t < 3.2:
                # Weak V: G triad slightly above C (shared G bin).
                for pc in c_pcs:
                    chroma[pc, i] = 0.85
                for pc in g_pcs:
                    chroma[pc, i] = 1.05
                chroma[g_pcs[0], i] = 1.15  # G root bin edge
            else:
                for pc in c_pcs:
                    chroma[pc, i] = 1.0
        chroma = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-9)

        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
        )
        symbols = [e.symbol for e in out]
        assert "G" in symbols, f"expected weak-V insert of G, got {symbols}"
        assert symbols[0].startswith("C")

    def test_weak_em_like_energy_under_c_does_not_insert_em(self) -> None:
        """P0: elevated E energy under long C must NOT insert false iii (Em).

        E-rich pads share two pitch classes with Em (E,G) and C (E). iii is a
        secondary function — require stronger evidence than primary V.
        """
        import numpy as np

        from titan_chordpro.engines.chord.chordino import (
            _triad_pitch_classes,
            resegment_long_holds,
        )

        events = [self._evt("C", 0.0, 6.0)]
        hop = 0.1
        duration = 6.0
        n = int(round(duration / hop)) + 1
        times = np.arange(n, dtype=float) * hop
        chroma = np.full((12, n), 0.05, dtype=float)
        c_pcs = _triad_pitch_classes("C", "maj")  # C E G
        for i, t in enumerate(times):
            for pc in c_pcs:
                chroma[pc, i] = 1.0
            if 2.0 <= t < 4.0:
                # Boost E (and a touch of B) — Em-like overtones, not a real V.
                chroma[4, i] = 1.35  # E
                chroma[11, i] = 0.55  # B (Em third of fifth partial-ish)
        chroma = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-9)

        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
        )
        symbols = [e.symbol for e in out]
        assert "Em" not in symbols, f"false iii insert: {symbols}"
        assert all(s.startswith("C") or s == "C" for s in symbols) or symbols == ["C"], (
            f"expected no Em split under C pad, got {symbols}"
        )

    def test_iii_vs_v_prefers_v_when_both_competitive(self) -> None:
        """When V and iii both score well under I, prefer primary V."""
        import numpy as np

        from titan_chordpro.engines.chord.chordino import (
            _triad_pitch_classes,
            resegment_long_holds,
        )

        events = [self._evt("C", 0.0, 6.0)]
        hop = 0.1
        duration = 6.0
        n = int(round(duration / hop)) + 1
        times = np.arange(n, dtype=float) * hop
        chroma = np.full((12, n), 0.05, dtype=float)
        c_pcs = _triad_pitch_classes("C", "maj")
        g_pcs = _triad_pitch_classes("G", "maj")
        em_pcs = _triad_pitch_classes("E", "min")
        for i, t in enumerate(times):
            if 2.0 <= t < 4.0:
                for pc in c_pcs:
                    chroma[pc, i] = 0.6
                for pc in g_pcs:
                    chroma[pc, i] = 1.0
                for pc in em_pcs:
                    chroma[pc, i] = max(chroma[pc, i], 0.95)
                chroma[7, i] = 1.2  # G root wins
            else:
                for pc in c_pcs:
                    chroma[pc, i] = 1.0
        chroma = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-9)

        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
        )
        symbols = [e.symbol for e in out]
        assert "G" in symbols, f"expected V not iii, got {symbols}"
        assert "Em" not in symbols, f"iii must not win over V: {symbols}"

    def test_reseg_split_clears_bass_on_both_pieces(self) -> None:
        """P1: after split, neither piece inherits sticky pre-split bass_note."""
        from titan_chordpro.core.schemas import ChordEvent, TimeStamp
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        ev = ChordEvent(
            symbol="C",
            timestamp=TimeStamp(start=0.0, end=8.0),
            bass_note="G",  # sticky fifth from long interval that included later G
            source_engine="mock",
        )
        chroma, times = self._chroma_from_segments(
            [("C", "maj", 0.0, 4.0), ("G", "maj", 4.0, 8.0)],
            duration=8.0,
        )
        out = resegment_long_holds(
            [ev],
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
        )
        assert len(out) >= 2, f"expected split, got {[e.symbol for e in out]}"
        for piece in out:
            assert piece.bass_note is None, (
                f"split piece {piece.symbol}@{piece.timestamp.start} kept bass={piece.bass_note}"
            )

    def test_multipass_splits_second_change_in_long_hold(self) -> None:
        """H1: single-split leaves a long alternate suffix; multipass peels again.

        Synthetic 12s C hold with chroma C→G→F (4s each). One pass yields
        C|G(rest) via suffix-commit; a second pass must still split G→F so the
        multi-bar pad does not swallow the final chord.
        """
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        events = [self._evt("C", 0.0, 12.0)]
        chroma, times = self._chroma_from_segments(
            [
                ("C", "maj", 0.0, 4.0),
                ("G", "maj", 4.0, 8.0),
                ("F", "maj", 8.0, 12.0),
            ],
            duration=12.0,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
            max_passes=4,
        )
        symbols = [e.symbol for e in out]
        assert "G" in symbols, f"expected G insert, got {symbols}"
        assert "F" in symbols, f"expected multipass F peel, got {symbols}"
        assert symbols[0].startswith("C")
        assert out[0].timestamp.start == pytest.approx(0.0)
        assert out[-1].timestamp.end == pytest.approx(12.0)
        # Three pieces (or more after post-collapse) covering the progression.
        assert len(out) >= 3, f"expected ≥3 segments after multipass, got {symbols}"

    def test_multipass_stable_when_no_further_split(self) -> None:
        """Consistent chroma must still be a single event even with max_passes>1."""
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        events = [self._evt("C", 0.0, 8.0)]
        chroma, times = self._chroma_from_segments(
            [("C", "maj", 0.0, 8.0)],
            duration=8.0,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.8,
            key_root="C",
            mode="major",
            max_passes=6,
        )
        assert len(out) == 1
        assert out[0].symbol == "C"

    def test_force_relabel_rewrites_wrong_onset_on_very_long_hold(self) -> None:
        """H1b: ≥12s hold with chroma C then F must emit C|F (onset rewrite).

        Single-split keeps Chordino onset and only inserts mid-hold alternates,
        so a span mislabeled F that actually opens on C never fixes the head.
        """
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        events = [self._evt("F", 0.0, 14.0)]
        chroma, times = self._chroma_from_segments(
            [
                ("C", "maj", 0.0, 3.0),
                ("F", "maj", 3.0, 14.0),
            ],
            duration=14.0,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=1.0,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
            min_alt_s=1.0,
        )
        symbols = [e.symbol for e in out]
        assert symbols[0].startswith("C"), f"expected C onset rewrite, got {symbols}"
        assert any(s.startswith("F") for s in symbols), f"expected F retained, got {symbols}"
        assert out[0].timestamp.start == pytest.approx(0.0)
        assert out[-1].timestamp.end == pytest.approx(14.0)
        assert len(out) >= 2

    def test_force_relabel_folds_leading_sub_floor_alternate(self) -> None:
        """P3: leading short run (< alt_floor) folds into next, not kept as blip.

        beat_period=0.5, min_alt_s=1.0 → first 0.5s alternate is sub-floor.
        Long hold with 0.5s leading G then long C must yield a single C event
        (no spurious leading alternate onset).
        """
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        events = [self._evt("C", 0.0, 14.0)]
        chroma, times = self._chroma_from_segments(
            [
                ("G", "maj", 0.0, 0.5),
                ("C", "maj", 0.5, 14.0),
            ],
            duration=14.0,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.5,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
            min_alt_s=1.0,
        )
        symbols = [e.symbol for e in out]
        assert len(out) == 1, f"expected single event after folding leading blip, got {symbols}"
        assert symbols[0].startswith("C"), f"expected C, got {symbols}"
        assert out[0].timestamp.start == pytest.approx(0.0)
        assert out[0].timestamp.end == pytest.approx(14.0)

    def test_force_relabel_folds_chained_leading_sub_floor_runs(self) -> None:
        """P2: consecutive leading shorts must not synthesize a floor-length alt.

        beat_period=0.5, min_alt_s=1.0. Leading 0.5s G then 0.5s F then long C
        must yield a single C — chaining two sub-floor blips into a 1.0s F
        onset (F|C) is incorrect; only a run that individually meets
        alt_floor may become an alternate.
        """
        from titan_chordpro.engines.chord.chordino import resegment_long_holds

        events = [self._evt("C", 0.0, 14.0)]
        chroma, times = self._chroma_from_segments(
            [
                ("G", "maj", 0.0, 0.5),
                ("F", "maj", 0.5, 1.0),
                ("C", "maj", 1.0, 14.0),
            ],
            duration=14.0,
        )
        out = resegment_long_holds(
            events,
            chroma=chroma,
            frame_times=times,
            beat_period=0.5,
            key_root="C",
            mode="major",
            min_hold_s=2.5,
            min_alt_s=1.0,
        )
        symbols = [e.symbol for e in out]
        assert len(out) == 1, (
            f"expected single C after folding chained leading blips, got {symbols}"
        )
        assert symbols[0].startswith("C"), f"expected C, got {symbols}"
        assert not any(s.startswith("F") for s in symbols), (
            f"chained shorts must not synthesize F onset: {symbols}"
        )
        assert out[0].timestamp.start == pytest.approx(0.0)
        assert out[0].timestamp.end == pytest.approx(14.0)


@pytest.mark.unit
class TestBassRecomputeAfterReseg:
    """P1: detect() recomputes bass on final intervals after reseg/postprocess."""

    def test_detect_recomputes_bass_after_reseg_split(self, tmp_path: Path) -> None:
        """Long C with pre-attached sticky bass must not leave C/G on prefix.

        We mock extract_bass_note to return G for the full [0,8) interval
        (pre-reseg sticky behaviour) and C for the short prefix [0, split)
        so post-reseg recompute yields honest root-position C on the left.
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

        # Synthetic chroma: C then G mid-hold so reseg splits.
        import numpy as np

        from titan_chordpro.engines.chord.chordino import _triad_pitch_classes

        hop = 0.1
        duration = 8.0
        n = int(round(duration / hop)) + 1
        times = np.arange(n, dtype=float) * hop
        chroma = np.full((12, n), 0.05, dtype=float)
        for i, t in enumerate(times):
            root, qual = ("G", "maj") if t >= 4.0 else ("C", "maj")
            for pc in _triad_pitch_classes(root, qual):
                chroma[pc, i] = 1.0
        chroma = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-9)

        def fake_bass(path, start, end):
            # Full long interval (or anything spanning past 4s) → G (sticky).
            # Prefix-only after reseg → C (honest root).
            if end <= 4.5:
                return ("C", 0.9)
            return ("G", 0.9)

        with (
            patch(
                "titan_chordpro.engines.chord.chordino._probe_duration",
                return_value=8.0,
            ),
            patch(
                "titan_chordpro.engines.chord.chordino.load_harmonic_chroma",
                return_value=(chroma, times),
            ),
            patch(
                "titan_chordpro.engines.chord.chordino.extract_bass_note",
                side_effect=fake_bass,
            ),
            patch(
                "titan_chordpro.engines.chord.chordino.estimate_beat_period",
                return_value=0.8,
            ),
        ):
            events = engine.detect(audio, bass_stem=bass)

        # First event should be C without slash (bass matches root → suppressed).
        assert events, "expected events"
        first = events[0]
        assert first.symbol.startswith("C")
        assert first.bass_note is None, (
            f"prefix must not keep sticky G bass; got bass_note={first.bass_note}"
        )

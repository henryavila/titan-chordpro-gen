"""Tests for benchmarks.metrics."""

from __future__ import annotations

import pytest

pytest.importorskip("mir_eval")


class TestToMirEvalChord:
    @pytest.mark.parametrize(
        "titan,expected",
        [
            ("C", "C:maj"),
            ("G", "G:maj"),
            ("Am", "A:min"),
            ("Gm", "G:min"),
            ("Cm7", "C:min7"),
            ("Cmaj7", "C:maj7"),
            ("F#", "F#:maj"),
            ("Bbm", "Bb:min"),
            ("F/A", "F:maj/A"),
            ("Gm/Bb", "G:min/Bb"),
            ("N", "N"),
            # Brazilian "7M" notation for maj7 (T70 iter)
            ("F7M", "F:maj7"),
            ("C7M", "C:maj7"),
            ("F7M/A", "F:maj7/A"),
            # Suspended chords collapse to root major (T70 iter — surfaced by corpus song "Entrega")
            ("Esus", "E:maj"),
            ("Csus2", "C:maj"),
            ("Asus4", "A:maj"),
            ("Esus/B", "E:maj/B"),
            # Brazilian add9 / 6 — surfaced by "Tua vontade" with 'D9'
            ("D9", "D:maj"),
            ("G9", "G:maj"),
            ("C6", "C:maj"),
            ("Am9", "A:min"),
            ("Am6", "A:min"),
            # Augmented + symbol
            ("Caug", "C:aug"),
            ("C+", "C:aug"),
            # Catch-all: exotic suffix falls back to root major/min
            ("Bm7b5", "B:min"),
            ("C13", "C:maj"),
            ("Cmaj9", "C:maj"),
        ],
    )
    def test_to_mir_eval_chord(self, titan: str, expected: str) -> None:
        from benchmarks.metrics import to_mir_eval_chord

        assert to_mir_eval_chord(titan) == expected


class TestComputeWcsrMajmin:
    def test_perfect_match(self) -> None:
        from benchmarks.metrics import compute_wcsr_majmin

        intervals = [(0.0, 1.0), (1.0, 2.0)]
        ref = ["C:maj", "G:maj"]
        score = compute_wcsr_majmin(intervals, ref, intervals, ref)
        assert score == pytest.approx(1.0)

    def test_total_mismatch(self) -> None:
        from benchmarks.metrics import compute_wcsr_majmin

        intervals = [(0.0, 1.0), (1.0, 2.0)]
        ref = ["C:maj", "G:maj"]
        est = ["F:maj", "A:min"]
        score = compute_wcsr_majmin(intervals, ref, intervals, est)
        assert score < 0.1


class TestComputeBeatConsistencyVsLibrosa:
    """Beat consistency cross-detector diagnostic (Phase C T67b)."""

    def test_empty_titan_beats_returns_zero(self, tmp_path) -> None:
        from benchmarks.metrics import compute_beat_consistency_vs_librosa

        # Audio file does not need to exist — empty titan_beats short-circuits.
        result = compute_beat_consistency_vs_librosa(tmp_path / "missing.wav", [])
        assert result == {"f_measure": 0.0, "amlt": 0.0}

    def test_missing_audio_returns_zero(self, tmp_path) -> None:
        from benchmarks.metrics import compute_beat_consistency_vs_librosa

        result = compute_beat_consistency_vs_librosa(
            tmp_path / "does-not-exist.wav", [1.0, 2.0, 3.0]
        )
        assert result == {"f_measure": 0.0, "amlt": 0.0}

    def test_synthetic_click_track_consistency(self, tmp_path) -> None:
        """Synthetic click track at 120 BPM: librosa + clean beats should
        agree on AMLt close to 1.0 (octave-invariant), and F-measure >= 0.0.
        Phase C T67b — verifies the diagnostic plumbing, not absolute
        accuracy (librosa beat detection is not deterministic at the bar
        level on synthetic clicks)."""
        pytest.importorskip("librosa")
        pytest.importorskip("soundfile")
        import numpy as np
        import soundfile as sf

        from benchmarks.metrics import compute_beat_consistency_vs_librosa

        sr = 22050
        duration_s = 8.0
        bpm = 120.0
        beat_period = 60.0 / bpm  # 0.5s
        n_samples = int(sr * duration_s)
        audio = np.zeros(n_samples, dtype=np.float32)
        # 10ms click envelope at each beat
        click_len = int(sr * 0.01)
        beat_times: list[float] = []
        t = 0.0
        while t < duration_s:
            start = int(t * sr)
            audio[start : start + click_len] = 0.8
            beat_times.append(t)
            t += beat_period
        wav = tmp_path / "click.wav"
        sf.write(str(wav), audio, sr)

        result = compute_beat_consistency_vs_librosa(wav, beat_times)
        assert 0.0 <= result["f_measure"] <= 1.0
        assert 0.0 <= result["amlt"] <= 1.0


class TestChordEventsToIntervals:
    def test_basic(self) -> None:
        from benchmarks.metrics import chord_events_to_intervals
        from titan_chordpro.core.schemas import ChordEvent, TimeStamp

        evts = [
            ChordEvent(
                symbol="C",
                timestamp=TimeStamp(start=0.0, end=2.0),
                confidence=1.0,
                source_engine="t",
            ),
            ChordEvent(
                symbol="G",
                timestamp=TimeStamp(start=2.0, end=4.0),
                bass_note="B",
                confidence=1.0,
                source_engine="t",
            ),
        ]
        intervals, labels = chord_events_to_intervals(evts)
        assert intervals == [(0.0, 2.0), (2.0, 4.0)]
        assert labels == ["C:maj", "G:maj/B"]

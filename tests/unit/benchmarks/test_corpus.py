"""Tests for benchmarks.corpus — songs.csv loader."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest


def _write_corpus_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["title", "external_link", "chordpro"])
        w.writeheader()
        w.writerows(rows)


class TestSongDataclass:
    def test_song_fields(self) -> None:
        from benchmarks.corpus import Song

        s = Song(
            title="Entrega",
            external_link="https://youtu.be/5qDYNTIJPsI",
            chordpro="{t: Entrega}\n[C]Hello",
            youtube_id="5qDYNTIJPsI",
        )
        assert s.title == "Entrega"
        assert s.youtube_id == "5qDYNTIJPsI"
        assert "Entrega" in s.chordpro


class TestLoadCorpus:
    def test_load_skips_empty_external_link(self, tmp_path: Path) -> None:
        from benchmarks.corpus import load_corpus

        csv_path = tmp_path / "songs.csv"
        _write_corpus_csv(
            csv_path,
            [
                {
                    "title": "A",
                    "external_link": "https://youtu.be/aaaaaaaaaaa",
                    "chordpro": "{t: A}",
                },
                {"title": "B", "external_link": "", "chordpro": "{t: B}"},
                {
                    "title": "C",
                    "external_link": "https://www.youtube.com/watch?v=ccccccccccc",
                    "chordpro": "{t: C}",
                },
            ],
        )
        songs, skipped = load_corpus(csv_path)
        assert len(songs) == 2
        assert skipped == 1
        assert songs[0].title == "A"
        assert songs[1].title == "C"

    def test_load_parses_youtube_id_short_form(self, tmp_path: Path) -> None:
        from benchmarks.corpus import load_corpus

        csv_path = tmp_path / "songs.csv"
        _write_corpus_csv(
            csv_path,
            [{"title": "X", "external_link": "https://youtu.be/abcDEF12345", "chordpro": "{t: X}"}],
        )
        songs, _ = load_corpus(csv_path)
        assert songs[0].youtube_id == "abcDEF12345"

    def test_load_parses_youtube_id_long_form(self, tmp_path: Path) -> None:
        from benchmarks.corpus import load_corpus

        csv_path = tmp_path / "songs.csv"
        _write_corpus_csv(
            csv_path,
            [
                {
                    "title": "Y",
                    "external_link": "https://www.youtube.com/watch?v=XYZ987abcde&t=15s",
                    "chordpro": "{t: Y}",
                }
            ],
        )
        songs, _ = load_corpus(csv_path)
        assert songs[0].youtube_id == "XYZ987abcde"

    def test_load_skips_non_youtube_url(self, tmp_path: Path) -> None:
        from benchmarks.corpus import load_corpus

        csv_path = tmp_path / "songs.csv"
        _write_corpus_csv(
            csv_path,
            [{"title": "Z", "external_link": "https://vimeo.com/123456", "chordpro": "{t: Z}"}],
        )
        songs, skipped = load_corpus(csv_path)
        assert songs == []
        assert skipped == 1

    def test_load_raises_on_missing_file(self, tmp_path: Path) -> None:
        from benchmarks.corpus import load_corpus

        with pytest.raises(FileNotFoundError):
            load_corpus(tmp_path / "nonexistent.csv")

    def test_load_raises_on_missing_columns(self, tmp_path: Path) -> None:
        from benchmarks.corpus import load_corpus

        csv_path = tmp_path / "songs.csv"
        with open(csv_path, "w") as f:
            f.write('title,chordpro\nA,"{t: A}"\n')
        with pytest.raises(ValueError, match="missing required column"):
            load_corpus(csv_path)


class TestParseYoutubeId:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://youtu.be/5qDYNTIJPsI", "5qDYNTIJPsI"),
            ("https://www.youtube.com/watch?v=5qDYNTIJPsI", "5qDYNTIJPsI"),
            ("https://youtube.com/watch?v=5qDYNTIJPsI&t=10s", "5qDYNTIJPsI"),
            ("http://youtu.be/5qDYNTIJPsI?si=token", "5qDYNTIJPsI"),
            ("https://www.youtube.com/embed/5qDYNTIJPsI", "5qDYNTIJPsI"),
            ("https://vimeo.com/123", None),
            ("", None),
            ("not-a-url", None),
        ],
    )
    def test_parse_youtube_id(self, url: str, expected: str | None) -> None:
        from benchmarks.corpus import parse_youtube_id

        assert parse_youtube_id(url) == expected

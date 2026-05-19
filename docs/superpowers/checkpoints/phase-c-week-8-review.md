# Phase C — Week 8 Architectural Review (Validation + F-004 + Cache) — ESSENTIAL

You are an Opus subagent doing architectural review of Phase C Week 8 (T60-T68: validation foundations, F-004 bass-note inversion, cache JSON serialization). This is the ONLY Week 8 stop. Three workstreams converge here:

- **F-004 closes a Codex review finding** — bass-stem chroma analysis is algorithmically delicate; wrong threshold = spurious slash chords; missing edge case = root-position fallback (acceptable but visible).
- **Cache wiring touches the orchestrator** — Pydantic round-trip across 8 stages; one schema not round-trippable breaks every nightly rerun.
- **Validation runner is the first time Titan output is *measured***. Errors in the mir_eval adapter or ground-truth parser silently inflate or deflate WCSR and mislead Henry's go/no-go at T70.

## What was supposed to be built

1. `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md` — Week 8 section (T60-T68 + Checkpoint 8).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`:
   - §374-408 (ChordRecognitionEngine) — bass-note mandate.
   - §749 (cache layout — 7 stage files + spec implies document/provenance).
   - §1099-1115 (StageConfidence aggregation) — interacts with cache when stages are reloaded.
   - §1532-1592 (Validation harness components) — divergence_ranker, validation_runner, audio_downloader shapes.
3. `.atomic-skills/reviews/2026-05-18-2116-phase-a-b-full-codebase-vs-spec-codex.md` — F-004 deferral text; what was promised for Phase C.
4. `titan_chordpro/engines/chord/chordino.py` (pre-T64 state, for comparison).

## What actually got built

```bash
ls -la benchmarks/ tests/unit/benchmarks/ tests/integration/test_cache_wiring.py tests/integration/test_validation_smoke.py
git log --oneline -- benchmarks/ titan_chordpro/engines/chord/ titan_chordpro/core/cache.py titan_chordpro/orchestrator.py
pytest tests/unit/benchmarks/ tests/unit/core/test_cache_serialization.py tests/unit/engines/chord/ -v
pytest tests/integration/test_cache_wiring.py tests/integration/test_validation_smoke.py tests/integration/test_chordino_smoke.py -v
```

Read in full:
- `benchmarks/corpus.py`
- `benchmarks/audio_downloader.py`
- `benchmarks/chordpro_parser.py`
- `benchmarks/metrics.py`
- `benchmarks/validation_runner.py`
- `benchmarks/divergence_ranker.py`
- `titan_chordpro/engines/chord/bass_chroma.py`
- `titan_chordpro/engines/chord/chordino.py` (post-T64)
- `titan_chordpro/core/cache.py` (post-T65)
- `titan_chordpro/orchestrator.py` (post-T66)
- `pyproject.toml` `[validation]` block + `corpus_full` marker

## Focus areas

### 1. F-004 bass-note correctness (T63 + T64)

- Does `bass_chroma.extract_bass_note` clamp `end` to actual file duration (the test asks 1.5-10.0 on a 2s file)?
- Is the 0.05s minimum-interval gate enforced BEFORE librosa is called (cheap rejection path)?
- Is the confidence formula `(max - median) / max` not `(max - mean) / max`? Median is more robust to pitched noise; mean would flatter the score.
- In `chordino.py`, is `_chord_root("F#m7")` correctly returning `"F#"` (not `"F"`)? The regex matches `[A-G][#b]?` greedily.
- When `bass_chroma` raises `FileNotFoundError` mid-detection (race: the bass stem was deleted by another process), does `detect()` log and continue with `bass_note=None`, or does it crash?
- Are bass-note emissions skipped for `bass_chroma` confidence below 0.5 even when a letter was returned (the function returns `(None, conf<0.5)` — but a callers-side belt-and-suspenders check is also reasonable)?

### 2. Cache serialization round-trip (T65 + T66)

- `dump_stage` writes via `<stage>.json.tmp` + `os.replace`. Is the tmp file under the SAME directory (cross-device rename fails otherwise)?
- `_run_or_cache_list` passes `[item.model_dump(mode="json") for item in result]`. If `result` is empty (silent.wav → no chords → []), does `load_stage` round-trip `[]` correctly back to `[]` via the `chords` stage?
- Does `cache_root=None` resolve to the SAME default in `cache_dir`, `stage_file`, `dump_stage`, AND `load_stage`? Verify by reading each function's default-handling.
- Does `transcribe(cache=True)` actually skip the second call to `factory.select_separation` on a cache hit, OR does it call factory and just skip `sep_engine.separate(...)`? (The integration test patches `factory.select_separation` — confirm the patch fires the expected `assert_not_called`.)
- Are `Stems`, `TranscriptionResult`, `AlignmentResult` exported from `core/schemas.py` and present in `core.schemas.__all__`? If not, the new orchestrator imports break the public surface contract.
- When the cache is corrupted (test scenario writes `{not json`), does `load_stage` return None silently? Does WARNING logging fire?

### 3. Validation runner — mir_eval adapter (T67)

- `to_mir_eval_chord` regex order: slash chords with quality come FIRST, then plain slash, then quality-only, then plain major. Reordering would map `Cm7/Eb` → `C:maj7/Eb` (wrong). Verify the order is intact.
- For chord symbols with bass: does `chord_events_to_intervals` produce `G:maj/B` (correct slash form) or `G:maj/B:maj` (wrong — should NOT pluralize the slash root with a quality)?
- Does `compute_wcsr_majmin` handle empty inputs (returns 0.0)? mir_eval would raise.
- Does the runner's `doc.sections[*].lines[*].chord_events` extraction handle both `LyricLine` and `InstrumentalLine` (the InstrumentalLine type may have `chord_events` directly on the line, not via lyrics)? Verify by reading `core/schemas.py` `Section.lines` union shape.
- When `extract_chord_sequence(song.chordpro)` returns `[]` (zero brackets in a chord-less verse), is the per-song result a `FailedMetric` (raised + caught) or an `SongMetric` with WCSR=0? Both are defensible; pick one and document it.

### 4. Ground-truth time alignment philosophy (T67)

- The plan assigns *equal-length intervals* across the chord sequence (no native timestamps). This means **chord ORDER matters, not exact alignment**. Is this called out in `chordpro_parser.py`'s docstring? Henry will read the source.
- Spec §1683 target is WCSR ≥ 70%. Equal-interval assignment can fudge alignment scoring — does the chosen scoring metric still discriminate "right chords wrong order" from "right chords right order"? (Answer: mir_eval's WCSR is duration-weighted; equal intervals + same labels gives a high score, equal intervals + different label OR different order gives a low score. Document this.)

### 5. yt-dlp wrapper — failure modes (T62)

- `_yt_dlp_download` writes to `target.with_suffix(".dl.%(ext)s")` then renames. What happens if yt-dlp produces MULTIPLE files (audio + thumbnail)? The current code globs `<stem>.dl.*` and takes the first sorted — could pick the wrong file if `.dl.jpg` sorts before `.dl.m4a`.
- Does the function handle the `[Errno 28] No space left on device` case gracefully (raise `DownloaderError` not bare `OSError`)?
- When `yt_dlp` is installed but the YouTube video is private / unavailable, what's the failure path? `yt_dlp.YoutubeDL().download([url])` raises a subclass of `DownloadError` — is that wrapped?

### 6. Severity ranking + report writing (T68)

- `Severity` value ordering: `CRITICAL=1, HIGH=2, MEDIUM=3, LOW=4, NEGLIGIBLE=5`. `sort` key `(severity.value, wcsr)` — worst severity first (lower value), then worst WCSR within severity. Verify ordering matches spec §1582 expectations.
- `write_report` filename: `top-divergences.md`. Spec §1592 names it the same. Confirm.
- Failures section is appended AFTER the top-N table. Verify failures aren't silently dropped if the test report had ONLY failures and no metrics.
- Does the report directory creation (`output_dir / day.isoformat()`) cope with `output_dir` not existing (`mkdir(parents=True)` should handle it)?

### 7. Phase B test surface — no regressions

- 320 tests passed at v0.1.0-b1. After T60-T68, count should be ≥ 424. Is it?
- Did any Phase B test get accidentally modified? `git diff v0.1.0-b1..HEAD -- tests/unit/` excluding new files should be empty (or only `test_chordino.py` — additive class).
- Does `pytest -q` complete in under 90 seconds (Phase B baseline ~60s; T60-T68 should add ~20s)?

### 8. Codex F-004 closure — verifiable

- Does `chordino.supports_inversions` now return `True`?
- Does the comment block above it cite Phase C T64 (not the Phase B deferral text)?
- Does the integration smoke test exercise a synthetic A2 bass tone and expect `letter == "A"`?

## What NOT to review

- Real-music F-004 accuracy — that's T70's manual review, not Week 8.
- Tier 2 metric thresholds — same, T70.
- README copy quality — T72 territory.
- Phase D scope — out of bounds.

## Output format

```
# Phase C Week 8 Architectural Review — ESSENTIAL

## Status
[Sound / Drift detected / Cache round-trip broken / mir_eval adapter broken / F-004 boundary issue]

## Findings
1. [File:line] — Issue — Severity (Critical/Significant/Minor)

## F-004 boundary
[Confirm — bass-stem chroma threshold + chord-root suppression intact]
[VIOLATION — describe file:line + observed vs expected]

## Cache round-trip
[Confirm — all 8 stages dump → load reciprocal across mock pipeline]
[BROKEN — list specific stage + reason (likely a Pydantic schema not round-trippable)]

## Validation runner correctness
[Confirm — mir_eval adapter + ground-truth parser produce reasonable WCSR on the smoke test]
[INFLATED/DEFLATED — describe]

## Continue to T69?
[Yes / Yes with caveats / NO — fix first]

## Notes for Henry
```

Max 800 words. This is the only Week 8 checkpoint with hard stops on F-004 AND cache AND mir_eval. Henry MUST receive the report before T69 starts.

---
date: 2026-05-19T11:10:00-03:00
topic: phase-c-plan-codex
artifact: docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md
skill: review-plan-with-codex
reviewer: gpt-5-codex
codex_version: codex-cli 0.130.0
final_verdict: needs_changes
counts_final: {blocker: 0, critical: 3, major: 3, minor: 0, nit: 0}
counts_blind: {blocker: 0, critical: 3, major: 2, minor: 0, nit: 0}
framing_delta: {dropped: 0, maintained: 5, emerged: 1}
schema_version: "1.0"
---

# Cross-Model Review — phase-c-plan-codex

## Pass 1 (blind)

---
verdict: needs_changes
counts: {blocker: 0, critical: 3, major: 2, minor: 0, nit: 0}
reviewer: gpt-5-codex
pass: blind
schema_version: "1.0"
---

## Summary
The plan has several executable contradictions that will break implementation before the nightly run, plus measurement bugs that make the validation report unreliable even if tests are made green. The biggest risks are in T66 cache wiring and T67 validation: the reference implementation imports a nonexistent schema, the cache-hit test contradicts eager engine selection, and validation extracts chord events from fields that the real document schema does not expose.

## Findings

### F-001 [critical] dependency-break — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:2111-2128

**Evidence:**
```python
from titan_chordpro.core.schemas import (
    AlignmentResult,
    BeatGrid,
    ChordEvent,
    ChordProDocument,
    EngineRegistry,
    InstrumentalLine,
    LyricLine,
    Metadata,
    Provenance,
    Section,
    StageConfidence,
    Stems,
    SyllableEvent,
    TimeStamp,
    TranscriptionResult,
    WordEvent,
    aggregate_stage_confidence,
)
```

**Claim:** T66 imports and uses `Stems`, but the current schema class is `StemSet`, so the reference implementation fails at import time.

**Impact:** `titan_chordpro.orchestrator` cannot import after T66, blocking the cache wiring task and every later task that imports `transcribe()`.

**Recommendation:** Replace `Stems` with `StemSet` throughout T66 and update the plan’s verification note to check `StemSet`, not `Stems`.

**Confidence:** high

---

### F-002 [critical] contradiction — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:2034-2050

**Evidence:**
```python
def test_cache_on_second_run_skips_engines(tmp_path: Path) -> None:
    """On a cache hit, engines must NOT be invoked. We assert this by
    patching factory.select_separation to a sentinel after the first run
    and verifying the second run does not hit it."""
    from titan_chordpro import factory
    from titan_chordpro.orchestrator import transcribe
    from tests.fixtures import silent_audio_path

    audio = silent_audio_path()
    # First run — populates the cache.
    transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)

    # Second run — patch factory.select_separation; if cache works, the
    # mock engine for separation must not be invoked.
    with patch.object(factory, "select_separation") as mock_sep:
        transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)
        mock_sep.assert_not_called()
```

**Claim:** The test requires no factory call on cache hit, but the T66 reference implementation eagerly calls every `factory.select_*` before any cache read.

**Impact:** T66’s own integration test fails; in real validation, a fully populated cache still requires engine dependencies to be importable/selectable, defeating the stated idempotent rerun goal.

**Recommendation:** Move engine selection into the cache-miss `compute` lambdas for each stage, and add an early `document.json` load path if the intended contract is a completely engine-free second run.

**Confidence:** high

---

### F-003 [critical] coverage-gap — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:2842-2848

**Evidence:**
```python
# Collect Titan chord events from doc.
titan_chords = []
for section in doc.sections:
    for line in section.lines:
        for evt in getattr(line, "chord_events", []) or []:
            titan_chords.append(evt)
est_intervals, est_labels = chord_events_to_intervals(titan_chords)
```

**Claim:** The validation runner looks for `line.chord_events`, but real `ChordProDocument` lines store lyric chords in `LyricLine.chord_markers[].chord` and instrumental chords in `InstrumentalLine.chords`.

**Impact:** Real validation reports will collect zero estimated chords, causing each real song to fail with “Titan produced no chord intervals”; the provided smoke test hides this by using a fake line with a non-schema `chord_events` attribute.

**Recommendation:** Extract chords from both real line shapes: `LyricLine.chord_markers[*].chord` and `InstrumentalLine.chords`, and rewrite the smoke test to build valid schema objects only.

**Confidence:** high

---

### F-004 [major] contradiction — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:2421

**Evidence:**
```markdown
Ground-truth time assignment: iasdermelinda ChordPro has no native timestamps. The runner uses the *downloaded audio duration* and assigns equal-length intervals across the chord sequence found in ground truth.
```

**Claim:** The stated scoring design uses downloaded audio duration, but the reference implementation derives duration from Titan’s last estimated chord interval instead.

**Impact:** WCSR is computed against a reference timeline squeezed or stretched to Titan’s output, so missing intros/outros, truncated chord detection, or failed late-song chords can be masked and the Phase C ≥70% gate becomes unreliable.

**Recommendation:** Probe the downloaded audio duration directly, or use the pipeline’s source duration if it is guaranteed to represent the full audio, and pass that duration into `to_intervals_labels()`.

**Confidence:** high

---

### F-005 [major] viability — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:921-925

**Evidence:**
```python
# Look for any extension match first (cache hit).
existing = sorted(base.glob(f"{youtube_id}.*"))
existing = [p for p in existing if p.suffix not in {".part", ".dl"}]
if existing:
    return existing[0]
```

**Claim:** The downloader cache-hit filter does not exclude yt-dlp temp names like `<id>.dl.m4a` because their suffix is `.m4a`, not `.dl`.

**Impact:** An interrupted or failed download can be treated as a valid cached audio file, causing later transcription/librosa steps to fail on partial audio or score against corrupted input.

**Recommendation:** Exclude paths whose name contains `.dl.` as well as `.part`, and write downloads into a separate temporary filename or directory before an atomic rename to the canonical cache path.

**Confidence:** high

## Questions (non-findings)

- docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:3416 — Should missing `CORPUS_URL` make the nightly job fail loudly instead of allowing a skipped validation run with no useful report artifact?

## Out of scope

- Writer profile changes
- Chordino subprocess boundary changes
- Fusion engine internals changes
- Tier 3 full-catalog review and deferred release/docs items
## Pass 2 (informed)

---
verdict: needs_changes
counts: {blocker: 0, critical: 3, major: 3, minor: 0, nit: 0}
reviewer: gpt-5-codex
pass: informed
schema_version: "1.0"
---

## Summary
The plan still has three implementation-breaking defects in the cache and validation workstreams, plus two measurement/cache correctness risks that would produce misleading reports or corrupted inputs. The informed pass adds one process blocker for execution: the plan does not include the required project-status/anchored-initiative preflight before T60 code edits.

## Findings

### F-001 [critical] dependency-break — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:2111

**Evidence:**
```python
from titan_chordpro.core.schemas import (
    AlignmentResult,
    BeatGrid,
    ChordEvent,
    ChordProDocument,
    EngineRegistry,
    InstrumentalLine,
    LyricLine,
    Metadata,
    Provenance,
    Section,
    StageConfidence,
    Stems,
    SyllableEvent,
    TimeStamp,
    TranscriptionResult,
    WordEvent,
    aggregate_stage_confidence,
)
```

**Claim:** T66 imports and uses `Stems`, but the current schema class is `StemSet`.

**Impact:** `titan_chordpro.orchestrator` cannot import after T66, blocking cache wiring and every later task that imports `transcribe()`.

**Recommendation:** Replace `Stems` with `StemSet` throughout T66 and update the plan’s verification note to check `StemSet`, not `Stems`.

**Confidence:** high

---

### F-002 [critical] contradiction — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:2034

**Evidence:**
```python
def test_cache_on_second_run_skips_engines(tmp_path: Path) -> None:
    """On a cache hit, engines must NOT be invoked. We assert this by
    patching factory.select_separation to a sentinel after the first run
    and verifying the second run does not hit it."""
    from titan_chordpro import factory
    from titan_chordpro.orchestrator import transcribe
    from tests.fixtures import silent_audio_path

    audio = silent_audio_path()
    # First run — populates the cache.
    transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)

    # Second run — patch factory.select_separation; if cache works, the
    # mock engine for separation must not be invoked.
    with patch.object(factory, "select_separation") as mock_sep:
        transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)
        mock_sep.assert_not_called()
```

**Claim:** The test requires no factory call on cache hit, but the T66 implementation eagerly calls every `factory.select_*` before any cache read.

**Impact:** T66’s own integration test fails; a fully populated cache still requires engine dependencies to be selectable, defeating idempotent reruns.

**Recommendation:** Move engine selection inside cache-miss computation for each stage, and add a `document.json` fast path if the intended contract is a completely engine-free second run.

**Confidence:** high

---

### F-003 [critical] coverage-gap — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:2842

**Evidence:**
```python
# Collect Titan chord events from doc.
titan_chords = []
for section in doc.sections:
    for line in section.lines:
        for evt in getattr(line, "chord_events", []) or []:
            titan_chords.append(evt)
est_intervals, est_labels = chord_events_to_intervals(titan_chords)
```

**Claim:** The validation runner reads nonexistent `line.chord_events`; real lines store lyric chords in `LyricLine.chord_markers[*].chord` and instrumental chords in `InstrumentalLine.chords`.

**Impact:** Real validation collects zero estimated chords, causing songs to fail with “Titan produced no chord intervals”; the smoke test hides this with a fake non-schema line.

**Recommendation:** Extract chords from both real line shapes and rewrite the smoke test to construct valid `LyricLine` and `InstrumentalLine` schema objects.

**Confidence:** high

---

### F-004 [major] contradiction — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:2421

**Evidence:**
```markdown
Ground-truth time assignment: iasdermelinda ChordPro has no native timestamps. The runner uses the *downloaded audio duration* and assigns equal-length intervals across the chord sequence found in ground truth.
```

**Claim:** The stated scoring design uses downloaded audio duration, but the implementation derives duration from Titan’s last estimated chord interval.

**Impact:** WCSR is computed against a reference timeline squeezed to Titan’s output, so missing intros/outros or truncated late-song detection can be masked and the ≥70% Phase C gate becomes unreliable.

**Recommendation:** Probe the downloaded audio duration directly, or use the pipeline’s source duration if guaranteed to represent the full audio, and pass that duration into `to_intervals_labels()`.

**Confidence:** high

---

### F-005 [major] viability — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:921

**Evidence:**
```python
# Look for any extension match first (cache hit).
existing = sorted(base.glob(f"{youtube_id}.*"))
existing = [p for p in existing if p.suffix not in {".part", ".dl"}]
if existing:
    return existing[0]
```

**Claim:** The downloader cache-hit filter does not exclude yt-dlp temp names like `<id>.dl.m4a` because their suffix is `.m4a`, not `.dl`.

**Impact:** An interrupted or failed download can be treated as valid cached audio, causing later transcription/librosa steps to fail on partial audio or score against corrupted input.

**Recommendation:** Exclude paths whose name contains `.dl.` and `.part`, and write downloads into a separate temporary filename or directory before an atomic rename to the canonical cache path.

**Confidence:** high

---

### F-006 [major] ordering — docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:45

**Evidence:**
```markdown
| 4 | Plan reviewer | **Codex cross-model review** | Matches Phase A/B discipline. Run `atomic-skills:review-plan-with-codex` on this draft BEFORE creating the initiative + executing T60. |
```

**Claim:** The plan has no required preflight task to load project status and activate a matching anchored initiative before T60 code edits.

**Impact:** Executing T60 as written violates the repository hard gate: no implementation may land without an active `.atomic-skills/initiatives/<slug>.md` initiative and matching branch.

**Recommendation:** Add a mandatory T59 preflight before T60: read `.atomic-skills/PROJECT-STATUS.md`, use `atomic-skills:project-status`, create or activate the Phase C initiative, verify the branch matches, then proceed to T60.

**Confidence:** high

## Questions (non-findings)

- docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md:3416 — Should missing `CORPUS_URL` make the nightly job fail loudly instead of allowing a skipped validation run with no useful report artifact?

## Out of scope

- Writer profile changes
- Chordino subprocess boundary changes
- Fusion engine internals changes
- Tier 3 full-catalog review and deferred release/docs items

## Pass 2 reconciliation

### Dropped from blind pass

- _(none)_

### Maintained

- F-001-blind → F-001-final [critical] — same
- F-002-blind → F-002-final [critical] — same
- F-003-blind → F-003-final [critical] — same
- F-004-blind → F-004-final [major] — same
- F-005-blind → F-005-final [major] — same

### Emerged

- F-006-final [major] ordering — emerged: the external hard-gate constraint requires project-status loading and an active anchored initiative before implementation, but the plan has no pre-T60 task enforcing it.
## Briefings used

<details>
<summary>Pass 1 briefing</summary>

Briefing file: `/tmp/codex-briefing-pass1-20260519-110508.md` (157KB; plan body inlined). Frame (non-artifact) was ~5KB / 1262 tokens — mandatory output-template scaffolding, no narrative intent.

</details>

<details>
<summary>Pass 2 briefing</summary>

Briefing file: `/tmp/codex-briefing-pass2-20260519-110508.md` (168KB; Pass 1 output + 10 verifiable constraints appended).

External constraints supplied to Codex Pass 2:
- Python requires-python >= 3.11 (pyproject.toml:12)
- Core schema class names: StemSet (NOT Stems), TranscriptionResult, AlignmentResult, ChordMarker, LyricLine, InstrumentalLine
- LyricLine.chord_markers: list[ChordMarker] (line 186); ChordMarker.chord: ChordEvent (line 170); InstrumentalLine.chords: list[ChordEvent] (line 196). No `chord_events` attribute on any Line subtype.
- transcribe() already has cache: bool = False (orchestrator.py:42)
- chord_engine.detect(audio, bass_stem=stems.bass) wired at orchestrator.py:97
- librosa>=0.10 in [mac] (line 42) and [cuda] (line 56) extras
- tests/fixtures/ has silent.wav + tone_a4_2s.wav but no __init__.py
- HARD-GATE: CLAUDE.md requires anchored initiative + matching branch before code edits
- Phase B baseline: 320 tests pass / 10 skipped at v0.1.0-b1
- Spec §749 cache filename `chords.json` (not `chord_recognition.json`); orchestrator stage name mapping defined in plan playbook

</details>

## Fixes applied in this session

<!-- Append-only. Triagem step adds lines here as user approves/skips. -->

- **F-001 [critical] dependency-break** — APPLIED: T66 RI import block now uses `StemSet` (the real class name at `core/schemas.py:139`); verification command at T66 Step 5 updated to import `StemSet`.
- **F-002 [critical] contradiction** — APPLIED: T66 RI now opens with a document.json fast path that returns engine-free on cache hit; engine selection moved into a lazy `_engine(name, **extra)` helper so each `factory.select_*` runs at most once and only on cache miss. The cache-hit test (`test_cache_on_second_run_skips_engines`) is now satisfiable.
- **F-003 [critical] coverage-gap** — APPLIED: T67 `validation_runner.run_validation` now extracts chords from `LyricLine.chord_markers[*].chord` and `InstrumentalLine.chords` (the real schema fields). T67 smoke test rebuilt to use real `ChordMarker` + `LyricLine` + `Section` objects, removing the `FakeLine.chord_events` workaround that was hiding the bug.
- **F-004 [major] contradiction** — APPLIED: T67 `validation_runner.run_validation` now probes duration via `soundfile.info(audio).duration` (matching the plan's stated design) instead of deriving from Titan's last interval. T67 smoke test writes a 4s silent WAV so the probe has something real to read.
- **F-005 [major] viability** — APPLIED: T62 `download_audio` now uses a `_is_complete_audio(path)` helper that excludes both `*.part` and any path with `.dl.` in its name (yt-dlp interim files). New test `test_ignores_partial_dl_files_on_cache_lookup` added; expected pytest count for T62 bumped from 9 to 10.
- **F-006 [major] ordering** — APPLIED: new "Pre-execution gate" section added between the Task Index and Week 8, introducing **T-pre** (project-status check + initiative flip to `status: active` + branch verification + metadata-only commit). Task index updated from "14 tasks" to "15 tasks (T-pre + T60..T73)". DO-NOT-PROCEED guard added at the end of T-pre.

Summary: **6 applied / 0 skipped / 0 deferred.** Plan grew from 4032 to 4215 lines.

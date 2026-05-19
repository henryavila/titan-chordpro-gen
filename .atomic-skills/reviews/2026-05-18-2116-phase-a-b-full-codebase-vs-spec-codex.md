---
date: 2026-05-18T21:16:00-03:00
topic: phase-a-b-full-codebase-vs-spec-codex
artifact: HEAD (Phase A + B complete, v0.1.0-a0 + v0.1.0-b0 + F-001..F-004 fixes)
skill: review-code-with-codex
reviewer: gpt-5-codex
codex_version: 0.130.0
final_verdict: reject
counts_final: {blocker: 0, critical: 4, major: 5, minor: 0, nit: 0}
counts_blind: {blocker: 1, critical: 4, major: 2, minor: 0, nit: 0}
framing_delta: {dropped: 1, maintained: 6, emerged: 3}
schema_version: "1.0"
---

# Cross-Model Review — phase-a-b-full-codebase-vs-spec-codex

## Pass 1 (blind)

---
verdict: reject
counts: {blocker: 1, critical: 4, major: 2, minor: 0, nit: 0}
reviewer: gpt-5-codex
pass: blind
schema_version: "1.0"
---

## Summary
The package diverges from the v0.1 contract in user-visible and boundary-critical paths. The public API specified by the design is not exported, normal production runs can silently substitute deterministic mocks, line-level chord placement duplicates section chords across every lyric line, Chordino does not implement the promised bass-note inversion path, and the GPL subprocess boundary is not enforced by this package.

Several requirements are also missing or partially wired: `pt-BR`, shown in the public API example, selects the mock syllabifier even when the Portuguese engine is available, and pipeline provenance never includes the mandated per-stage confidence aggregates.

## Findings

### F-001 [blocker] GPL boundary integrity — titan_chordpro/engines/chord/chordino.py:31-41

**Evidence:**
```py
def _load_extractor() -> Any:
    try:
        from chord_extractor.extractors import Chordino
    except ImportError as exc:
        raise EngineUnavailableError(
            "chord_extractor (with Chordino VAMP plugin) is not installed; "
            "run scripts/install_vamp.sh and see docs/setup-vamp.md",
            engine="chordino",
            cause=exc,
        ) from exc
    return Chordino()
```

**Claim:** Chordino is instantiated through an in-process Python object, so this package does not enforce the required separate subprocess boundary for the GPL VAMP plugin.

**Impact:** GPL isolation depends on undocumented behavior inside `chord_extractor`; if that dependency loads or links the VAMP plugin in-process, the MIT wheel crosses the process boundary the design requires and the distribution cannot be certified as GPL-isolated.

**Recommendation:** Replace the wrapper call with an explicit subprocess adapter owned by this package, e.g. invoke `sonic-annotator`/Chordino out of process and parse its output; do not instantiate Chordino via Python imports in the runtime path.

**Confidence:** medium

---

### F-002 [critical] Public API — titan_chordpro/__init__.py:1-3

**Evidence:**
```py
from titan_chordpro.version import __version__

__all__ = ["__version__"]
```

**Claim:** `from titan_chordpro import transcribe, ChordProDocument` fails because neither symbol is imported or exported at package root.

**Impact:** The documented library API is unusable for normal consumers; users must know internal module paths despite the spec defining root-level imports.

**Recommendation:** Import and export `transcribe` from `orchestrator.py` and `ChordProDocument` from `core.schemas` in `titan_chordpro/__init__.py`.

**Confidence:** high

---

### F-003 [critical] Mock-vs-real parity — titan_chordpro/factory.py:65-81

**Evidence:**
```py
    if force_mock or not _have_module("audio_separator"):
        _record(
            "separation",
            "mock",
            False,
            "audio_separator not installed" if not force_mock else "force_mock",
        )
        return MockSourceSeparationEngine()
    try:
        from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

        engine = HtdemucsEngine(backend=backend)
        _record("separation", "htdemucs_ft", True, "audio_separator importable")
        return engine
    except EngineUnavailableError as exc:
        _record("separation", "mock", False, f"htdemucs init failed: {exc}")
        return MockSourceSeparationEngine()
```

**Claim:** With default `force_mock=False`, missing or failed real engines silently return deterministic mocks instead of failing fast.

**Impact:** A production `transcribe(song.wav)` on an underconfigured host can emit a plausible `.chordpro` built from hardcoded mock words/chords rather than the input audio, causing silent data corruption.

**Recommendation:** Only return mocks when `force_mock=True`; otherwise raise `EngineUnavailableError` with stage context when a required engine dependency or initialization is unavailable.

**Confidence:** high

---

### F-004 [critical] Chord placement — titan_chordpro/orchestrator.py:190-204

**Evidence:**
```py
            line_words = line.word_alignments
            global_indices = [word_index.get(id(w), -1) for w in line_words]
            line_syls = [
                s for gi in global_indices if gi >= 0 for s in syl_by_global_word.get(gi, [])
            ]
            line_chords = [c for c in chords if _chord_in_span(c, section.timestamp)]
            placed, _orphans = placer.place_chords_in_line(
                line_text=line.text,
                words=line_words,
                syllables=line_syls,
                chords_in_line=line_chords,
                beat_grid=beats,
                melismas=melismas,
                language=language,
            )
```

**Claim:** Every lyric line receives all chords in the enclosing section because `line_chords` is filtered by `section.timestamp`, not the line’s word/syllable span.

**Impact:** Any verse/chorus with multiple lyric lines can duplicate the same chord progression onto each line, producing incorrect ChordPro output even when upstream recognition is correct.

**Recommendation:** Compute each lyric line’s time span from `line_words` and pass only chords overlapping that line; route leftover/orphan chords into sibling `InstrumentalLine`s.

**Confidence:** high

---

### F-005 [critical] Chord engine spec divergence — titan_chordpro/engines/chord/chordino.py:93-98

**Evidence:**
```py
    @property
    def supports_inversions(self) -> bool:
        # Chordino's chord-class output excludes inversions; we synthesize
        # slash chords only when a bass stem is provided AND a bass-detection
        # pass is run (Phase C — out of scope here).
        return False
```

**Claim:** The v0.1 Chordino engine reports no inversion support and does not derive slash-chord bass notes from the provided bass stem.

**Impact:** Required v0.1 slash-chord cases such as `F/A`, `G/B`, and `C/E` collapse to root-position symbols, so the output loses harmonic information the design explicitly requires for the PT-BR corpus.

**Recommendation:** Implement bass-stem-derived `bass_note` assignment in Chordino v0.1 and report `supports_inversions=True` when that path is active.

**Confidence:** high

---

### F-006 [major] Language selection — titan_chordpro/factory.py:183-229

**Evidence:**
```py
def select_syllabification(
    language: str = "pt",
    *,
    force_mock: bool = False,
    **_ignored: Any,
) -> SyllabificationEngine:
    if language == "pt":
        if force_mock or not _have_module("gruut"):
            _record(
                "syllabification",
                "mock",
                False,
                "gruut not installed" if not force_mock else "force_mock",
            )
            return MockSyllabificationEngine(language=language)
        try:
            from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

            pt_engine: SyllabificationEngine = PortugueseSyllabifierEngine()
            _record("syllabification", "gruut_pt", True, "gruut importable")
            return pt_engine
        except EngineUnavailableError as exc:
            _record("syllabification", "mock", False, f"gruut_pt init failed: {exc}")
            return MockSyllabificationEngine(language=language)

    if language == "en":
        if force_mock or not _have_module("g2p_en"):
            _record(
                "syllabification",
                "mock",
                False,
                "g2p_en not installed" if not force_mock else "force_mock",
            )
            return MockSyllabificationEngine(language=language)
        try:
            from titan_chordpro.engines.lang.english import EnglishSyllabifierEngine

            en_engine: SyllabificationEngine = EnglishSyllabifierEngine()
            _record("syllabification", "g2p_en", True, "g2p_en importable")
            return en_engine
        except EngineUnavailableError as exc:
            _record("syllabification", "mock", False, f"g2p_en init failed: {exc}")
            return MockSyllabificationEngine(language=language)

    # Unknown language → always mock with passed language for parent tracking.
    _record("syllabification", "mock", False, f"unknown language {language!r}; using mock")
    return MockSyllabificationEngine(language=language)
```

**Claim:** The specified `language="pt-BR"` path is treated as unknown and always selects `MockSyllabificationEngine`.

**Impact:** Portuguese real-engine syllabification is bypassed for the documented public API example, degrading stress and syllable placement while provenance labels the stage as mock.

**Recommendation:** Normalize language tags before selection, mapping `pt-BR`/`pt_BR`/`pt` to the Portuguese engine and `en-*`/`en` to the English engine.

**Confidence:** high

---

### F-007 [major] Provenance — titan_chordpro/orchestrator.py:108-121

**Evidence:**
```py
    provenance = Provenance(
        titan_version=_titan_version(),
        audio_id=audio_id,
        engines=EngineRegistry(
            separation=sep_engine.info,
            transcription=trans_engine.info,
            alignment=align_engine.info,
            chord_recognition=chord_engine.info,
            beat_tracking=beat_engine.info,
            syllabification=syll_engine.info,
        ),
        started_at=started_at,
        completed_at=completed_at,
        confidence=[],
    )
```

**Claim:** `Provenance.confidence` is always empty instead of containing the mandated per-stage `StageConfidence` aggregates.

**Impact:** Rendered headers omit all `{meta: titan_confidence_* ...}` directives, downstream audit tooling cannot identify low-confidence stages, and the design’s “provenance everywhere” contract is not met.

**Recommendation:** Aggregate stage confidence for separation, transcription, alignment, chord recognition, beat tracking, syllabification, and fusion before constructing `Provenance`.

**Confidence:** high

## Questions (non-findings)

- titan_chordpro/orchestrator.py:42 — `output_profile` is accepted by `transcribe()` but not used until callers render/write; should invalid profiles fail during transcription or only during serialization?

## Out of scope

- Items explicitly marked v0.2+, Phase C/D, or deferred in the design spec.
- ChordPro visual styling differences beyond mandated directives and chord syntax.

## Pass 2 (informed)

---
verdict: reject
counts: {blocker: 0, critical: 4, major: 5, minor: 0, nit: 0}
reviewer: gpt-5-codex
pass: informed
schema_version: "1.0"
---

## Summary
The informed pass drops the GPL-boundary finding: the revealed constraint establishes that `chord_extractor` shells out to the VAMP host and does not load Chordino GPL code into this Python process. The remaining critical issues still make the package diverge from the v0.1 contract in normal library use and generated output correctness.

The implementation does not export the documented root API, silently substitutes mocks on underconfigured real runs, duplicates section-level chords across lyric lines, and fails the required Chordino bass-note inversion contract. Additional public API, backend selection, provenance, language-tag, and mock parity gaps remain.

## Findings

### F-001 [critical] Public API — titan_chordpro/__init__.py:1

**Evidence:**
```py
from titan_chordpro.version import __version__

__all__ = ["__version__"]
```

Spec:
```md
from titan_chordpro import transcribe, ChordProDocument
```

**Claim:** The documented root import `from titan_chordpro import transcribe, ChordProDocument` fails because neither symbol is imported or exported at package root.

**Impact:** The specified library API is unusable for consumers; callers must discover internal module paths despite the spec defining root-level imports.

**Recommendation:** Re-export `transcribe` and `ChordProDocument` from `titan_chordpro/__init__.py`.

**Confidence:** high

---

### F-002 [critical] Mock-vs-real parity / fail-fast — titan_chordpro/factory.py:65

**Evidence:**
```py
if force_mock or not _have_module("audio_separator"):
    _record(
        "separation",
        "mock",
        False,
        "audio_separator not installed" if not force_mock else "force_mock",
    )
    return MockSourceSeparationEngine()
```

Same pattern exists for transcription, alignment, chord recognition, beat tracking, and syllabification.

Spec:
```md
1. **Fail-fast**: stage falha → pipeline para. Sem partial outputs silenciosamente errados.
```

**Claim:** With default `force_mock=False`, missing or failed real engine dependencies silently return deterministic mocks instead of raising a stage-specific configuration error.

**Impact:** A production `transcribe(song.wav)` on an underconfigured host can emit plausible ChordPro output based on hardcoded mock words/chords, not the input audio.

**Recommendation:** Only return mocks when `force_mock=True` or `--device mock`; otherwise raise `EngineUnavailableError` with stage and engine context.

**Confidence:** high

---

### F-003 [critical] Chord placement — titan_chordpro/orchestrator.py:195

**Evidence:**
```py
line_chords = [c for c in chords if _chord_in_span(c, section.timestamp)]
placed, _orphans = placer.place_chords_in_line(
    line_text=line.text,
    words=line_words,
    syllables=line_syls,
    chords_in_line=line_chords,
```

**Claim:** Every lyric line receives all chords in the enclosing section because chord filtering uses `section.timestamp`, not the individual line’s word/syllable span.

**Impact:** Any verse or chorus with multiple lyric lines can duplicate the same chord progression onto each line, producing incorrect ChordPro even when upstream recognition is correct.

**Recommendation:** Compute a per-line time span from `line_words` or `line_syls`, pass only overlapping chords to that line, and preserve unmatched chords as instrumental/orphan material.

**Confidence:** high

---

### F-004 [critical] Chord engine spec divergence — titan_chordpro/engines/chord/chordino.py:94

**Evidence:**
```py
@property
def supports_inversions(self) -> bool:
    return False
```

```py
ChordEvent(
    symbol=symbol,
    timestamp=TimeStamp(start=start, end=end),
    bass_note=None,
    confidence=1.0,
    source_engine="chordino",
)
```

Spec:
```md
**v0.1:** `engines/chord/chordino.py` (vocab=`majmin` + bass note → derive inversions).
```

**Claim:** The v0.1 Chordino engine reports no inversion support and always emits `bass_note=None`, even when `bass_stem` is provided.

**Impact:** Required slash-chord cases such as `F/A`, `G/B`, and `C/E` collapse to root-position symbols, losing harmonic information the v0.1 PT-BR corpus requires.

**Recommendation:** Implement bass-stem-derived `bass_note` assignment for Chordino v0.1 and report inversion support when that path is active.

**Confidence:** high

---

### F-005 [major] Language selection — titan_chordpro/factory.py:183

**Evidence:**
```py
def select_syllabification(
    language: str = "pt",
    *,
    force_mock: bool = False,
    **_ignored: Any,
) -> SyllabificationEngine:
    if language == "pt":
        ...
    if language == "en":
        ...
    _record("syllabification", "mock", False, f"unknown language {language!r}; using mock")
    return MockSyllabificationEngine(language=language)
```

Spec:
```md
language="pt-BR",
```

**Claim:** The documented `language="pt-BR"` path is treated as unknown and selects the mock syllabifier even when the Portuguese engine is available.

**Impact:** The public API example bypasses real PT-BR syllabification, degrading stress and syllable placement for the primary corpus language.

**Recommendation:** Normalize language tags before selection, mapping `pt`, `pt-BR`, and `pt_BR` to the Portuguese engine, and similarly handling `en-*`.

**Confidence:** high

---

### F-006 [major] Provenance — titan_chordpro/orchestrator.py:108

**Evidence:**
```py
provenance = Provenance(
    titan_version=_titan_version(),
    audio_id=audio_id,
    engines=EngineRegistry(...),
    started_at=started_at,
    completed_at=completed_at,
    confidence=[],
)
```

Spec:
```md
`Provenance.confidence: list[StageConfidence]` agrega per-stage:
```

```md
{meta: titan_confidence_chord_recognition 0.92}
```

**Claim:** `Provenance.confidence` is always empty instead of containing the mandated per-stage `StageConfidence` aggregates.

**Impact:** Rendered output omits all `{meta: titan_confidence_* ...}` directives, and downstream audit tooling cannot identify low-confidence stages.

**Recommendation:** Aggregate confidence for separation, transcription, alignment, chord recognition, beat tracking, syllabification, and fusion before constructing `Provenance`.

**Confidence:** high

---

### F-007 [major] Public API overrides — titan_chordpro/orchestrator.py:39

**Evidence:**
```py
def transcribe(
    audio: Path,
    language: str | None = None,
    output_profile: str = "inline_slash",
    keep_stems: bool = False,
    cache: bool = False,
    force_mock: bool = False,
    backend: str | None = None,
) -> ChordProDocument:
```

Spec:
```md
def transcribe(
    audio: Path,
    language: str | None = None,
    output_profile: str = 'inline_slash',
    keep_stems: bool = False,
    cache: bool = False,
    **engine_overrides,
) -> ChordProDocument:
```

**Claim:** The implementation removed `**engine_overrides`, so the documented override example such as `transcription_engine="mlx-whisper"` raises `TypeError`.

**Impact:** Users cannot select engines through the public API shape the spec defines; any documented engine override fails before factory selection runs.

**Recommendation:** Restore `**engine_overrides` in `transcribe()` and route supported override keys through factory selection with validation for unknown keys.

**Confidence:** high

---

### F-008 [major] Backend selection — titan_chordpro/core/hardware.py:26

**Evidence:**
```py
def detect_backend(prefer: str | None = None) -> Backend:
    """
    If the preferred backend is not actually available, the call
    falls back to autodetect (does NOT raise). Unknown strings are
    silently ignored (also fall back to autodetect).
    """
```

```py
if prefer in _VALID_BACKENDS:
    ...
    _log.info("preferred backend %r unavailable; using %r", prefer, auto)

_cached_backend = auto
return auto
```

**Claim:** Explicit backend requests such as `--device cuda` or `backend="mps"` silently run on another backend when the requested one is unavailable.

**Impact:** Dual-path behavior is misleading and hard to diagnose: a CUDA-specific run can actually execute on MPS or CPU while provenance reports the substituted backend after the fact.

**Recommendation:** Treat unavailable explicit backend preferences as `EngineUnavailableError` or `TitanConfigError`; reserve autodetection fallback for `backend=None` / `--device auto`.

**Confidence:** high

---

### F-009 [major] Mock-vs-real parity — titan_chordpro/mocks.py:181

**Evidence:**
```py
def syllabify(
    self,
    words: list[WordEvent],
    phonemes: list[PhonemeEvent] | None = None,
) -> list[SyllableEvent]:
    result: list[SyllableEvent] = []
    for word in words:
        result.extend(syllabify_word_orthographic(word, self._language))
    return result
```

Called helper emits syllables with a fixed parent index:
```py
SyllableEvent(
    text=text[cs:ce],
    timestamp=TimeStamp(start=t_start, end=t_end),
    is_stressed=False,
    parent_word_idx=0,
)
```

**Claim:** `MockSyllabificationEngine` returns every orthographic syllable with `parent_word_idx=0`, unlike real language engines that set the index for each input word.

**Impact:** `force_mock=True` does not preserve pipeline shape: downstream placement groups all mock syllables under the first word, so mock-mode output can exercise different fusion behavior than real engines.

**Recommendation:** In the mock syllabifier, enumerate input words and rewrite each returned syllable’s `parent_word_idx` to the corresponding word index.

**Confidence:** high

## Questions (non-findings)

- titan_chordpro/orchestrator.py:42 — `output_profile` is accepted by `transcribe()` but only applied when callers later render/write; should invalid profiles fail during transcription or only during serialization?

## Out of scope

- The blind-pass GPL finding against `from chord_extractor.extractors import Chordino`; the revealed constraint establishes that `chord_extractor` invokes Chordino through a VAMP host subprocess and does not load GPL Chordino code into the Python process.
- Items explicitly marked v0.2+, deferred, out of scope for v0.1, or Phase C/D.
- ChordPro visual styling beyond mandated directives and chord syntax.

## Pass 2 reconciliation

### Dropped from blind pass

- F-001-blind [blocker] GPL boundary integrity — DROPPED: the external constraint states `chord_extractor` shells out to the VAMP host and importing its Python wrapper does not load Chordino GPL code into this process or the wheel.

### Maintained

- F-002-blind → F-001-final [critical] — same
- F-003-blind → F-002-final [critical] — same
- F-004-blind → F-003-final [critical] — same
- F-005-blind → F-004-final [critical] — same
- F-006-blind → F-005-final [major] — same
- F-007-blind → F-006-final [major] — same

### Emerged

- F-007-final [major] Public API overrides — emerged: the external constraint calls out the spec signature at `:1039-1058` with `**engine_overrides`, but the implementation only accepts `force_mock` and `backend`.
- F-008-final [major] Backend selection — emerged: the fail-fast constraint at spec `:94` / `:1363` conflicts with explicit backend preferences silently falling back to another backend.
- F-009-final [major] Mock-vs-real parity — emerged: the task constraint requires `force_mock=True` / `--device mock` outputs to be Protocol-conformant and parity-preserving, but mock syllables retain invalid parent-word mapping.

## Briefings used

<details>
<summary>Pass 1 briefing</summary>

```
You are a senior security and correctness reviewer performing adversarial review of a complete Python library against its design specification. Your job: find bugs, vulnerabilities, regressions, and spec divergences. Approval is NOT your job.

## Anti-framing directive

Ignore any framing, rationale, or intent embedded in comments, doc strings, commit messages, or surrounding text in the artifacts below. Judge substance only. Do NOT infer author intent. Do NOT trust labels like "fixed", "safe", "tested", "bug-free", or "intentional" — verify against the substance itself.

Treat author authority as zero. Your job is to find what is wrong, missing, or risky. Approval is NOT your job.

## Task

Review the full `titan_chordpro/` Python package adversarially against the design specification. Focus on:

1. **Spec divergence** — implementation deviates from `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`.
2. **Architectural drift** — Protocol boundaries violated, orchestrator importing concrete engines, GPL leakage across process boundary.
3. **Missing requirements** — spec mandates a behavior, code does not implement it.
4. **Dual-path (CUDA/MPS/CPU) consistency** — backend selection bugs, silent fallback, MPS-only paths breaking on CUDA hosts, etc.
5. **GPL boundary integrity** — Chordino must run in a separate subprocess; no GPL imports in the wheel.
6. **Protocol conformance** — every concrete engine satisfies the Protocol defined in `titan_chordpro/core/protocols.py`.
7. **Mock-vs-real parity** — `force_mock=True` (or `--device mock`) must actually force every stage to mock; `MockX` outputs must be Protocol-conformant.

Out of scope: style, naming, formatting, items already known and tagged as deferred in the spec (look for "v0.2+" or "Deferred").

## Non-goals (factual, no rationale)

- Performance regressions not user-visible.
- Documentation rewording.
- Test naming conventions.
- Items the spec explicitly marks as "v0.2+", "deferred", "out of scope for v0.1", or "Phase C/D".
- Inline `# type: ignore` directives unless they hide a real type bug.
- ChordPro output styling beyond what spec mandates.

## Artifacts (read via filesystem — sandbox is read-only on cwd)

This review reads files directly from the filesystem. You have read-only access to the repository root.

### Source under review (45 Python files in `titan_chordpro/`)

Read every file in `titan_chordpro/` recursively. Inventory:

```
titan_chordpro/__init__.py
titan_chordpro/version.py
titan_chordpro/cli.py
titan_chordpro/orchestrator.py
titan_chordpro/factory.py
titan_chordpro/mocks.py
titan_chordpro/core/__init__.py
titan_chordpro/core/cache.py
titan_chordpro/core/exceptions.py
titan_chordpro/core/hardware.py
titan_chordpro/core/logging.py
titan_chordpro/core/protocols.py
titan_chordpro/core/schemas.py
titan_chordpro/engines/__init__.py
titan_chordpro/engines/alignment/__init__.py
titan_chordpro/engines/alignment/torchaudio_align.py
titan_chordpro/engines/beat/__init__.py
titan_chordpro/engines/beat/beatthis.py
titan_chordpro/engines/chord/__init__.py
titan_chordpro/engines/chord/chordino.py
titan_chordpro/engines/lang/__init__.py
titan_chordpro/engines/lang/english.py
titan_chordpro/engines/lang/portuguese.py
titan_chordpro/engines/separation/__init__.py
titan_chordpro/engines/separation/htdemucs.py
titan_chordpro/engines/transcription/__init__.py
titan_chordpro/engines/transcription/whisper_cpp.py
titan_chordpro/fusion/__init__.py
titan_chordpro/fusion/beat_snap.py
titan_chordpro/fusion/melisma.py
titan_chordpro/fusion/onset_fusion.py
titan_chordpro/fusion/placer.py
titan_chordpro/fusion/sectioner.py
titan_chordpro/fusion/stress.py
titan_chordpro/fusion/syllabifier.py
titan_chordpro/writer/__init__.py
titan_chordpro/writer/document.py
titan_chordpro/writer/serializer.py
titan_chordpro/writer/profiles/__init__.py
titan_chordpro/writer/profiles/base.py
titan_chordpro/writer/profiles/chordpro_ref.py
titan_chordpro/writer/profiles/inline_slash.py
titan_chordpro/writer/profiles/onsong.py
titan_chordpro/writer/profiles/propresenter.py
titan_chordpro/writer/profiles/songbookpro.py
```

### Test files (~30 files, read selectively to verify behavior)

`tests/unit/...` and `tests/integration/...` — read tests for any module you flag as buggy to check whether the bug is already covered or escapes coverage.

### Authoritative spec (1 file, MANDATORY READ)

`docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` — 1807 lines. This is the contract. Implementation deviations from this spec are findings.

### Implementation plans (READ ON DEMAND for context only)

- `docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md` — Phase A (pure-Python core, mocks, fusion, CLI, writer, schemas, protocols). 7342 lines.
- `docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md` — Phase B (real ML engines: separation, transcription, alignment, chord, beat, syllabification). 4420 lines.

The plans are not the source of truth — the spec is. If plan and spec conflict, spec wins, and that is itself a finding.

### Build/config

- `pyproject.toml` — package metadata, extras `[mac]`, `[cuda]`, `[dev]`.
- `.github/workflows/ci.yml` — CI matrix.
- `scripts/install_vamp.sh` — VAMP plugin installer for Chordino host.

## What to look for (attack surfaces)

1. **Correctness**: logic bugs, off-by-one, null/undefined, type confusion.
2. **Race conditions**: shared state, async ordering, missing locks.
3. **Security**: path traversal, command injection in subprocess calls, secrets exposure.
4. **Data integrity**: silent truncation, lost writes, dropped errors.
5. **Error handling**: silently swallowed failures, generic `except Exception:` masking bugs.
6. **Backward compatibility**: Protocol contract changes that break Phase A mocks.
7. **Performance**: algorithmic regressions, O(n²) over song duration, repeated model loads.
8. **Test gaps**: new code paths without corresponding tests.
9. **Observability**: failures without logging.
10. **Spec compliance**: every spec contract honored (`{title}`, `{key}`, `[chord]` syntax, profile renderings, Protocol shapes).
11. **GPL boundary**: any direct import of GPL code into Python wheel; missing subprocess isolation for Chordino.
12. **Hardware path**: `core/hardware.py` returns `mps` / `cuda` / `cpu` correctly; engines respect the returned backend on both Apple Silicon and CUDA hosts.

## Finding bar (mandatory for EACH finding)

Every finding MUST answer all four:
1. WHAT fails (which input causes which incorrect behavior — be specific).
2. WHY (mechanism — not "this looks wrong").
3. IMPACT — concrete consequence (data loss? auth bypass? user-visible bug? unimplementable design decision?).
4. RECOMMENDATION — specific action.

If a finding cannot answer all four: DROP IT.

Every finding MUST cite `file:line` from the artifact. No line cite = drop.

## Severity calibration

- **blocker**: production data loss, security breach, makes feature impossible, GPL leak in the wheel.
- **critical**: bug that hits users in normal use, major regression, dual-path silently broken.
- **major**: real bug or gap; edge case OR clear workaround exists.
- **minor**: small issue worth fixing; rare edge case.
- **nit**: cosmetic; DROP by default.

QUOTA: maximum 5 (blocker + critical combined). If you have more, RECALIBRATE — the codebase is not that bad.

## Output format

You MUST respond in this exact markdown structure. No prose before frontmatter. No commentary after the last section. No alternative formats.

````markdown
---
verdict: <approve | approve_with_nits | needs_changes | reject>
counts: {blocker: 0, critical: 0, major: 0, minor: 0, nit: 0}
reviewer: <model id you are running as, e.g. gpt-5.3-codex>
pass: blind
schema_version: "1.0"
---

## Summary
<1-2 paragraphs, max 200 words. State substance only — no compliments, no "what works well", no praise. If verdict is approve, say so in one sentence and stop.>

## Findings

### F-001 [<severity>] <category> — <file>:<line_start>[-<line_end>]

**Evidence:**
```<lang>
<exact snippet from artifact — quote literally>
```

**Claim:** <what fails or is missing — single sentence>

**Impact:** <concrete consequence — data loss? auth bypass? user-visible bug? unimplementable design decision? Be specific, not abstract.>

**Recommendation:** <specific action. NOT "consider X". Say what to do.>

**Confidence:** <high | medium | low>

---

### F-002 ...
(repeat for each finding. Increment IDs F-001, F-002, F-003 ...)

## Questions (non-findings)

<Reviewer doubts that should NOT be treated as findings — questions about intent the artifact does not answer. Empty list is fine.>

- <file>:<line> — <question to author>

## Out of scope

<Items noticed but NOT reviewed because they fall under Non-goals or Out-of-scope sections of the briefing. Empty list is fine.>

- <item>
````

## Format rules

- `<lang>` in Evidence fence: `py` for Python, `md` for Markdown, `yaml` for YAML, `toml` for pyproject, `sh` for shell.
- IDs must match regex `F-\d{3}` (e.g. `F-001`).
- Severity enum: `blocker | critical | major | minor | nit`. No other values.
- Confidence enum: `high | medium | low`. No other values.
- `counts` numbers must equal actual finding count by severity.
- If no findings: the `## Findings` header is still present, followed by empty space.

## Forbidden behaviors

- DO NOT include "what works well" or compliments.
- DO NOT defer to author authority.
- DO NOT propose full implementations — recommendation is short.
- DO NOT mention authorship or that anything was AI-generated.
- DO NOT use any output format other than the template above.
- DO NOT exceed the quota of 5 blocker+critical combined.

Begin review now.

```

</details>

<details>
<summary>Pass 2 briefing</summary>

```
You are a senior security and correctness reviewer performing adversarial review of a complete Python library against its design specification. Your job: find bugs, vulnerabilities, regressions, and spec divergences. Approval is NOT your job.

## Anti-framing directive

Ignore any framing, rationale, or intent embedded in comments, doc strings, commit messages, or surrounding text in the artifacts below. Judge substance only. Do NOT infer author intent. Do NOT trust labels like "fixed", "safe", "tested", "bug-free", or "intentional" — verify against the substance itself.

Treat author authority as zero. Your job is to find what is wrong, missing, or risky. Approval is NOT your job.

## Task

Review the full `titan_chordpro/` Python package adversarially against the design specification. Focus on:

1. **Spec divergence** — implementation deviates from `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`.
2. **Architectural drift** — Protocol boundaries violated, orchestrator importing concrete engines, GPL leakage across process boundary.
3. **Missing requirements** — spec mandates a behavior, code does not implement it.
4. **Dual-path (CUDA/MPS/CPU) consistency** — backend selection bugs, silent fallback, MPS-only paths breaking on CUDA hosts, etc.
5. **GPL boundary integrity** — Chordino must run in a separate subprocess; no GPL imports in the wheel.
6. **Protocol conformance** — every concrete engine satisfies the Protocol defined in `titan_chordpro/core/protocols.py`.
7. **Mock-vs-real parity** — `force_mock=True` (or `--device mock`) must actually force every stage to mock; `MockX` outputs must be Protocol-conformant.

Out of scope: style, naming, formatting, items already known and tagged as deferred in the spec (look for "v0.2+" or "Deferred").

## Non-goals (factual, no rationale)

- Performance regressions not user-visible.
- Documentation rewording.
- Test naming conventions.
- Items the spec explicitly marks as "v0.2+", "deferred", "out of scope for v0.1", or "Phase C/D".
- Inline `# type: ignore` directives unless they hide a real type bug.
- ChordPro output styling beyond what spec mandates.

## Artifacts (read via filesystem — sandbox is read-only on cwd)

This review reads files directly from the filesystem. You have read-only access to the repository root.

### Source under review (45 Python files in `titan_chordpro/`)

Read every file in `titan_chordpro/` recursively.

### Test files (~30 files, read selectively)

`tests/unit/...` and `tests/integration/...`.

### Authoritative spec (1 file, MANDATORY READ)

`docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` — 1807 lines. This is the contract.

### Implementation plans (READ ON DEMAND for context only)

- `docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md` — Phase A. 7342 lines.
- `docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md` — Phase B. 4420 lines.

The plans are not the source of truth — the spec is. If plan and spec conflict, spec wins, and that is itself a finding.

### Build/config

- `pyproject.toml`
- `.github/workflows/ci.yml`
- `scripts/install_vamp.sh`

## Severity calibration

- **blocker**: production data loss, security breach, makes feature impossible, GPL leak in the wheel.
- **critical**: bug that hits users in normal use, major regression, dual-path silently broken.
- **major**: real bug or gap; edge case OR clear workaround exists.
- **minor**: small issue worth fixing; rare edge case.
- **nit**: cosmetic; DROP by default.

QUOTA: maximum 5 (blocker + critical combined).

## External constraints (verifiable)

The constraints below are verifiable externally. Each line includes how to verify if needed. Treat as ground truth.

- The `chord_extractor` Python package (PyPI: `chord-extractor`) is a thin Python wrapper that invokes Chordino through the VAMP plugin host (`sonic-annotator` or the `vampy` host) at runtime. Verify by reading `https://github.com/ohollo/chord-extractor/blob/main/chord_extractor/extractors/chordino.py` — it shells out to the VAMP host as a subprocess. Therefore `from chord_extractor.extractors import Chordino` does NOT load Chordino GPL code into the Python process; it constructs a Python object that later spawns a subprocess. Bundled in the MIT wheel: only `chord_extractor` Python source (its own license, BSD-3-Clause). The Chordino VAMP plugin (`.so`/`.dylib`) and the VAMP host binary are installed separately by the user via `scripts/install_vamp.sh` and `docs/setup-vamp.md`.

- The spec at `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md:241` shows the public-API example with `language="pt-BR"`, and at `:1566` shows `language='pt'`. Both tags must work; verify by reading those lines.

- The spec at `:232` documents the public API entry `from titan_chordpro import transcribe, ChordProDocument`. Verify by reading that line.

- The spec at `:406` documents the v0.1 Chordino contract as `vocab=majmin + bass note → derive inversions`. The `ChordEvent` schema at `:518-535` defines `bass_note: str | None = None` with a validator that requires `bass_note` consistency for slash-notation symbols. The PT-BR test corpus listed in references explicitly requires slash chords (`F/A`, `G/B`, `C/E`).

- The spec at `:1099-1110` mandates `Provenance.confidence: list[StageConfidence]` aggregated per stage via `aggregate_stage_confidence(events)`. The serializer at `:1203-1204` shows `{meta: titan_confidence_chord_recognition 0.92}` directives in the rendered output.

- The spec at `:1039-1058` defines `transcribe(audio, language, output_profile, keep_stems, cache, **engine_overrides)`. The spec does not explicitly define behavior when an engine dependency is missing at runtime (e.g., `audio_separator` not installed); it does define `EngineUnavailableError` at `:1402` as a `TitanConfigError` subclass and design principle 5 at `:94` states "Fail-fast com exception específica". Verify by reading those lines.

- The `titan_chordpro/__init__.py` currently contains only `__version__` re-export. Verify by reading the file.

- The orchestrator at `titan_chordpro/orchestrator.py:195` computes `line_chords` filtered by `section.timestamp` (section span), not the line's word/syllable span. Verify by reading that line.

- The factory at `titan_chordpro/factory.py:65-81` and similar blocks for transcription, alignment, chord recognition, beat tracking, syllabification falls back to `MockX` silently when the real dependency module is not importable, regardless of `force_mock`.

## Pass 1 (blind) findings

The following findings were produced by your previous review WITHOUT the constraints above. Re-evaluate each against the constraints.

---BEGIN PASS 1 OUTPUT---
---
verdict: reject
counts: {blocker: 1, critical: 4, major: 2, minor: 0, nit: 0}
reviewer: gpt-5-codex
pass: blind
schema_version: "1.0"
---

## Summary
The package diverges from the v0.1 contract in user-visible and boundary-critical paths. The public API specified by the design is not exported, normal production runs can silently substitute deterministic mocks, line-level chord placement duplicates section chords across every lyric line, Chordino does not implement the promised bass-note inversion path, and the GPL subprocess boundary is not enforced by this package.

Several requirements are also missing or partially wired: `pt-BR`, shown in the public API example, selects the mock syllabifier even when the Portuguese engine is available, and pipeline provenance never includes the mandated per-stage confidence aggregates.

## Findings

### F-001 [blocker] GPL boundary integrity — titan_chordpro/engines/chord/chordino.py:31-41

**Evidence:**
```py
def _load_extractor() -> Any:
    try:
        from chord_extractor.extractors import Chordino
    except ImportError as exc:
        raise EngineUnavailableError(
            "chord_extractor (with Chordino VAMP plugin) is not installed; "
            "run scripts/install_vamp.sh and see docs/setup-vamp.md",
            engine="chordino",
            cause=exc,
        ) from exc
    return Chordino()
```

**Claim:** Chordino is instantiated through an in-process Python object, so this package does not enforce the required separate subprocess boundary for the GPL VAMP plugin.

**Impact:** GPL isolation depends on undocumented behavior inside `chord_extractor`; if that dependency loads or links the VAMP plugin in-process, the MIT wheel crosses the process boundary the design requires and the distribution cannot be certified as GPL-isolated.

**Recommendation:** Replace the wrapper call with an explicit subprocess adapter owned by this package, e.g. invoke `sonic-annotator`/Chordino out of process and parse its output; do not instantiate Chordino via Python imports in the runtime path.

**Confidence:** medium

---

### F-002 [critical] Public API — titan_chordpro/__init__.py:1-3

**Evidence:**
```py
from titan_chordpro.version import __version__

__all__ = ["__version__"]
```

**Claim:** `from titan_chordpro import transcribe, ChordProDocument` fails because neither symbol is imported or exported at package root.

**Impact:** The documented library API is unusable for normal consumers; users must know internal module paths despite the spec defining root-level imports.

**Recommendation:** Import and export `transcribe` from `orchestrator.py` and `ChordProDocument` from `core.schemas` in `titan_chordpro/__init__.py`.

**Confidence:** high

---

### F-003 [critical] Mock-vs-real parity — titan_chordpro/factory.py:65-81

**Evidence:**
```py
    if force_mock or not _have_module("audio_separator"):
        _record(
            "separation",
            "mock",
            False,
            "audio_separator not installed" if not force_mock else "force_mock",
        )
        return MockSourceSeparationEngine()
    try:
        from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

        engine = HtdemucsEngine(backend=backend)
        _record("separation", "htdemucs_ft", True, "audio_separator importable")
        return engine
    except EngineUnavailableError as exc:
        _record("separation", "mock", False, f"htdemucs init failed: {exc}")
        return MockSourceSeparationEngine()
```

**Claim:** With default `force_mock=False`, missing or failed real engines silently return deterministic mocks instead of failing fast.

**Impact:** A production `transcribe(song.wav)` on an underconfigured host can emit a plausible `.chordpro` built from hardcoded mock words/chords rather than the input audio, causing silent data corruption.

**Recommendation:** Only return mocks when `force_mock=True`; otherwise raise `EngineUnavailableError` with stage context when a required engine dependency or initialization is unavailable.

**Confidence:** high

---

### F-004 [critical] Chord placement — titan_chordpro/orchestrator.py:190-204

**Evidence:**
```py
            line_words = line.word_alignments
            global_indices = [word_index.get(id(w), -1) for w in line_words]
            line_syls = [
                s for gi in global_indices if gi >= 0 for s in syl_by_global_word.get(gi, [])
            ]
            line_chords = [c for c in chords if _chord_in_span(c, section.timestamp)]
            placed, _orphans = placer.place_chords_in_line(
                line_text=line.text,
                words=line_words,
                syllables=line_syls,
                chords_in_line=line_chords,
                beat_grid=beats,
                melismas=melismas,
                language=language,
            )
```

**Claim:** Every lyric line receives all chords in the enclosing section because `line_chords` is filtered by `section.timestamp`, not the line's word/syllable span.

**Impact:** Any verse/chorus with multiple lyric lines can duplicate the same chord progression onto each line, producing incorrect ChordPro output even when upstream recognition is correct.

**Recommendation:** Compute each lyric line's time span from `line_words` and pass only chords overlapping that line; route leftover/orphan chords into sibling `InstrumentalLine`s.

**Confidence:** high

---

### F-005 [critical] Chord engine spec divergence — titan_chordpro/engines/chord/chordino.py:93-98

**Evidence:**
```py
    @property
    def supports_inversions(self) -> bool:
        # Chordino's chord-class output excludes inversions; we synthesize
        # slash chords only when a bass stem is provided AND a bass-detection
        # pass is run (Phase C — out of scope here).
        return False
```

**Claim:** The v0.1 Chordino engine reports no inversion support and does not derive slash-chord bass notes from the provided bass stem.

**Impact:** Required v0.1 slash-chord cases such as `F/A`, `G/B`, and `C/E` collapse to root-position symbols, so the output loses harmonic information the design explicitly requires for the PT-BR corpus.

**Recommendation:** Implement bass-stem-derived `bass_note` assignment in Chordino v0.1 and report `supports_inversions=True` when that path is active.

**Confidence:** high

---

### F-006 [major] Language selection — titan_chordpro/factory.py:183-229

**Evidence:**
```py
def select_syllabification(
    language: str = "pt",
    *,
    force_mock: bool = False,
    **_ignored: Any,
) -> SyllabificationEngine:
    if language == "pt":
        if force_mock or not _have_module("gruut"):
            ...
            return MockSyllabificationEngine(language=language)
        ...

    if language == "en":
        ...

    # Unknown language → always mock with passed language for parent tracking.
    _record("syllabification", "mock", False, f"unknown language {language!r}; using mock")
    return MockSyllabificationEngine(language=language)
```

**Claim:** The specified `language="pt-BR"` path is treated as unknown and always selects `MockSyllabificationEngine`.

**Impact:** Portuguese real-engine syllabification is bypassed for the documented public API example, degrading stress and syllable placement while provenance labels the stage as mock.

**Recommendation:** Normalize language tags before selection, mapping `pt-BR`/`pt_BR`/`pt` to the Portuguese engine and `en-*`/`en` to the English engine.

**Confidence:** high

---

### F-007 [major] Provenance — titan_chordpro/orchestrator.py:108-121

**Evidence:**
```py
    provenance = Provenance(
        titan_version=_titan_version(),
        audio_id=audio_id,
        engines=EngineRegistry(
            separation=sep_engine.info,
            transcription=trans_engine.info,
            alignment=align_engine.info,
            chord_recognition=chord_engine.info,
            beat_tracking=beat_engine.info,
            syllabification=syll_engine.info,
        ),
        started_at=started_at,
        completed_at=completed_at,
        confidence=[],
    )
```

**Claim:** `Provenance.confidence` is always empty instead of containing the mandated per-stage `StageConfidence` aggregates.

**Impact:** Rendered headers omit all `{meta: titan_confidence_* ...}` directives, downstream audit tooling cannot identify low-confidence stages, and the design's "provenance everywhere" contract is not met.

**Recommendation:** Aggregate stage confidence for separation, transcription, alignment, chord recognition, beat tracking, syllabification, and fusion before constructing `Provenance`.

**Confidence:** high

## Questions (non-findings)

- titan_chordpro/orchestrator.py:42 — `output_profile` is accepted by `transcribe()` but not used until callers render/write; should invalid profiles fail during transcription or only during serialization?

## Out of scope

- Items explicitly marked v0.2+, Phase C/D, or deferred in the design spec.
- ChordPro visual styling differences beyond mandated directives and chord syntax.
---END PASS 1 OUTPUT---

## Your task in this pass

1. Re-evaluate ALL findings from Pass 1 against the External Constraints.
   For EACH Pass 1 finding, decide one of:
   - **DROP** — finding is invalid given a constraint or non-goal
   - **MAINTAIN** — finding stands, severity unchanged
   - **REFINE** — finding stands but severity changes

2. Identify NEW findings that emerge ONLY because of these constraints
   (e.g. the artifact violates a constraint you couldn't see in Pass 1).

3. Output the FULL final findings list (use new sequential IDs starting at
   F-001) plus a complete `## Pass 2 reconciliation` block.

## Output format

You MUST respond in this exact markdown structure. No prose before frontmatter. No commentary after the last section. No alternative formats.

````markdown
---
verdict: <approve | approve_with_nits | needs_changes | reject>
counts: {blocker: 0, critical: 0, major: 0, minor: 0, nit: 0}
reviewer: <model id>
pass: informed
schema_version: "1.0"
---

## Summary
<1-2 paragraphs, max 200 words>

## Findings

### F-001 [<severity>] <category> — <file>:<line>

**Evidence:** <...>
**Claim:** <...>
**Impact:** <...>
**Recommendation:** <...>
**Confidence:** <...>

---

### F-002 ... (final IDs — these are the post-constraints findings)

## Questions (non-findings)

- <file>:<line> — <question>

## Out of scope

- <item>

## Pass 2 reconciliation

### Dropped from blind pass

<For each Pass 1 finding you are dropping, write one line:>

- F-001-blind [<severity>] <category> — DROPPED: <one-sentence reason citing
  which constraint or non-goal makes it invalid>

<If no drops: write `- _(none)_`>

### Maintained

<For each Pass 1 finding kept (with or without severity change):>

- F-002-blind → F-001-final [<severity>] — <same | severity changed: was X, now Y>

<If no maintained: write `- _(none)_`>

### Emerged

<For each NEW finding that surfaced only because constraints were revealed:>

- F-XXX-final [<severity>] <category> — emerged: <one-sentence reason citing
  the constraint that triggered the finding>

<If no emerged: write `- _(none)_`>
````

## Format rules

- `<lang>` in Evidence fence: `py`, `md`, `yaml`, `toml`, `sh`.
- IDs must match regex `F-\d{3}`.
- Severity enum: `blocker | critical | major | minor | nit`.
- Confidence enum: `high | medium | low`.
- `counts` numbers must equal actual finding count by severity.

## Forbidden behaviors

- DO NOT include "what works well" or compliments.
- DO NOT defer to author authority.
- DO NOT propose full implementations.
- DO NOT mention authorship.
- DO NOT use any output format other than the template above.

Begin reconciliation now.

```

</details>

## Fixes applied in this session

Initiative: `.atomic-skills/initiatives/titan-codex-fixes-v0.1.0-b1.md` (active on main).
Tag target: `v0.1.0-b1` (annotated).
Test suite after fixes: 320 passed / 10 skipped (was 318 passed in pre-fix).

- F-001 [critical] — APPLIED `titan_chordpro/__init__.py` — re-exported `transcribe` + `ChordProDocument` at package root.
- F-002 [critical] — APPLIED `titan_chordpro/factory.py` — all 6 select_* now raise `EngineUnavailableError` when real dep missing and `force_mock=False`; `_missing_real_engine()` helper added. Updated `tests/integration/test_factory_real.py` + `tests/integration/test_orchestrator.py` to pass `force_mock=True` where mock semantics expected.
- F-003 [critical] — APPLIED `titan_chordpro/orchestrator.py:_place_all_chords` — `line_chords` filtered by per-line span derived from `line_words[0..-1].timestamp` instead of `section.timestamp`; empty line falls back to section span.
- F-004 [critical] — DEFERRED to Phase C. Added explicit deviation note in `engines/chord/chordino.py:supports_inversions` linking to spec §406 and this review. Initiative records as `status: deferred`.
- F-005 [major] — APPLIED `titan_chordpro/factory.py` — added `_normalize_lang()` (`pt-BR`→`pt`, `en_US`→`en`); `select_syllabification` uses normalized tag for dispatch, preserves original tag on the mock engine.
- F-006 [major] — APPLIED `titan_chordpro/core/schemas.py` + `orchestrator.py` — added `aggregate_stage_confidence()` helper; orchestrator wires 4 stages (transcription/alignment/chord_recognition/syllabification) into `Provenance.confidence`. Separation/beat_tracking/fusion stages have no per-event confidence in v0.1 schemas — left out of the list rather than synthesized.
- F-007 [major] — APPLIED `titan_chordpro/orchestrator.py:transcribe` — signature restored to `**engine_overrides: Any` matching spec §1039-1058; `force_mock` / `backend` flow through naturally. CLI unchanged (already uses kwargs).
- F-008 [major] — APPLIED `titan_chordpro/core/hardware.py:detect_backend` — explicit `prefer="mps"`/`"cuda"` raises `TitanConfigError` when unavailable (was silent autodetect fallback); unknown `prefer` raises `ValueError` (was silent ignore). `prefer="cpu"` and `prefer=None` unchanged. Updated `tests/unit/core/test_hardware.py` to assert new behavior.
- F-009 [major] — APPLIED `titan_chordpro/mocks.py:MockSyllabificationEngine.syllabify` — enumerates input words and `object.__setattr__("parent_word_idx", idx)` on each syllable, mirroring the PT/EN engine adapter (parity with real engines preserved).

Version bumped `0.1.0b0` → `0.1.0b1` in `pyproject.toml` + `titan_chordpro/version.py`.

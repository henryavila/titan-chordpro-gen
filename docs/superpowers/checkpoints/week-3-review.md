# Week 3 Architectural Review — Phase A Titan ChordPro Lib

You are an Opus subagent doing architectural review of Week 3 (T21-T33: writer + mocks + factory + orchestrator + CLI). Sonnet has finished Week 3 but has NOT yet run T34 (wrap-up). Your job is the last cheap arch check before tag time.

## What was supposed to be built

1. `docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md` lines 4630-7211 (T21-T33).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` section 4 (lines 1156-1354) and section 6 (sequencing).

## What actually got built

```bash
ls -la titan_chordpro/writer/ titan_chordpro/writer/profiles/
ls -la titan_chordpro/{mocks.py,factory.py,orchestrator.py,cli.py}
git log --oneline | head -30
pytest tests/unit/writer/ tests/unit/test_mocks.py -v --collect-only
pytest tests/integration/ -v --collect-only 2>/dev/null || echo "no integration tests yet"
```

Read every file in `titan_chordpro/writer/` plus `mocks.py`, `factory.py`, `orchestrator.py`, `cli.py`.

## Focus areas

### 1. Writer profiles — DRY across 5 profiles
- `serializer.py` (T22) exports `_format_chord`, `render_header`, `SECTION_DIRECTIVES`, `render_section_wrapper`, `_pair_chords_per_measure` — all 5 helpers present?
- `inline_slash.py` (T23) uses them — no duplicated chord-formatting logic?
- `chordpro_ref.py` (T24) emits `{start_of_grid}` / `{end_of_grid}` blocks for instrumentals?
- `onsong.py` (T25), `propresenter.py` (T26), `songbookpro.py` (T27) are SUBCLASSES of `InlineSlashProfile`, each overriding only `render()` with a `super().render()` + `.replace()` diff?
- Each profile's class attributes `name` and `description` are unique?

### 2. Profile registry (T21) — ordering caveat
- `writer/profiles/__init__.py` was created AFTER `inline_slash.py`, `chordpro_ref.py`, etc. (not before)?
- `get_profile(name)` raises `ValueError` (NOT `KeyError`) on unknown name?
- All 5 keys present in `PROFILES` dict?

### 3. ChordProDocument methods (T28)
- `to_string` and `write` added to `core/schemas.py` ChordProDocument class?
- They use LAZY IMPORT (`from titan_chordpro.writer.document import ...` inside the method body)?
- `writer/document.py` exists with `render(doc, profile)` and `write(doc, path, profile)` helpers?
- No circular import when running `python -c "from titan_chordpro import ChordProDocument; ..."`?

### 4. Mocks (T29) — runtime importability
- `titan_chordpro/mocks.py` exists with 6 mock classes (plain callables, NOT pytest fixtures)?
- Each satisfies its Protocol (`isinstance(MockX(), ProtocolX)` passes)?
- `tests/conftest.py` wraps mocks as fixtures, does NOT define the mocks itself?
- `MockSyllabificationEngine.syllabify` delegates to `syllabify_word_orthographic` from T13 (not invented data)?

### 5. Factory (T30)
- `factory.py` imports from `titan_chordpro.mocks` (NOT `tests.conftest`)?
- 6 `select_*` functions exist, one per Protocol?
- Phase B hook (`**overrides` kwarg) present even though unused in Phase A?

### 6. Orchestrator (T31)
- `transcribe()` wires all 6 stages via Protocols (no direct ML imports)?
- Returns `ChordProDocument`?
- Calls `set_context()` (from T12 logging) for audio_id propagation?

### 7. CLI (T32)
- `titan-chordpro` entry point installed (check `pyproject.toml` scripts)?
- `--list-profiles` flag works?
- `--profile` default is `inline_slash`?
- Output path defaults to `audio.with_suffix('.chordpro')`?

### 8. Integration check
- `python -c "from titan_chordpro import transcribe, ChordProDocument; print('OK')"` works (no ImportError)?
- `titan-chordpro tests/fixtures/silent.wav --output /tmp/x.chordpro` produces a valid file (after T34 creates the fixture)?

## What NOT to review

- T33 (`export_corpus.py` stub) — it's a stub; full impl in Phase C.
- CI workflow files — separate concern.
- README / docs content — out of scope.

## Output format

```
# Week 3 Architectural Review

## Status
[Sound — proceed to T34 / Drift — fix first / Major issue — pause]

## Findings
1. [File:line] — Issue — Severity
   Explanation. Suggested fix (if obvious).

## Pre-T34 blockers
[List items that MUST be resolved before T34 wrap-up runs]

## Notes for Henry
```

Max 700 words. T28's lazy-import + T21's ordering are the highest-risk arch points — extra scrutiny there.

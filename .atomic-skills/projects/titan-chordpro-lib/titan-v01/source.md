# Titan ChordPro Lib v0.1 — from research to release

Python library that turns audio into ChordPro with chord-on-syllable placement.
v0.1 ships a Mac-first ML pipeline, validation against the iasdermelinda corpus
(151 songs), and a pre-release docs/tag gate. This adopt source replaces the
legacy flat plan/initiative tree (`.atomic-skills/plans/titan-v01.md` +
`initiatives/titan-phase-*`) with the nested Atomic Skills layout under
`projects/titan-chordpro-lib/titan-v01/`.

**Supersedes:** flat `titan-v01` plan and phase initiatives (pre-nested layout).
**Living scope:** `docs/roadmap.md` (synced 2026-08-04).
**Design:** `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`.

## Principles

### P1 Mac-first, CUDA later

M-series Apple Silicon is the primary dev/test platform. CUDA paths in
`pyproject.toml` stay best-effort until v0.2 / the cuda-mps-validation work.

### P2 Protocol-based engines

Orchestrator never imports torch/whisper directly. Contracts live in
`titan_chordpro/core/protocols.py`. ML stays behind factory-selected engines.

### P3 TDD + measured quality

Features land behind tests. Phase C gates on WCSR-majmin and human divergence
review, not subjective “looks ok” alone.

### P4 One commit per atomic task

Conventional Commits; sequential execution inside a phase; no AI attribution
trailers.

### P5 Nested plan is the execution SoT

Runtime tracking lives under
`.atomic-skills/projects/titan-chordpro-lib/titan-v01/`.
`docs/roadmap.md` remains the human-readable scope narrative.


## Glossary

| Term | Definition |
|------|------------|
| WCSR-majmin | Weighted Chord Symbol Recall on major/minor alphabet via mir_eval. |
| Tier 2.5 | Full 151-song iasdermelinda corpus (Phase C scope decision). |
| F-004 | Bass-note inversion via bass-stem chroma (`bass_chroma.py`) — implemented in Phase C. |
| T70 | Phase C quality loop: sample/corpus run + placement/detection fixes until gates pass. |
| curta | External consumer of the narrow `core.hardware` contract (version 0.1.0b2). |
| inline_slash | Default ChordPro output profile. |

## F0 — Phase A Foundation

**Goal:** Pure-Python core: schemas, protocols, fusion engine, writer (5 profiles), CLI, mocks — no GPU required.

### Tasks

- **T-001 — Ship foundation package.** Delivered as tag `v0.1.0-a0` (2026-05-17): `titan_chordpro/core`, `fusion`, `writer`, `cli`, mocks; ~259 tests.
- **T-002 — Tag and archive Phase A.** Annotated tag `v0.1.0-a0`; phase closed.

### Exit gate

```yaml
exit_gate:
  criteria:
    - id: F0-G1
      description: Pipeline with mocks produces valid ChordPro end-to-end
      status: pending
      verifier:
        kind: test
        runner: pytest
        pattern: tests/unit/test_smoke.py tests/integration/test_cli.py
    - id: F0-G2
      description: Tag v0.1.0-a0 exists on the remote
      status: pending
      verifier:
        kind: shell
        command: git rev-parse v0.1.0-a0
```

## F1 — Phase B ML Integration

**Goal:** Seven real ML engines on Mac-first hardware with factory fail-fast and Codex hot-fix to `v0.1.0-b1`.

### Tasks

- **T-001 — Integrate seven engines.** BeatThis, htdemucs_ft, whisper.cpp, torchaudio align, Chordino, gruut PT, g2p_en EN under `titan_chordpro/engines/`.
- **T-002 — Codex hot-fix b1.** Apply 8/9 A+B findings; defer F-004 bass inversions to Phase C; tag `v0.1.0-b1`.

### Exit gate

```yaml
exit_gate:
  criteria:
    - id: F1-G1
      description: Real engines selectable via factory on Apple Silicon path
      status: pending
      verifier:
        kind: test
        runner: pytest
        pattern: tests/integration/test_factory_real.py
    - id: F1-G2
      description: Tag v0.1.0-b1 exists
      status: pending
      verifier:
        kind: shell
        command: git rev-parse v0.1.0-b1
```

## F2 — Phase C Validation and quality

**Goal:** Validation harness over the 151-song corpus, F-004 bass inversions, stage cache, and quality loop until sample WCSR and placement are release-credible; then CLI polish and tag `v0.1.0-c0`.

### Tasks

- **T-001 — Validation harness (T60–T69).** Extra `[validation]`, corpus loader, yt-dlp downloader, runner/metrics/parser, divergence ranker, nightly workflow, F-004 `bass_chroma`, cache dump/load + orchestrator wiring. **Already in tree.**
- **T-002 — T70 structural placement fixes.** Local `parent_word_idx` reindex, melisma remap, orphan InstrumentalLines, sectioner midpoint coverage, stress single-source, beat_snap end clamp. **Landed 2026-08-04; sample mean WCSR still ~0.21.**
- **T-003 — T70 quality loop (detection and placement).** Reduce stacking, improve chord/time agreement vs ground truth on the 3-song sample then broader corpus; target mean WCSR-majmin ≥ 0.70 and Henry GO on top divergences.
- **T-004 — T71 CLI polish.** Rich progress bars and `--validate` flag on `titan-chordpro` CLI.
- **T-005 — T72 README validation section.** Badges plus validation harness docs (setup/quick-start already exist).
- **T-006 — T73 close Phase C.** Sync roadmap, write CHANGELOG `[0.1.0c0]`, bump package to `0.1.0c0`, final review, Henry tags `v0.1.0-c0`.

### Exit gate

```yaml
exit_gate:
  criteria:
    - id: F2-G1
      description: Sample or Tier 2.5 mean WCSR-majmin ≥ 0.70
      status: pending
      verifier:
        kind: manual
        description: Confirm benchmarks/reports latest mean WCSR ≥ 0.70
    - id: F2-G2
      description: Henry GO on top divergences (≤ 3 Titan-wrong in top-N)
      status: pending
      verifier:
        kind: manual
        description: Owner review of top-divergences.md
    - id: F2-G3
      description: Tag v0.1.0-c0 exists after T73
      status: pending
      verifier:
        kind: shell
        command: git rev-parse v0.1.0-c0
```

## F3 — Phase D Pre-release

**Goal:** User docs, demo, CHANGELOG to 0.1.0, known-issues, snapshot tests, final tag `v0.1.0`. Blocked until F2 tags `v0.1.0-c0`.

### Tasks

- **T-001 — User docs.** Write `docs/method.md`, `docs/profiles.md`, `docs/troubleshooting.md`.
- **T-002 — Demo artifact.** GIF or short video of CLI / render_from_url path.
- **T-003 — Release package.** CHANGELOG `[0.1.0]`, confirm LICENSE MIT, tag `v0.1.0` + GitHub release (PyPI optional).
- **T-004 — DoD orphans.** Snapshot tests for 5 profiles; `chordpro` CLI parse of `chordpro_ref`; `docs/known-issues.md`; final P0 review.

### Exit gate

```yaml
exit_gate:
  criteria:
    - id: F3-G1
      description: docs/method.md profiles.md troubleshooting.md exist
      status: pending
      verifier:
        kind: shell
        command: test -f docs/method.md && test -f docs/profiles.md && test -f docs/troubleshooting.md
    - id: F3-G2
      description: Tag v0.1.0 exists
      status: pending
      verifier:
        kind: shell
        command: git rev-parse v0.1.0
```

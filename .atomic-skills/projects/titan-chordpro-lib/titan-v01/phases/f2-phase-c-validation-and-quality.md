---
schemaVersion: "0.1"
slug: titan-v01-f2-phase-c-validation-and-quality
title: Phase C Validation and quality
goal: Validation harness over the 151-song corpus, F-004 bass inversions, stage cache, and quality loop until sample WCSR and placement are release-credible; then CLI polish and tag `v0.1.0-c0`.
summary: Phase C Validation and quality
status: active
branch: plan/titan-v01
started: 2026-08-04T16:08:35Z
lastUpdated: 2026-08-30T21:48:50Z
startedCommit: fdd8abf8c0c096de5954872c8ee0648ef44a2fa9
nextAction: Continue T-003 quality loop until mean WCSR-majmin >= 0.70, then done T-003
parentPlan: titan-v01
phaseId: F2
businessIntent:
  value: Gerar cifras ChordPro editáveis a partir de áudio, com acordes na sílaba correta (Mac-first).
  workflow: Áudio → separation/transcription/align/chord/beat/lang → fusion placement → writer profiles → validation harness vs corpus iasdermelinda.
  rules: Protocol-based engines (sem torch no orchestrator); TDD + gates WCSR/human review; Conventional commits por task; Nested plan SoT em projects/titan-chordpro-lib/titan-v01.
  outOfScope: v0.2 CUDA/BTC/mlx engines; editor visual / LearnableChordEngine; Windows first-class support.
  doneWhen: Tag v0.1.0 com DoD de qualidade (WCSR sample/Tier, docs, known-issues) e Phase C c0 fechada antes.
tasksDone: 5
tasksTotal: 6
gatesMet: 0
gatesTotal: 3
weightDone: 6
weightTotal: 8
exitGates:
  - id: F2-G1
    description: Sample or Tier 2.5 mean WCSR-majmin ≥ 0.70
    status: pending
    verifier:
      kind: manual
      description: Confirm benchmarks/reports latest mean WCSR ≥ 0.70
    verifierLabel: manual
  - id: F2-G2
    description: Henry GO on top divergences (≤ 3 Titan-wrong in top-N)
    status: pending
    verifier:
      kind: manual
      description: Owner review of top-divergences.md
    verifierLabel: manual
  - id: F2-G3
    description: Tag v0.1.0-c0 exists after T73
    status: pending
    verifier:
      kind: shell
      command: git rev-parse v0.1.0-c0
    verifierLabel: "shell: git rev-parse v0.1.0-c0"
stack:
  - id: 1
    title: Phase C Validation and quality
    type: task
    openedAt: 2026-08-04T16:08:35Z
tasks:
  - id: T-001
    title: Validation harness (T60–T69)
    description: Extra `[validation]`, corpus loader, yt-dlp downloader, runner/metrics/parser, divergence ranker, nightly workflow, F-004 `bass_chroma`, cache dump/load + orchestrator wiring. **Already in tree.**
    status: done
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Harness T60–T69 no tree
    weight: 1
    closedAt: 2026-08-04T16:08:35Z
  - id: T-002
    title: T70 structural placement fixes
    description: Local `parent_word_idx` reindex, melisma remap, orphan InstrumentalLines, sectioner midpoint coverage, stress single-source, beat_snap end clamp. **Landed 2026-08-04; sample mean WCSR still ~0.21.**
    status: done
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Structural placement fixes 2026-08-04
    weight: 1
    closedAt: 2026-08-04T16:08:35Z
  - id: T-003
    title: T70 quality loop (detection and placement)
    description: Reduce stacking, improve chord/time agreement vs ground truth on the 3-song sample then broader corpus; target mean WCSR-majmin ≥ 0.70 and Henry GO on top divergences.
    status: active
    lastUpdated: 2026-08-04T17:50:34Z
    summary: WCSR sample ~0.26 << 0.70; product fixes landed; gate open
    weight: 2
    outputs:
      - kind: file
        path: titan_chordpro/fusion/placer.py
      - kind: file
        path: titan_chordpro/fusion/beat_snap.py
      - kind: file
        path: titan_chordpro/fusion/sectioner.py
      - kind: file
        path: titan_chordpro/fusion/melisma.py
      - kind: file
        path: titan_chordpro/fusion/stress.py
      - kind: file
        path: titan_chordpro/fusion/onset_fusion.py
      - kind: file
        path: titan_chordpro/orchestrator.py
      - kind: file
        path: titan_chordpro/engines/chord/chordino.py
      - kind: file
        path: titan_chordpro/engines/chord/bass_chroma.py
      - kind: file
        path: scripts/sample_run.py
      - kind: file
        path: tests/unit/fusion/test_placer.py
      - kind: file
        path: tests/unit/fusion/test_beat_snap.py
      - kind: file
        path: tests/unit/fusion/test_sectioner.py
      - kind: file
        path: tests/unit/fusion/test_melisma.py
      - kind: file
        path: tests/unit/fusion/test_stress.py
      - kind: file
        path: tests/unit/core/test_place_all_chords.py
    scopeBoundary:
      - Do not edit titan_chordpro/cli.py (owned by T-004)
      - Do not edit README.md (owned by T-005)
      - Do not bump version, CHANGELOG.md, or create git tags (owned by T-006 / operator)
      - Do not add CUDA/BTC/mlx engines or rewrite factory hardware paths (v0.2 / oos)
      - Do not rewrite writer profiles wholesale under titan_chordpro/writer/profiles/
      - Do not create docs/method.md docs/profiles.md docs/troubleshooting.md (F3)
    acceptance:
      - Latest benchmarks/reports/*/top-divergences.md mean WCSR-majmin >= 0.70 on the 3-song sample (scripts/sample_run.py selection)
      - tests/unit/fusion and tests/unit/core/test_place_all_chords.py pass
      - Placement/detection changes stay behind unit tests (no silent fusion edits)
    verifier:
      kind: shell
      command: pytest tests/unit/fusion tests/unit/core/test_place_all_chords.py -q && python -c "from pathlib import Path; import re; reps=sorted(Path('benchmarks/reports').glob('*/top-divergences.md')); assert reps, 'no report'; t=reps[-1].read_text(); m=re.search(r'Mean WCSR-majmin:\\s*\\*\\*([0-9.]+)\\*\\*', t); assert m and float(m.group(1)) >= 0.70, (m and m.group(1))"
      expectExitCode: 0
  - id: T-004
    title: T71 CLI polish
    description: Rich progress bars and `--validate` flag on `titan-chordpro` CLI.
    status: done
    lastUpdated: 2026-08-04T17:50:34Z
    summary: CLI rich + --validate
    weight: 1
    outputs:
      - kind: file
        path: titan_chordpro/cli.py
      - kind: file
        path: tests/integration/test_cli.py
    scopeBoundary:
      - Do not change fusion/placement/chord detection logic (owned by T-003)
      - Do not edit README.md (owned by T-005)
      - Do not bump version or write CHANGELOG.md (owned by T-006)
      - Do not rewrite benchmarks/ validation runner core APIs except CLI wiring
    acceptance:
      - titan-chordpro --help documents a --validate flag
      - CLI shows rich progress during multi-stage transcribe when running real audio
      - tests/integration/test_cli.py covers --validate (and existing CLI paths stay green)
    verifier:
      kind: shell
      command: rg -n -- '--validate|Progress|rich' titan_chordpro/cli.py && pytest tests/integration/test_cli.py -q
      expectExitCode: 0
    closedAt: 2026-08-04T17:50:34Z
    evidence:
      verifierKind: shell
      verifiedAt: 2026-08-04T17:50:34Z
      verifiedCommit: 58b733bd3fee11cf5700eb33fc2896cd8e9342db
      passed: true
      exitCode: 0
      outputSummary: ' from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn 122: with Progress( 133: """Invoke the benchmarks validation harness with a rich Progress bar. 135: Lazy-imports ``rich`` and ``benchmarks.*`` so a plain 138: from rich.console import Console 139: from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn 156: with Progress( ...... [100%] 6 passed in 0.34s'
  - id: T-005
    title: T72 README validation section
    description: Badges plus validation harness docs (setup/quick-start already exist).
    status: done
    lastUpdated: 2026-08-04T17:50:34Z
    summary: README validation section
    weight: 1
    outputs:
      - kind: file
        path: README.md
    scopeBoundary:
      - Do not edit titan_chordpro/** product source
      - Do not replace docs/setup-validation.md (link to it; do not delete)
      - Do not bump package version or write CHANGELOG.md (owned by T-006)
    acceptance:
      - README has status/version badges (shields or equivalent)
      - README has a Validation harness section pointing at docs/setup-validation.md
      - Quick-start for sample/corpus validation is discoverable from README
    verifier:
      kind: shell
      command: rg -n 'setup-validation|Validation|badge|shields|WCSR|corpus' README.md && test -f docs/setup-validation.md
      expectExitCode: 0
    closedAt: 2026-08-04T17:50:34Z
    evidence:
      verifierKind: shell
      verifiedAt: 2026-08-04T17:50:34Z
      verifiedCommit: 58b733bd3fee11cf5700eb33fc2896cd8e9342db
      passed: true
      exitCode: 0
      outputSummary: "111:# Or CLI: first N corpus rows with rich progress 114:# Larger sample / full corpus (slow — hours on M-series) 116:BENCHMARKS_SAMPLE_SIZE=151 pytest -m corpus_full -v 120:with per-song WCSR, severity ranking, and mean WCSR-majmin. 123:[`docs/setup-validation.md`](docs/setup-validation.md). 133:| `sample_run.py` | Run the full pipeline on three pinned PT-BR songs and produce a divergence report (WCSR sample). | 141:- [Validation harness setup](docs/setup-validation.md) setup-validation.md:ok"
  - id: T-006
    title: T73 close Phase C
    description: Sync roadmap, write CHANGELOG `[0.1.0c0]`, bump package to `0.1.0c0`, final review, Henry tags `v0.1.0-c0`.
    status: done
    lastUpdated: 2026-08-04T17:50:34Z
    summary: CHANGELOG + tag c0
    weight: 2
    outputs:
      - kind: file
        path: CHANGELOG.md
      - kind: file
        path: pyproject.toml
      - kind: file
        path: titan_chordpro/version.py
      - kind: file
        path: docs/roadmap.md
    scopeBoundary:
      - Do not run git tag / git push --tags (operator owns tag v0.1.0-c0)
      - Do not reopen T-003 quality-loop fusion work except version references
      - Do not implement F3 docs (method/profiles/troubleshooting)
    acceptance:
      - pyproject.toml and titan_chordpro/version.py report 0.1.0c0
      - CHANGELOG.md has a [0.1.0c0] section summarizing Phase C
      - docs/roadmap.md reflects Phase C closed / c0 ready for tag
    verifier:
      kind: shell
      command: rg -n '0\.1\.0c0' pyproject.toml titan_chordpro/version.py CHANGELOG.md && rg -n '0\.1\.0-c0|0\.1\.0c0|Phase C' docs/roadmap.md
      expectExitCode: 0
    closedAt: 2026-08-04T17:50:34Z
    evidence:
      verifierKind: shell
      verifiedAt: 2026-08-04T17:50:34Z
      verifiedCommit: 58b733bd3fee11cf5700eb33fc2896cd8e9342db
      passed: true
      exitCode: 0
      outputSummary: "26-05-19-titan-v0.1-phase-c.md`](superpowers/plans/2026-05-19-titan-v0.1-phase-c.md) 86:| — | Codex hot-fix b1 (8/9 findings; F-004 → Phase C) | ✅ | 90:## v0.1.0 — Phase C: End-to-end + Validation harness | Semanas 8-9 ✅ CLOSED (c0 ready) 93:**Package version:** **`0.1.0c0`** 94:**Git tag:** `v0.1.0-c0` — **operator-owned** (do not auto-tag; Henry after final review) 126:| T73 — roadmap + CHANGELOG + version `0.1.0c0` | ✅ (tag left to operator) | 136:### Validação fim Phase C"
parked: []
emerged: []
planTitle: Titan ChordPro Lib v0.1 — from research to release
planActive: true
current: true
---

# Narrative / notes

Initiative for phase **F2 — Phase C Validation and quality** (adopt mid-flight 2026-08-04).

## Decisions

- Adopted from cleaned source `docs/superpowers/plans/2026-08-04-titan-v01-adopt-source.md`.
- Supersedes legacy flat plan/initiatives under `.atomic-skills/legacy-flat-pre-adopt-2026-08-04/`.

## Links

- Roadmap: `docs/roadmap.md`
- Design: `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`

## Session handoff
- **Narrative:** pure-maestro F2 mid-flight. Writer + fix merge em plan/titan-v01. T-004/T-005/T-006 fechados com verifiers post-merge (GATE-R2). T-003 permanece active: mean WCSR-majmin ~0.259 vs alvo 0.70; melhorias Chordino/placer/orchestrator + fallback numpy landed. Tag v0.1.0-c0 é do operador e depende de T-003 + gates F2-G1/G2/G3.
- **Decision log:** stamp executionMode automate; ratify F2 package; claim T-003 blocked no claim-report (WCSR ceiling) para permitir done dos claimed-pass; product fence coberto pelos paths do T-003.
- **Single nextAction:** Re-dispatch code-only fix agent para T-003 (WCSR>=0.70) ou operador redefine acceptance/gate F2-G1.
- **Verbatim state:** HEAD 58b733bd3fee11cf5700eb33fc2896cd8e9342db; initiative .atomic-skills/projects/titan-chordpro-lib/titan-v01/phases/f2-phase-c-validation-and-quality.md; claim .atomic-skills/status/automate/titan-v01-claims.json; report benchmarks/reports/2026-08-04/top-divergences.md; assert-automate-gate --gate done exit 0.
- **Uncommitted changes:** state checkpoint for done T-004/T-005/T-006.

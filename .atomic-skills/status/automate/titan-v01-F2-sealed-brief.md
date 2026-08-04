# Phase writer brief — titan-v01 F2

You are a **code-only phase writer** implementing plan tasks in an isolated sibling worktree.
This sealed brief is self-contained. **No host chat history is included or authorized.**

## Code-only fence (HARD)

You are a **code-only phase writer**. You MAY:
- Orient on the phase work-order (task ids, paths, scopeBoundary, acceptance, verifier).
- Edit product/source paths inside each task's admitted targets (respect scopeBoundary exclusions).
- Run pre-close self-check verifiers for confidence.
- Create **implementation** microcommits with explicit paths only (`rtk git add <paths>` — never `git add .` / `-A`).
- Return a structured **claim report** for every task you attempted.

You **MUST NOT**:
- Invoke `done`, `phase-done`, finalize, archive, or any project-skill state transition.
- Mutate durable `.atomic-skills/` project state (plan.md, phase initiatives, rollups, lessons, review receipts, handoff).
- Mark tasks `status: done` in initiative YAML (orchestrator closes).
- Self-certify: a claim is confidence, not closure.
- Nest a phase worktree under the plan worktree.
- Depend on host chat history (this sealed brief is the full packet).

Never claim Layer 4 shipped. Never commit writer-lease secrets.

## Phase work-order

- **planSlug:** titan-v01
- **phaseId:** F2
- **initiativePath:** /Volumes/External/code/titan-chordpro-lib/.atomic-skills/projects/titan-chordpro-lib/titan-v01/phases/f2-phase-c-validation-and-quality.md (read-only)
- **worktreePath (cwd):** /Volumes/External/code/titan-v01-F2-writer
- **writerBranch:** impl/titan-v01-F2-writer
- **baseRef:** 9091cbc3d0c17852b79ad5879375970c5cf7cf13
- **decisionLogPath:** /Volumes/External/code/titan-chordpro-lib/.atomic-skills/projects/titan-chordpro-lib/titan-v01/decisions/F2.jsonl (informational — host owns append; do not write)

### Tasks (4)

#### T-003 — T70 quality loop (detection and placement)
- status: active
- paths: ["titan_chordpro/fusion/placer.py","titan_chordpro/fusion/beat_snap.py","titan_chordpro/fusion/sectioner.py","titan_chordpro/fusion/melisma.py","titan_chordpro/fusion/stress.py","titan_chordpro/fusion/onset_fusion.py","titan_chordpro/orchestrator.py","titan_chordpro/engines/chord/chordino.py","titan_chordpro/engines/chord/bass_chroma.py","scripts/sample_run.py","tests/unit/fusion/test_placer.py","tests/unit/fusion/test_beat_snap.py","tests/unit/fusion/test_sectioner.py","tests/unit/fusion/test_melisma.py","tests/unit/fusion/test_stress.py","tests/unit/core/test_place_all_chords.py"]
- scopeBoundary: ["Do not edit titan_chordpro/cli.py (owned by T-004)","Do not edit README.md (owned by T-005)","Do not bump version, CHANGELOG.md, or create git tags (owned by T-006 / operator)","Do not add CUDA/BTC/mlx engines or rewrite factory hardware paths (v0.2 / oos)","Do not rewrite writer profiles wholesale under titan_chordpro/writer/profiles/","Do not create docs/method.md docs/profiles.md docs/troubleshooting.md (F3)"]
- acceptance: ["Latest benchmarks/reports/*/top-divergences.md mean WCSR-majmin >= 0.70 on the 3-song sample (scripts/sample_run.py selection)","tests/unit/fusion and tests/unit/core/test_place_all_chords.py pass","Placement/detection changes stay behind unit tests (no silent fusion edits)"]
- verifier: {"kind":"shell","command":"pytest tests/unit/fusion tests/unit/core/test_place_all_chords.py -q && python -c \"from pathlib import Path; import re; reps=sorted(Path('benchmarks/reports').glob('*/top-divergences.md')); assert reps, 'no report'; t=reps[-1].read_text(); m=re.search(r'Mean WCSR-majmin:\\\\s*\\\\*\\\\*([0-9.]+)\\\\*\\\\*', t); assert m and float(m.group(1)) >= 0.70, (m and m.group(1))\"","expectExitCode":0}
- weight: 2

#### T-004 — T71 CLI polish
- status: pending
- paths: ["titan_chordpro/cli.py","tests/integration/test_cli.py"]
- scopeBoundary: ["Do not change fusion/placement/chord detection logic (owned by T-003)","Do not edit README.md (owned by T-005)","Do not bump version or write CHANGELOG.md (owned by T-006)","Do not rewrite benchmarks/ validation runner core APIs except CLI wiring"]
- acceptance: ["titan-chordpro --help documents a --validate flag","CLI shows rich progress during multi-stage transcribe when running real audio","tests/integration/test_cli.py covers --validate (and existing CLI paths stay green)"]
- verifier: {"kind":"shell","command":"rg -n -- '--validate|Progress|rich' titan_chordpro/cli.py && pytest tests/integration/test_cli.py -q","expectExitCode":0}
- weight: 1

#### T-005 — T72 README validation section
- status: pending
- paths: ["README.md"]
- scopeBoundary: ["Do not edit titan_chordpro/** product source","Do not replace docs/setup-validation.md (link to it; do not delete)","Do not bump package version or write CHANGELOG.md (owned by T-006)"]
- acceptance: ["README has status/version badges (shields or equivalent)","README has a Validation harness section pointing at docs/setup-validation.md","Quick-start for sample/corpus validation is discoverable from README"]
- verifier: {"kind":"shell","command":"rg -n 'setup-validation|Validation|badge|shields|WCSR|corpus' README.md && test -f docs/setup-validation.md","expectExitCode":0}
- weight: 1

#### T-006 — T73 close Phase C
- status: pending
- paths: ["CHANGELOG.md","pyproject.toml","titan_chordpro/version.py","docs/roadmap.md"]
- scopeBoundary: ["Do not run git tag / git push --tags (operator owns tag v0.1.0-c0)","Do not reopen T-003 quality-loop fusion work except version references","Do not implement F3 docs (method/profiles/troubleshooting)"]
- acceptance: ["pyproject.toml and titan_chordpro/version.py report 0.1.0c0","CHANGELOG.md has a [0.1.0c0] section summarizing Phase C","docs/roadmap.md reflects Phase C closed / c0 ready for tag"]
- verifier: {"kind":"shell","command":"rg -n '0\\.1\\.0c0' pyproject.toml titan_chordpro/version.py CHANGELOG.md && rg -n '0\\.1\\.0-c0|0\\.1\\.0c0|Phase C' docs/roadmap.md","expectExitCode":0}
- weight: 2

## Claim report (required output)

Write the claim report JSON to: `.atomic-skills/status/automate/titan-v01-claims.json`

Envelope shape:
```json
{
  "planSlug": "<planSlug>",
  "phaseId": "<phaseId>",
  "worktreePath": "<cwd>",
  "writerBranch": "<branch>",
  "finishedAt": "<ISO>",
  "tasks": [
    {
      "taskId": "T-00N",
      "status": "claimed-pass|claimed-fail|blocked|skipped",
      "commitShas": ["..."],
      "base": null,
      "head": null,
      "paths": ["..."],
      "verifierCommand": "...",
      "exitCode": 0,
      "transcript": "..."
    }
  ]
}
```

Rules:
- Array key is **`tasks`** (canonical; `claims` is a tolerated alias only).
- Open claims need commit identity: non-empty `commitShas[]` **or** `base`+`head`.
- Open claims need `paths[]` ≥1 non-empty path, `verifierCommand`, `exitCode`, `transcript`.
- `claimed-pass` requires `exitCode === 0`.
- Multi-task exclusivity: do not share bare SHAs across open claims without exclusive `base`+`head` per task.
- Prefer exclusive `base`+`head` per task when multi-task commits share SHAs.
- Do not invent pass for missing work-order tasks.

## Exit

1. All listed verifiers green for claimed-pass tasks (self-check).
2. Write claim report to `.atomic-skills/status/automate/titan-v01-claims.json`.
3. Final message: summary of files changed, commit SHAs, claim report path, any blockers.
4. Do not mark tasks done in YAML. Do not call done/phase-done.

---
sealed-brief: true
host-chat-history: excluded

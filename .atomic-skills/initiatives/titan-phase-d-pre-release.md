---
initiative_id: titan-phase-d-pre-release
title: "Titan ChordPro Lib v0.1 Phase D — pre-release docs, demo, LICENSE, tag v0.1.0"
status: pending
branch: main
started: null
last_updated: 2026-05-26T15:00:00Z
plan_link: null
next_action: "Blocked by Phase C completion (v0.1.0-c0 tagged). Then: write Phase D plan, execute D1–D13."
parentPlan: titan-v01
phaseId: F3
max_stack_depth_warning: 5
stack: []
tasks:
  D1: {title: "docs/method.md — pipeline architecture description", status: pending}
  D2: {title: "docs/profiles.md — 5 output profiles + when to use each", status: pending}
  D3: {title: "docs/troubleshooting.md — common errors + actions", status: pending}
  D4: {title: "Demo GIF/video (asciicast or animated GIF of CLI)", status: pending}
  D5: {title: "LICENSE file (MIT) — file missing, README already says MIT", status: pending}
  D6: {title: "CHANGELOG.md — promote [0.1.0c0] to [0.1.0] + add Phase D items", status: pending}
  D7: {title: "git tag v0.1.0 + GitHub release", status: pending}
  D8: {title: "(Optional) PyPI publish", status: pending}
  D9: {title: "CI matrix: enable ubuntu-latest in ci.yml (DoD orphan)", status: pending}
  D10: {title: "Snapshot tests for 5 writer profiles (DoD orphan, deferred since Phase A)", status: pending}
  D11: {title: "Verify chordpro CLI parses chordpro_ref output without errors (DoD orphan)", status: pending}
  D12: {title: "docs/known-issues.md + GitHub issues for known bugs (DoD orphan)", status: pending}
  D13: {title: "Final DoD gate: no P0 open, all checkboxes reviewed (DoD orphan)", status: pending}
parked: []
emerged: []
---

## Context

Phase D is the final v0.1 phase. It picks up after Phase C tags `v0.1.0-c0` and focuses on pre-release polish.

## Scope — what Phase D IS

User-facing documentation (method, profiles, troubleshooting), demo artifact, LICENSE file, CHANGELOG finalization, CI hardening (ubuntu), DoD orphan resolution, and the final `v0.1.0` tag + GitHub release.

## Scope — what Phase D is NOT

- **NOT a corpus re-run.** Phase C T70 already runs all 151 songs. Phase D does not re-run unless post-C fixes require revalidation.
- **NOT a divergence review.** Phase C T70 iter1-iter4 already did this. Henry already classified divergences.
- **NOT Beat F or word offset gating.** Spec §1697-1702 deferred these to Phase D, but they require a labeled corpus (DALI/RWC-Pop/hand-annotated) that does not exist. These gates are aspirational and may be formally cut from the v0.1 DoD.

## Overlap notes (from discover 2026-05-26)

- Roadmap.md items 1-2 ("Tier 3 run 147 songs" + "review top 20") are **redundant** — absorbed by Phase C T70 when corpus was escalated from 30 to 151.
- CHANGELOG is **sequential**: Phase C T73 creates `[0.1.0c0]`; Phase D promotes to `[0.1.0]`.
- README work is **mostly done**: ad-hoc commits added install + quick-start + scripts. Phase C T72 will add badges + validation section. Phase D does not re-touch README unless minor updates are needed.

## Blocked by

Phase C completion — specifically `v0.1.0-c0` tag. Phase C has 3 pending tasks (T71-T73) plus the chord placement blocker from T70-iter4.

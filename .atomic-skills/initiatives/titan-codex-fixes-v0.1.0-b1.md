---
initiative_id: titan-codex-fixes-v0.1.0-b1
title: Hot-fix v0.1.0-b1 — apply Codex cross-model review findings (full-codebase-vs-spec)
status: archived
branch: main
started: 2026-05-18
last_updated: 2026-05-19T00:00:00Z
archived: 2026-05-19
plan_link: .atomic-skills/reviews/2026-05-18-2116-phase-a-b-full-codebase-vs-spec-codex.md
next_action: "ARCHIVED — v0.1.0-b1 tagged + pushed (254d88b on main). Continue to Phase C (F-004 bass-note + corpus harness)."
max_stack_depth_warning: 3
stack: []
tasks:
  F-001: {title: "Export transcribe + ChordProDocument at package root", status: done}
  F-002: {title: "Factory: fail-fast on missing real engines unless force_mock=True", status: done}
  F-003: {title: "Orchestrator: chord placement filter by line span, not section span", status: done}
  F-004: {title: "Chordino bass-note derivation from bass_stem", status: deferred}
  F-005: {title: "Factory: normalize pt-BR / en_US language tags", status: done}
  F-006: {title: "Orchestrator: aggregate StageConfidence per stage into Provenance", status: done}
  F-007: {title: "Orchestrator: restore **engine_overrides signature (spec §API)", status: done}
  F-008: {title: "Hardware: fail-fast when explicit prefer backend unavailable", status: done}
  F-009: {title: "MockSyllabificationEngine: preserve parent_word_idx", status: done}
  TAG: {title: "Tag v0.1.0-b1 + update roadmap + archive initiative", status: done}
parked: []
emerged: []
---

## Context

Cross-model adversarial review (gpt-5-codex via `review-code-with-codex`) of the full v0.1.0-b0 codebase against the design spec found 9 spec-divergence and correctness findings (1B/4C/2M blind → 0B/4C/5M informed; blocker dropped after constraint clarified `chord_extractor` uses subprocess for VAMP host).

The Phase B pre-tag review (2026-05-18-1558) caught 4 findings during execution but did not contrast against the full spec contract — these 9 emerged from the holistic comparison. The user authorized this hot-fix initiative to ship them as v0.1.0-b1 before starting Phase C.

## Notes

- F-004 (bass-note inversions) deferred to Phase C: requires bass-stem chromagram analysis + pitch detection; not a single-edit fix. Will be documented as known v0.1 gap with reference to spec §406.
- F-002 is a policy change (silent mock fallback → fail-fast): integration tests that call `transcribe(audio)` expecting graceful mocks will need `force_mock=True` added. Estimated ~20 LoC test updates.
- Branch strategy: direct commits on main (mirrors Phase B fix commits F-001..F-004 pattern). Tag `v0.1.0-b1` annotated after all fixes + green pytest.
- Review file `.atomic-skills/reviews/2026-05-18-2116-phase-a-b-full-codebase-vs-spec-codex.md` gets "Fixes applied" entries appended per finding.

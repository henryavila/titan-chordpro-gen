---
initiative_id: cuda-mps-validation
title: "Validate chunked alignment on CUDA vs MPS — no quality regression"
status: pending
branch: null
started: null
last_updated: 2026-05-26T15:00:00Z
plan_link: null
next_action: "Blocked: RTX 5070Ti workstation not available. Revisit post v0.1.0-c0."
max_stack_depth_warning: 5
stack: []
tasks:
  V1: {title: "Setup RTX 5070Ti workstation with titan-chordpro dev env", status: pending}
  V2: {title: "Add _align_chunked bool engine kwarg override for A/B testing", status: pending}
  V3: {title: "Run 3-5 corpus songs on both backends, collect word-level timestamps", status: pending}
  V4: {title: "Compare delta mean/p50/p95/max, distribution by position in song", status: pending}
  V5: {title: "Write findings doc + decision (keep chunked or add single-shot path)", status: pending}
parked: []
emerged: []
---

## Context

Phase C T70 introduced chunked emissions + global Viterbi for torchaudio forced alignment (`engines/alignment/torchaudio_align.py`, commit `a5cd9b4`). The theoretical analysis (2s overlap >> 40ms wav2vec2 receptive field) predicts negligible quality loss, but Henry requested empirical validation on CUDA hardware.

## Acceptance criteria

Word-level timestamp delta (chunked vs single-shot) < 20ms mean across 3-5 songs.

## Overlap

Contributes to roadmap v0.2 item "Pipeline tested em RTX 5070Ti (PC Windows)".

## Blocked by

1. RTX 5070Ti workstation setup (v0.2 timeline)
2. Phase C shipped (`v0.1.0-c0` tagged)

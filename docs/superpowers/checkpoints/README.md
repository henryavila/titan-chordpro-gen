# Architectural Checkpoints — Phase A + Phase B

This directory contains **review prompts** Henry passes to an Opus subagent at the end of each Week of implementation (Phase A: Weeks 1-3; Phase B: Weeks 4-7). They exist because Henry chose end-to-end review at each phase tag time but wants cheap architectural validation per-Week to catch bugs that would otherwise compound across weeks.

## How to use

### Trigger condition

When Sonnet finishes a Week and the **Architectural Checkpoint** smoke at the end of that Week section in the plan reports any failure (or even if it passes — these are also good "second-pair-of-eyes" gates).

### Invocation (from Henry, in Claude Code)

```text
Spawn an Opus subagent to do the architectural review described in
docs/superpowers/checkpoints/week-1-review.md (or week-2, week-3).
Pass it the file contents as the prompt and let it run.
```

Or programmatically — Claude reads the file with Read tool and passes its content to `Agent({ subagent_type: "general-purpose", model: "opus", prompt: <file content> })`.

### What you get back

A focused architectural review (300-600 words) reporting:
- **Drift from spec** (schema fields, validators, Protocol method signatures).
- **Drift from plan** (test count mismatches, file structure deviations, missing files).
- **Architectural smells** (circular imports, leaked test-time helpers in runtime, frozen-config violations).
- **Decision points needing human input** (where review found something ambiguous).

It does NOT do detailed line-level code review — that's reserved for the end-to-end review at tag time. Architectural checkpoints stay cheap and focused on the system shape.

## Files

### Phase A (Weeks 1-3, T01-T34, tag `v0.1.0-a0`)

| File | When to use |
|---|---|
| `week-1-review.md` | After Week 1 (T01-T12): schemas + protocols + exceptions + logging |
| `week-2-review.md` | After Week 2 (T13-T20): fusion engine |
| `week-3-review.md` | After Week 3 (T21-T33): writer + mocks + CLI (run BEFORE T34) |
| `final-review.md` | After T34 but BEFORE `git tag v0.1.0-a0` — full architectural review |

### Phase B (Weeks 4-7, T35-T59, tag `v0.1.0-b0`)

| File | When to use |
|---|---|
| `phase-b-week-4-review.md` | After Week 4 (T35-T40): pyproject extras + hardware probe + engines skeleton + BeatThis |
| `phase-b-week-5-review.md` | After Week 5 (T41-T43): htdemucs_ft + cache helper |
| `phase-b-week-6-review.md` | After Week 6 (T44-T47): whisper.cpp + torchaudio forced_align |
| `phase-b-week-7-review.md` | After Week 7 (T48-T53): Chordino + EN/PT lang wrappers — **ESSENTIAL** (license + Phase A surface compat) |
| `phase-b-final-review.md` | After T58 but BEFORE T59 tag step — full architectural review |

## Why this layer exists

Sonnet executes by following the plan's Reference Implementation blocks literally. That eliminates ~90% of execution errors but cannot catch architectural drift caused by the plan ITSELF having a subtle bug (rare but happens) or by the spec having moved since the plan was written. The checkpoints cost ~5 minutes each and catch the remaining 10%.

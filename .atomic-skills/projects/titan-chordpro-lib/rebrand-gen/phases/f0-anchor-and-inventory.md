---
schemaVersion: "0.1"
slug: rebrand-gen-f0-anchor-and-inventory
title: Anchor and inventory
goal: Initiative/branch anchored; MUST_CHANGE inventory confirmed against
  design; no code rename yet.
status: active
branch: plan/rebrand-gen
started: 2026-08-29T02:46:42.203Z
lastUpdated: 2026-08-29T02:46:42.203Z
nextAction: "Start T-001: Ancorar iniciativa / ad-hoc"
parentPlan: rebrand-gen
phaseId: F0
businessIntent:
  value: Acabar a ambiguidade -lib vs UI alinhando repo, PyPI e CLI primary a
    titan-chordpro-gen sem quebrar callers.
  workflow: Inventário MUST_CHANGE → PR de metadata/docs/scripts neste repo →
    rename GitHub+pasta (operator) → pins/paths curta e link NAMING no mesmo
    dia.
  rules: Option A (import titan_chordpro); LEAVE research/superpowers; CLI primary
    titan-chordpro-gen + alias titan-chordpro; não misturar com F2 quality loop;
    slug atomic-skills do projeto não migra agora.
  outOfScope: UI/viewer/editor neste tree; monorepo; app Titan; mudanças
    ML/schemas/profiles; Option B import rename; auto-tag v0.1.0-c0.
  doneWhen: "Handoff §4.7: repo+dir gen, pyproject name gen, README/roadmap Gen,
    import titan_chordpro ok, CLIs --help, checklist preenchido."
tasksDone: 0
tasksTotal: 3
gatesMet: 0
gatesTotal: 0
exitGates: []
stack:
  - id: 1
    title: Anchor and inventory
    type: task
    openedAt: 2026-08-29T02:46:42.203Z
tasks:
  - id: T-001
    title: Ancorar iniciativa / ad-hoc
    summary: Declarar initiative rebrand-gen e deixar F2 pausado
    weight: 1
    description: Declare / materialize initiative for `rebrand-gen` (or explicit
      ad-hoc) matching the working branch; park or leave F2 untouched.
    status: pending
    lastUpdated: 2026-08-29T02:46:42.203Z
  - id: T-002
    title: Congelar inventário MUST_CHANGE
    summary: Lista fechada de arquivos live a editar
    weight: 1
    outputs:
      - kind: file
        path: .atomic-skills/projects/titan-chordpro-lib/rebrand-gen/research-digest.md
    description: Freeze MUST_CHANGE list from `research-digest.md` + design
      (pyproject, uv.lock, README, CLAUDE, roadmap H1, CHANGELOG Unreleased,
      install.sh, live core docstrings, chordino MIT blurb).
    status: pending
    lastUpdated: 2026-08-29T02:46:42.203Z
  - id: T-003
    title: Anotar paths externos curta/viewer
    summary: Paths curta+NAMING para janela F2
    weight: 1
    description: Note curta + chordpro-viewer external paths for the cutover window
      (no edit yet).
    status: pending
    lastUpdated: 2026-08-29T02:46:42.203Z
parked: []
emerged: []
---

# Narrative / notes

Initiative for phase **F0 — Anchor and inventory**.

## Decisions

_(record decisions here as they are made)_

## Links

_(plan doc, external refs)_

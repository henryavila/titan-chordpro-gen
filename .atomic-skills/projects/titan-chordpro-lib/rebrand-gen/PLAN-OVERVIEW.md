# Plano `rebrand-gen` — overview

**Branch / worktree:** `plan/rebrand-gen` em `.worktrees/rebrand-gen`  
**Design:** [design.md](./design.md) (critic **approve**, user approved)  
**titan-v01:** **paused** (F2 quality loop) durante este front

## Decisões travadas

| Item | Decisão |
|------|---------|
| Repo / PyPI | `titan-chordpro-gen` |
| Import | Option A — `titan_chordpro` |
| CLI | Primary `titan-chordpro-gen` + alias `titan-chordpro` |
| Histórico | LEAVE `docs/research` + `docs/superpowers` |
| Cutover | PR deste repo → rename GitHub/pasta (operator) → curta/siblings no mesmo dia |

## Fases

### F0 — Anchor and inventory *(ativa)*
Ancorar o plano e congelar o inventário MUST_CHANGE.

| ID | Resumo |
|----|--------|
| T-001 | Declarar initiative rebrand-gen e deixar F2 pausado |
| T-002 | Lista fechada de arquivos live a editar |
| T-003 | Paths curta+NAMING para janela F2 |

### F1 — This-repo identity flip
Renomear PyPI/docs/CLI neste repo com Option A.

| ID | Resumo |
|----|--------|
| T-010 | pyproject name + dual scripts |
| T-011 | Regenerar uv.lock |
| T-012 | CHANGELOG Unreleased chore |
| T-013 | Docs live README/roadmap/CLAUDE/install |
| T-014 | Docstrings produto Gen |
| T-015 | Verificar pytest/import/CLIs |
| T-016 | Commit/PR deste repo |

### F2 — Operator rename + consumer window
Rename GitHub/pasta + pins curta/siblings no mesmo dia.

| ID | Resumo | Owner |
|----|--------|-------|
| T-020 | Rename GitHub + pasta local | **operator** |
| T-021 | Flip badges README | agent |
| T-022 | Pins/path curta | agent/operator |
| T-023 | NAMING chordpro-viewer | agent |
| T-024 | Polish sda 07b | agent |
| T-025 | Checklist handoff §4.7 | ambos |

## Como executar

```bash
cd /Volumes/External/code/titan-chordpro-lib/.worktrees/rebrand-gen
# depois: implementar F0→F1; operator faz T-020 na janela F2
```

## Artefatos

- `design.md` / `research-digest.md` / `source.md`
- `plan.md` + `phases/f0-anchor-and-inventory.md`
- Sidecars F1/F2: `*.source.json` (materializar fases com `project materialize`)

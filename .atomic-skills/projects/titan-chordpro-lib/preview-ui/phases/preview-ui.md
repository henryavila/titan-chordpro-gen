---
schemaVersion: "0.1"
slug: preview-ui
title: Ponte gen → UI
goal: Operador visualiza ChordPro gerado no ChordproViewer sem colar arquivo à mão.
summary: CLI preview abre o viewer Vue nas cifras geradas.
status: active
branch: plan/preview-ui
started: 2026-09-05T17:24:52Z
lastUpdated: 2026-09-05T17:24:52Z
startedCommit: c15a466cddbe36fc6c94e516a9a11869a5247130
nextAction: Implementar titan_chordpro/preview.py até os testes unitários passarem
parentPlan: preview-ui
phaseId: F0
businessIntent:
  value: Ver a cifra que o gerador acabou de escrever no viewer profissional, não num editor de texto.
  workflow: Gerar ou achar .chordpro → resolver sibling UI → TITAN_PREVIEW_DIR → pnpm dev → browser no ChordproViewer.
  rules: Repos separados; lib sem import de preview; .txt das cifras do harness entram no glob.
  outOfScope: App titan-chordpro; vendor do Vue neste repo; sync de áudio; qualidade WCSR (F2).
  doneWhen: "preview e --preview abrem o demo nas cifras; testes gen+UI passam; as 3 cifras de 2026-08-04 abrem no viewer."
tasksDone: 0
tasksTotal: 3
gatesMet: 0
gatesTotal: 2
weightDone: 0
weightTotal: 3
exitGates:
  - id: F0-G1
    description: pytest tests/unit/test_preview.py e tests/integration/test_cli.py passam
    status: pending
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/test_preview.py tests/integration/test_cli.py
  - id: F0-G2
    description: Demo Vue lista arquivos de TITAN_PREVIEW_DIR em /__titan_preview
    status: pending
    verifier:
      kind: shell
      command: pnpm --dir /Volumes/External/code/titan-chordpro-ui test -- tests/demo
      expectExitCode: 0
stack:
  - id: 1
    title: Ponte gen → UI
    type: task
    openedAt: 2026-09-05T17:24:52Z
tasks:
  - id: T-001
    title: Módulo preview (resolver UI + coletar cifras)
    description: titan_chordpro/preview.py resolve o sibling, coleta .cho/.chordpro/.txt, materializa TITAN_PREVIEW_DIR e sobe o demo via pnpm (injetável nos testes).
    status: active
    lastUpdated: 2026-09-05T17:24:52Z
    summary: Resolver UI e listar cifras sem importar na lib
    weight: 1
    outputs:
      - kind: file
        path: titan_chordpro/preview.py
      - kind: file
        path: tests/unit/test_preview.py
    scopeBoundary:
      - Do not import preview from titan_chordpro/__init__.py
      - Do not copy titan-chordpro-ui into this tree
      - Do not edit titan_chordpro/fusion or engines
      - Do not edit titan_chordpro/cli.py (T-002)
    acceptance:
      - collect_chart_files inclui .txt e .chordpro de um diretório
      - resolve_ui_root prefere TITAN_CHORDPRO_UI e cai no sibling
      - start_preview chama pnpm com TITAN_PREVIEW_DIR e não bloqueia quando wait=False
      - import titan_chordpro não carrega titan_chordpro.preview
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/test_preview.py
  - id: T-002
    title: CLI preview e --preview
    description: Subcomando preview [paths] e flag --preview após transcribe (ou sozinha para a última pasta cifras/).
    status: pending
    lastUpdated: 2026-09-05T17:24:52Z
    summary: titan-chordpro-gen preview abre o demo
    weight: 1
    outputs:
      - kind: file
        path: titan_chordpro/cli.py
      - kind: file
        path: tests/integration/test_cli.py
      - kind: file
        path: scripts/render_from_url.py
    scopeBoundary:
      - Do not change fusion/placement/chord detection
      - Do not bump version or CHANGELOG
      - Do not vendor Vue
    acceptance:
      - titan-chordpro-gen preview --help existe
      - --preview sem audio chama start_preview com as cifras default
      - após transcribe --preview chama start_preview no arquivo escrito
    verifier:
      kind: test
      runner: pytest
      pattern: tests/integration/test_cli.py
  - id: T-003
    title: Demo Vue lê TITAN_PREVIEW_DIR
    description: Plugin Vite /__titan_preview + App.vue troca fixtures pelo catálogo gerado.
    status: pending
    lastUpdated: 2026-09-05T17:24:52Z
    summary: Demo lista cifras do gerador
    weight: 1
    outputs:
      - kind: file
        path: /Volumes/External/code/titan-chordpro-ui/demo/preview-plugin.ts
      - kind: file
        path: /Volumes/External/code/titan-chordpro-ui/demo/preview-catalog.ts
      - kind: file
        path: /Volumes/External/code/titan-chordpro-ui/demo/App.vue
      - kind: file
        path: /Volumes/External/code/titan-chordpro-ui/vite.config.ts
    scopeBoundary:
      - Do not merge gen into the UI package exports
      - Do not rewrite ChordproViewer
      - Do not change core parse/transpose
    acceptance:
      - listPreviewFiles lê .txt e .chordpro do dir
      - GET /__titan_preview devolve JSON files[]
      - fetchPreviewCatalog vazio/204 retorna null
    verifier:
      kind: shell
      command: pnpm --dir /Volumes/External/code/titan-chordpro-ui test -- tests/demo
      expectExitCode: 0
parked: []
emerged: []
---

# Ponte gen → UI

Henry pediu para integrar `/Volumes/External/code/titan-chordpro-ui` a este gerador e usá-lo para visualizar as cifras já geradas (`benchmarks/reports/2026-08-04/cifras/`).

## Decisions

- Não monorepo / não app Titan (NAMING.md do sibling).
- Ponte = env `TITAN_PREVIEW_DIR` + subprocess `pnpm dev` no sibling.
- `.txt` das cifras do harness conta como ChordPro.

## Session handoff

- **Narrative:** Iniciativa ancorada em `plan/preview-ui`. titan-v01 F2 permanece no índice; este branch isola a ponte de preview.
- **Decision log:** Repos separados; CLI costura; lib não importa preview.
- **Single nextAction:** Implementar titan_chordpro/preview.py até os testes unitários passarem
- **Verbatim state:** branch `plan/preview-ui`; HEAD was `c15a466cddbe36fc6c94e516a9a11869a5247130`; cifras em `benchmarks/reports/2026-08-04/cifras/*.txt`
- **Uncommitted changes:** initiative files just written

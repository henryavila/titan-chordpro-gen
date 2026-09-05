---
schemaVersion: "0.1"
slug: preview-ui
title: Preview generated ChordPro in titan-chordpro-ui
version: "1.0"
status: active
started: 2026-09-05T17:24:52Z
lastUpdated: 2026-09-05T17:24:52Z
branch: plan/preview-ui
currentPhase: F0
parallelismAllowed: false
principles:
  - id: P1
    title: Repos ficam separados
    body: "gen lança o demo Vue do sibling titan-chordpro-ui. Nao copiar o viewer para esta arvore, nao criar o app titan-chordpro, nao virar monorepo."
  - id: P2
    title: CLI é a costura
    body: "titan-chordpro-gen preview e --preview apontam TITAN_PREVIEW_DIR para as cifras geradas e sobem o demo."
  - id: P3
    title: Superfície da lib permanece limpa
    body: "import titan_chordpro nao puxa preview, pnpm nem webbrowser."
glossary:
  - term: TITAN_PREVIEW_DIR
    definition: Diretório de .chordpro/.cho/.txt que o demo Vue lista em /__titan_preview.
  - term: sibling UI
    definition: Checkout local de titan-chordpro-ui, default ../titan-chordpro-ui ou env TITAN_CHORDPRO_UI.
phases:
  - id: F0
    slug: preview-ui
    title: Ponte gen → UI
    summary: CLI preview abre o viewer Vue nas cifras geradas.
    goal: Operador visualiza ChordPro gerado no ChordproViewer sem colar arquivo à mão.
    dependsOn: []
    subPhaseCount: 0
    status: active
    businessIntent:
      value: Ver a cifra que o gerador acabou de escrever no viewer profissional, não num editor de texto.
      workflow: Gerar ou achar .chordpro → resolver sibling UI → TITAN_PREVIEW_DIR → pnpm dev → browser no ChordproViewer.
      rules: Repos separados; lib sem import de preview; .txt das cifras do harness entram no glob.
      outOfScope: App titan-chordpro; vendor do Vue neste repo; sync de áudio; qualidade WCSR (F2).
      doneWhen: "preview e --preview abrem o demo nas cifras; testes gen+UI passam; as 3 cifras de 2026-08-04 abrem no viewer."
    exitGate:
      summary: Viewer irmão abre cifras geradas
      criteria:
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
---

# Preview generated ChordPro in titan-chordpro-ui

NAMING lock: gen e ui são repos irmãos. Esta ponte não é o app Titan.

## 1. Context

O gerador escreve `.chordpro` / `.txt` em `benchmarks/reports/*/cifras/` e via CLI. O viewer vive em `titan-chordpro-ui`. Sem ponte, o operador não vê a cifra no ChordproViewer.

## 2. Inviolable principles

Ver frontmatter `principles`.

## 3. Phase tree

F0 único — módulo preview + CLI + demo plugin.

## 4. What stays valid

Pipeline ML, fusion, writer profiles, harness WCSR, contrato `curta`.

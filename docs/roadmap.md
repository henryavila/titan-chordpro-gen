# Titan ChordPro Lib — Roadmap

> **Living document** — Atualize sempre que mudar status de uma tarefa, terminar uma fase, ou repriorizar. Substitui o `docs/research/00-original-roadmap.md` (artefato histórico de pesquisa inicial).
>
> **Última atualização:** 2026-05-17
> **Fase atual:** Phase A completa — v0.1.0-a0 tagueado
> **Próxima milestone:** v0.1.0 (Phase B — ML integration)

## Status legend

| Símbolo | Significado |
|---|---|
| ✅ | Done |
| 🚧 | In progress |
| ⏳ | Not started (planejado) |
| ⏸ | Deferred (postponed para versão futura) |
| ❌ | Cancelled (não será feito) |
| ⚠️ | Blocked (esperando algo externo) |

## Quick links

- **Research:** [`docs/research/`](research/) (10 arquivos: 9 streams + síntese)
- **Design spec:** `docs/superpowers/specs/` (drafts em `drafts/`, consolidado pendente)
- **Implementation plan:** TBD (gerado por `writing-plans` skill após consolidação do spec)
- **Original roadmap (histórico):** [`docs/research/00-original-roadmap.md`](research/00-original-roadmap.md)

---

## Phase 0 — Research + Design (em conclusão)

### Research streams (`docs/research/`)

| # | Tópico | Arquivo | Status |
|---|---|---|---|
| 1 | Source separation SOTA | [`01-source-separation.md`](research/01-source-separation.md) | ✅ |
| 2 | Transcription + word alignment | [`02-transcription-and-alignment.md`](research/02-transcription-and-alignment.md) | ✅ |
| 3 | Chord recognition | [`03-chord-recognition.md`](research/03-chord-recognition.md) | ✅ |
| 4 | Beat tracking + meter | [`04-beat-tracking.md`](research/04-beat-tracking.md) | ✅ |
| 5 | ChordPro format spec | [`05-chordpro-format.md`](research/05-chordpro-format.md) | ✅ |
| 6 | Hardware + platform strategy | [`06-hardware-platforms.md`](research/06-hardware-platforms.md) | ✅ |
| 7 | Competitive landscape + MVP | [`07-competitive-landscape.md`](research/07-competitive-landscape.md) | ✅ |
| 8 | Tab + solo transcription | [`08-tab-and-solo.md`](research/08-tab-and-solo.md) | ✅ |
| 9 | Chord-on-syllable algorithm | [`09-chord-on-syllable.md`](research/09-chord-on-syllable.md) | ✅ |
| ∑ | Synthesis (TL;DR) | [`00-synthesis.md`](research/00-synthesis.md) | ✅ |

### Design sections (`docs/superpowers/specs/drafts/`)

| # | Seção | Arquivo | Status |
|---|---|---|---|
| 1 | Architecture overview + Module structure | `section-1-architecture.md` | ✅ Aprovado |
| 2 | Engine Protocols + Schemas | `section-2-protocols-and-schemas.md` | ✅ Aprovado |
| 3 | Fusion Engine algorithm | `section-3-fusion-engine.md` | ✅ Aprovado |
| 4 | ChordPro Writer + Output Profiles | `section-4-writer-and-profiles.md` | ✅ Aprovado |
| 5 | Error handling + Testing strategy | `section-5-error-handling-and-testing.md` | ✅ Aprovado |
| 6 | Sequencing + Definition of Done | `section-6-sequencing-and-done.md` | ✅ Aprovado |

### Pre-implementation closeout

| Tarefa | Status |
|---|---|
| Consolidar 6 seções em [`docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`](superpowers/specs/2026-05-09-titan-v0.1-design.md) | ✅ |
| Spec self-review (placeholders, contradições, scope) | ✅ |
| User review do spec consolidado | ✅ Aprovado |
| Invocar `superpowers:writing-plans` → [`docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md`](superpowers/plans/2026-05-12-titan-v0.1-phase-a.md) | ✅ Phase A plan escrito (34 tasks) |

---

## v0.1.0 — Phase A: Foundation (no GPU) | Semanas 1-3 ✅ COMPLETA

### Week 1 — Bootstrap + schemas + protocols

| Tarefa | Status |
|---|---|
| `pyproject.toml` (deps, extras `[mac]/[cuda]/[dev]`) | ✅ |
| Repo layout (`titan_chordpro/`, `tests/`, `docs/`, `benchmarks/`) | ✅ |
| Pre-commit hooks (ruff format, ruff check, mypy) | ✅ |
| `core/schemas.py` (todos schemas Pydantic da Seção 2) | ✅ |
| `core/protocols.py` (6 Engine Protocols) | ✅ |
| `core/exceptions.py` (TitanError hierarchy + 8 subclasses) | ✅ |
| Unit tests para schemas (validação Pydantic) | ✅ |

### Week 2 — Fusion engine (IP central)

| Tarefa | Status |
|---|---|
| `fusion/syllabifier.py` (Maximum Onset Principle + orthographic fallback) | ✅ |
| `fusion/stress.py` (PT orthographic + EN CMU dict via g2p_en) | ✅ |
| `fusion/beat_snap.py` (±70ms / ±150ms tolerâncias) | ✅ |
| `fusion/onset_fusion.py` (v0.1: chord+beat) | ✅ |
| `fusion/melisma.py` (heurística simples) | ✅ |
| `fusion/sectioner.py` (heurística baseada em gaps) | ✅ |
| `fusion/placer.py` (algoritmo de placement com 5 estratégias) | ✅ |
| Unit tests por módulo do fusion (~90% coverage target) | ✅ |

### Week 3 — Writer + CLI + CI + corpus export

| Tarefa | Status |
|---|---|
| `writer/profiles/inline_slash.py` (default) | ✅ |
| `writer/profiles/chordpro_ref.py` | ✅ |
| `writer/profiles/onsong.py` | ✅ |
| `writer/profiles/propresenter.py` | ✅ |
| `writer/profiles/songbookpro.py` | ✅ |
| `writer/serializer.py` (ChordProDocument → string) | ✅ |
| `cli.py` (argparse + entry point `titan-chordpro`) | ✅ |
| `factory.py` (engine selection com hardware detection) | ✅ |
| `.github/workflows/ci.yml` (matrix macOS-14 + ubuntu) | ⏸ Deferred — não bloqueia Phase A |
| `tests/conftest.py` (mock engines pytest fixtures) | ✅ |
| `benchmarks/export_corpus.py` (SQL → JSON) | ✅ stub |
| `tests/corpus-export.json` (run inicial do export, ~147 songs) | ⏸ Deferred to Phase C |
| Snapshot tests dos 5 profiles | ⏸ Deferred — cobertura 93% via unit tests |

**Validação fim Phase A:**
- [x] Pipeline com mocks rodando end-to-end (259 testes, 93% cobertura)
- [x] Coverage ≥ 80% em `core/` e `fusion/` (93% total)
- [ ] CI passando em ambas plataformas (deferred)
- [x] `titan-chordpro tests/fixtures/silent.wav` produz ChordPro válido

---

## v0.1.0 — Phase B: ML Integration (Mac-first) | Semanas 4-7

### Week 4 — BeatThis (beat tracking)

| Tarefa | Status |
|---|---|
| `engines/beat/beatthis.py` (BeatThis MIT, PyTorch CUDA+MPS) | ⏳ |
| Integration test: F-measure > 0.85 em snippets | ⏳ |
| EngineInfo correctly reports backend (mps/cuda/cpu) | ⏳ |

### Week 5 — htdemucs_ft (separation)

| Tarefa | Status |
|---|---|
| `engines/separation/htdemucs.py` via `python-audio-separator` | ⏳ |
| Integration test: 4 stems gerados, audible | ⏳ |
| Cache integration (opt-in via `cache=True`) | ⏳ |

### Week 6 — whisper.cpp + alignment

| Tarefa | Status |
|---|---|
| `engines/transcription/whisper_cpp.py` via `pywhispercpp` | ⏳ |
| `engines/alignment/torchaudio_align.py` (forced alignment MPS+CUDA) | ⏳ |
| Integration test: word-level offset mediano < 100ms | ⏳ |

### Week 7 — Chordino + EN syllabifier

| Tarefa | Status |
|---|---|
| `engines/chord/chordino.py` via `chord-extractor` (VAMP plugin) | ⏳ |
| `engines/lang/english.py` (g2p_en + CMU stress) | ⏳ |
| `engines/lang/portuguese.py` (gruut + orthographic stress) | ⏳ |
| Integration test: chord events com bass note correto | ⏳ |
| Setup script para VAMP plugin (brew install vamp-plugin-sdk) | ⏳ |

**Validação fim Phase B:**
- [ ] Pipeline real end-to-end nas 6 músicas PT-BR
- [ ] Tier 1 CI tests passando com engines reais
- [ ] Output `.chordpro` "razoável" (subjective review do owner)

---

## v0.1.0 — Phase C: End-to-end + Validation harness | Semanas 8-9

### Week 8 — Validation harness (Tier 2+3)

| Tarefa | Status |
|---|---|
| `benchmarks/audio_downloader.py` (yt-dlp wrapper, cache local) | ⏳ |
| `benchmarks/validation_runner.py` (pipeline + mir_eval metrics) | ⏳ |
| `benchmarks/divergence_ranker.py` (severity scoring CRITICAL/HIGH/MEDIUM/LOW/NEGLIGIBLE) | ⏳ |
| `.github/workflows/nightly.yml` (cron daily 06:00 UTC) | ⏳ |
| Tier 2 sample stratification (slash chords, 6/8, melisma, etc.) | ⏳ |

### Week 9 — Tier 2 nightly + iteração + polish

| Tarefa | Status |
|---|---|
| Primeira run nightly (30 songs) | ⏳ |
| Review top 10 divergências | ⏳ |
| Fix bugs descobertos | ⏳ |
| Polish CLI (mensagens de erro, progress bars via rich) | ⏳ |
| `README.md` (badges, install, invocation, demo) | ⏳ |

**Validação fim Phase C:**
- [ ] Tier 2 metrics: WCSR-majmin ≥ 70%
- [ ] Beat F-measure ≥ 0.85
- [ ] Word alignment median offset < 100ms
- [ ] Top 10 divergências revisadas (≤ 3 são "Titan errado")

---

## v0.1.0 — Phase D: Pre-release | Semana 10

| Tarefa | Status |
|---|---|
| Run Tier 3 completa (147 songs) | ⏳ |
| Review top 20 divergências | ⏳ |
| `docs/method.md` (descrição do pipeline) | ⏳ |
| `docs/profiles.md` (5 output profiles + quando usar) | ⏳ |
| `docs/troubleshooting.md` (erros comuns + ações) | ⏳ |
| `CHANGELOG.md` v0.1.0 | ⏳ |
| Demo GIF/video | ⏳ |
| `LICENSE` MIT | ⏳ |
| `git tag v0.1.0` + GitHub release | ⏳ |
| (Opcional) PyPI publish | ⏳ |

---

## Definition of Done — v0.1.0

### Funcionalidade
- [ ] CLI `titan-chordpro song.mp3` produz `.chordpro` válido
- [ ] CLI suporta `--profile=`, `--language=`, `--output=`, `--keep-stems`, `--cache`
- [ ] Library API: `transcribe()` + `doc.write()` + `doc.to_string()`
- [ ] Pipeline funciona em Apple Silicon (M4)
- [ ] `inline_slash` é default

### Qualidade
- [ ] Tier 1 CI passando em macOS-14 + ubuntu-latest
- [ ] Coverage ≥ 80% (gate)
- [ ] Tier 2 nightly: WCSR-majmin ≥ 70%, Beat F ≥ 0.85
- [ ] Tier 3 pre-release: top 20 divergências revisadas
- [ ] Snapshot tests dos 5 profiles passando
- [ ] `chordpro` CLI parseia output do `chordpro_ref` sem erros

### Documentação
- [ ] README com badge, install, invocation, demo
- [ ] `docs/method.md`, `docs/profiles.md`, `docs/troubleshooting.md`
- [ ] CHANGELOG.md
- [ ] Demo GIF/video

### Distribuição
- [ ] `pyproject.toml` com extras `[mac]`, `[cuda]`
- [ ] `LICENSE` MIT
- [ ] CI + nightly workflows

### Sem regressões
- [ ] `docs/known-issues.md` se houver bugs conhecidos
- [ ] Cada known issue tem GitHub issue
- [ ] Nenhum bug bloqueador (P0) aberto

---

## v0.2 — Roadmap (preview, ~3 meses pós-v0.1)

**Tema:** "CUDA + Apple Silicon dual-platform completo"

| Tarefa | Status |
|---|---|
| Fork BTC-ISMIR19 → port PyTorch 2.x + MPS | ⏸ Deferred to v0.2 |
| `engines/transcription/mlx_whisper.py` (Apple Silicon fast-path) | ⏸ |
| `engines/transcription/faster_whisper.py` (CUDA fast-path) | ⏸ |
| `engines/separation/demucs_mlx.py` (~73× realtime no M4) | ⏸ |
| Pipeline tested em RTX 5070Ti (PC Windows) | ⏸ |
| Multi-evidence onset fusion (`fuse_onsets_v02`): bass + vocal onset | ⏸ |
| Acoustic prosody fallback no stress detection | ⏸ |
| All-In-One model integration (sectioning + chord + beat joint) | ⏸ |
| Vocab `extended_170` no chord engine (BTC-ISMIR19 nativo) | ⏸ |
| Variable BPM handling | ⏸ |

---

## v0.3 — Roadmap (preview, ~6 meses pós-v0.1)

**Tema:** "Solo / tab (approximate) + extensões harmônicas"

| Tarefa | Status |
|---|---|
| Solo → first-draft ASCII tab inside `{sot}/{eot}` (watermarked approximate) | ⏸ |
| Vocab estendido com sus, add9, dim, aug | ⏸ |
| Meter change detection (4/4 → 6/8 mid-song) | ⏸ |
| Key change / modulation detection | ⏸ |
| ChordFormer / BACHI integration (se code público) | ⏸ |
| Pre-chorus detection | ⏸ |

---

## Phase 2 — Sibling projects (vision, ~6-12 meses pós-v0.1)

**Tema:** "Editor visual + learning loop"

Projetos separados deste repo:

| Projeto | Linguagem | Status |
|---|---|---|
| `titan-chordpro-render` | TypeScript/JS | ⏸ Repo não criado ainda |
| `titan-chordpro-theme-default` | CSS | ⏸ |
| Editor app (drag-to-correct) | TBD framework web | ⏸ |
| `LearnableChordEngine` (volta na lib Python) | Python | ⏸ Schema `CorrectionLog` já em v0.1 |

---

## Updates log

> Adicione aqui mudanças significativas no roadmap. Mantenha cronológico, mais recente em cima.

### 2026-05-17
- ✅ Phase A completa — 259 testes passando, 92.55% coverage, pipeline end-to-end funcional.
- ✅ `v0.1.0-a0` tagueado.
- 📌 Próximo: Phase B — ML integration (BeatThis → htdemucs → whisper.cpp → Chordino).

### 2026-05-12
- ✅ Spec aprovado.
- ✅ Phase A implementation plan escrito em [`docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md`](superpowers/plans/2026-05-12-titan-v0.1-phase-a.md) — 34 tasks atômicas, ~3 semanas de trabalho.
- 📌 Próximo: escolher modo de execução (Subagent-Driven ou Inline Execution) e começar T01.

### 2026-05-09
- ✅ Spec consolidado em [`docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`](superpowers/specs/2026-05-09-titan-v0.1-design.md).
- ✅ Spec self-review completo. Inconsistências corrigidas inline:
  - `placement_strategy` enum agora tem 5 valores em todas as referências
  - `ChordProDocument.to_string/write` default fixado em `inline_slash`
  - Mock engines atualizados (sem `supports_phoneme_alignment` que foi removido do Protocol)
  - `AlignmentEngine` docstring corrigida
  - Edge case 4 reescrito (orphan flow vs end-of-line antigo)
  - Drafts originais preservados em `docs/superpowers/specs/drafts/` para histórico
- 🚧 Aguardando user review do spec consolidado.
- 📌 Próximo: invocar `superpowers:writing-plans`.

### 2026-05-08
- 📝 Roadmap criado consolidando 9 streams de pesquisa + 6 seções de design aprovadas.
- ✅ Phase 0 (Research + Design) concluída exceto consolidação do spec + writing-plans.
- 📌 Próximo: consolidar drafts em spec final + invocar `writing-plans`.

<!-- Adicione novas entradas acima desta linha -->

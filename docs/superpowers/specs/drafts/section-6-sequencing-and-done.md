# Design — Seção 6: Implementation Sequencing + Definition of Done

> Parte 6 de 6 (final) do design do Titan ChordPro Lib v0.1.
> Esta seção define a **ordem de execução** das fases de implementação, **critérios de done** para v0.1, e o **roadmap pós-v0.1** (v0.2, v0.3, phase 2).
> Data: 2026-05-08

---

## Princípio de sequenciamento

**Foundation-first, ML-last.** Construir todo o pipeline pure-Python (schemas, protocols, mocks, fusion, writer) ANTES de plugar qualquer engine de ML. Razões:

1. Pipeline com mocks já produz `.chordpro` válido — feedback imediato sobre design
2. ML engines viram "swap implementations" sem refactor — cada um é commit isolado
3. Bugs de orchestration / fusion são pegos cedo, sem ruído de ML inference
4. Owner pode trabalhar **sem GPU** nas fases A e D, **sem PC ligado** durante tudo (Mac-first)

---

## Fases de implementação v0.1

### Fase A — Foundation (no GPU, no ML) | Semanas 1-3

| Semana | Trabalho | Entregáveis |
|---|---|---|
| **1** | Bootstrap + schemas + protocols | `pyproject.toml`, repo layout, pre-commit, ruff/mypy config, `core/schemas.py` (todos schemas Pydantic da Seção 2), `core/protocols.py` (6 Engine Protocols), `core/exceptions.py` (hierarchy) |
| **2** | Fusion engine — IP central | `fusion/syllabifier.py` (Maximum Onset Principle), `fusion/stress.py` (PT orthographic + EN CMU), `fusion/beat_snap.py`, `fusion/onset_fusion.py` (v0.1: chord+beat), `fusion/melisma.py`, `fusion/sectioner.py`, `fusion/placer.py` (placement algorithm com 5 estratégias) |
| **3** | Writer + CLI + CI + test infra | `writer/profiles/` (5 profiles), `writer/serializer.py`, `cli.py`, `factory.py` (engine selection), GitHub Actions matrix (macOS-14 + ubuntu-latest), mocks pytest fixtures, `tests/corpus-export.json` (DB export do owner), `benchmarks/export_corpus.py` |

**Validação no fim de Fase A:**
- Pipeline com mocks rodando end-to-end → output `.chordpro` válido
- Suíte de testes unitários ≥ 80% coverage em `core/` e `fusion/`
- CI passando em ambas plataformas
- Snapshot tests dos 5 profiles passando contra fixtures fake

**Sem GPU. Sem PC Windows ligado. Tudo no Mac.**

---

### Fase B — ML integration (Mac-first) | Semanas 4-7

| Semana | Engine | Entregáveis |
|---|---|---|
| **4** | BeatThis (beat tracking) | `engines/beat/beatthis.py`. Mais simples — pure PyTorch, MPS funciona limpo. Validação: F-measure > 0.85 nos snippets de teste |
| **5** | htdemucs_ft (separation) | `engines/separation/htdemucs.py` via `python-audio-separator`. Validação: 4 stems gerados, audible, correct sample rate |
| **6** | whisper.cpp + alignment | `engines/transcription/whisper_cpp.py` via `pywhispercpp`, `engines/alignment/torchaudio_align.py`. Validação: word-level timestamps com offset mediano < 100ms vs ground truth |
| **7** | Chordino + EN syllabifier | `engines/chord/chordino.py` via `chord-extractor`, `engines/lang/english.py` (g2p_en). Validação: chord events com bass note, EN syllabification produz stress markers corretos |

**Validação no fim de Fase B:**
- Pipeline real end-to-end nas 6 músicas PT-BR cadastradas
- Tier 1 CI tests passando com engines reais
- Output `.chordpro` é "razoável" (subjective review do owner)
- Cada engine integrado tem teste específico que valida `EngineInfo` correto + invariants

**Mac-first. PC Windows continua desligado.**

---

### Fase C — End-to-end + validation harness | Semanas 8-9

| Semana | Trabalho | Entregáveis |
|---|---|---|
| **8** | Validation harness (Tier 2+3) | `benchmarks/audio_downloader.py` (yt-dlp), `benchmarks/validation_runner.py` (pipeline + mir_eval metrics), `benchmarks/divergence_ranker.py` (severity scoring) |
| **9** | Tier 2 nightly running + iteração | Cron de nightly funcionando; primeira run de 30 songs estratificadas; review top 10 divergências; correções de bugs críticos descobertos. Polish da CLI, mensagens de erro, README |

**Validação no fim de Fase C:**
- Tier 2 metrics: WCSR-majmin ≥ 70% nos 30 songs sample (ajustável por categoria)
- Beat F-measure ≥ 0.85
- Word alignment median offset < 100ms
- Top 10 divergências revisadas; ≤ 3 são "Titan errado" (resto são charts errados ou ambiguous)

---

### Fase D — Pre-release | Semana 10

| Trabalho | Entregáveis |
|---|---|
| Tier 3 full validation | Run completa nos 147 songs; report final em `benchmarks/reports/v0.1.0/`; review top 20 divergências |
| Documentação final | README com install + invocation, `docs/method.md` descrevendo pipeline, `CHANGELOG.md`, `LICENSE` (MIT) |
| Demo materials | Demo GIF/video de input → `.chordpro` → rendered PDF |
| Release | `git tag v0.1.0`, GitHub release com release notes, PyPI publish (opcional v0.1, certain v0.1.x) |

**Definition of Done de v0.1 (checklist abaixo).**

**Total estimado:** ~10 semanas de trabalho focado. Considerando que projeto é side-project, calendário real provavelmente 3-5 meses.

---

## Definition of Done — v0.1.0

Checklist canonical para tag `v0.1.0`:

### Funcionalidade

- [ ] CLI `titan-chordpro song.mp3` produz `.chordpro` válido
- [ ] CLI suporta `--profile=` (5 profiles)
- [ ] CLI suporta `--language=`, `--output=`, `--keep-stems`, `--cache`
- [ ] Library API: `from titan_chordpro import transcribe; doc = transcribe(...)` funciona
- [ ] `doc.write(path, profile)` e `doc.to_string(profile)` funcionam
- [ ] Pipeline funciona em **Apple Silicon (M4)** (production target primário)
- [ ] Output profile `inline_slash` é default; render compatível com OnSong, ProPresenter, SongbookPro, iasdermelinda

### Qualidade

- [ ] Tier 1 CI passando em macOS-14 + ubuntu-latest
- [ ] Coverage ≥ 80% (gate)
- [ ] Tier 2 nightly: WCSR-majmin ≥ 70%, Beat F-measure ≥ 0.85
- [ ] Tier 3 pre-release: 147 songs rodadas, top 20 divergências revisadas
- [ ] Snapshot tests dos 5 profiles passando
- [ ] `chordpro` CLI parseia o output do profile `chordpro_ref` sem erros

### Documentação

- [ ] `README.md` com badge de status, single-line install, single-line invocation
- [ ] `docs/method.md` descrevendo o pipeline (5 engines + fusion + output)
- [ ] `docs/profiles.md` documentando os 5 output profiles e quando usar cada
- [ ] `docs/troubleshooting.md` com mensagens de erro comuns + ações
- [ ] `CHANGELOG.md` documenting v0.1.0 features
- [ ] Demo GIF ou video curto

### Distribuição

- [ ] `pyproject.toml` com extras `[mac]`, `[cuda]` (mesmo que CUDA seja v0.2)
- [ ] `LICENSE` MIT
- [ ] `.github/workflows/ci.yml` + `.github/workflows/nightly.yml`
- [ ] (Opcional) PyPI publish — pode ficar para v0.1.1

### Sem regressões conhecidas

- [ ] Lista de bugs conhecidos em `docs/known-issues.md`
- [ ] Cada bug conhecido tem issue no GitHub
- [ ] Nenhum bug bloqueador (P0) aberto

---

## Estratégia de mitigação de riscos

| Fase | Risco | Probabilidade | Mitigação |
|---|---|---|---|
| A | Schema design errado emerge tarde | Baixa | Pydantic + testes precoces; refactor barato em pure Python |
| A | Algoritmo de fusion não produz placement legível | Média | Snapshot tests com ground truth manualmente anotado das 6 songs; iteração rápida com mocks |
| B | BeatThis MPS tem operador sem kernel | Baixa | Fallback para CPU dentro do engine; impacto: ~5x mais lento mas funcional |
| B | whisper.cpp Python binding incompleto | Média | Plan B: usar `whisper.cpp` via subprocess CLI (mais lento mas funciona); contributção upstream se gap pequeno |
| B | Chordino instalação no Mac (VAMP plugin) | Média | Documentar setup script; brew install vamp-plugin-sdk; fallback: temporário com `chord-extractor` raiz se VAMP plugin falhar |
| C | Tier 2 metrics abaixo do threshold (WCSR < 70%) | Média | Análise de top divergências por edge case; pode ser bug fix simples (placement bug) ou indicar Chordino limitations (esperado v0.1) |
| C | Audio download muito lento (147 yt-dlp serial) | Baixa | Paralelismo via `concurrent.futures`; rate limit do YouTube documentado |
| D | Top 20 divergências revelam problema sistemático | Baixa-Média | Atrasar release v0.1.0 e implementar fix. Tags de "preview" (`v0.1.0-rc.1`) podem ser uses para validação intermediária |

---

## Roadmap pós-v0.1

### v0.2 (~3 meses pós-v0.1)

**Tema:** "CUDA + Apple Silicon dual-platform completo"

- BTC-ISMIR19 fork + porting para PyTorch 2.x + MPS (vocab 170-class incl. slash chords nativo)
- mlx-whisper como Apple Silicon fast-path (alternativa a whisper.cpp)
- demucs-mlx para Apple Silicon (separação ~73× realtime no M4)
- faster-whisper como CUDA fast-path
- Pipeline completo testado em RTX 5070Ti (PC Windows)
- Multi-evidence onset fusion (`fuse_onsets_v02`): bass + vocal onset detection
- Acoustic prosody fallback no stress detection (EN ambiguous cases)
- All-In-One model integration: sectioning + chord + beat joint (substitui sectioner heurístico)

### v0.3 (~6 meses pós-v0.1)

**Tema:** "Solo / tab (approximate) + extensões harmônicas"

- Solo → first-draft ASCII tab inside `{sot}/{eot}` (approximate, watermarked)
- Vocab `extended_170` no chord engine (BTC-ISMIR19 expanded)
- Meter change detection (4/4 → 6/8 mid-song)
- Key change / modulation detection
- Variable tempo handling (gradual or sudden BPM changes)
- ChordFormer / BACHI integration if code becomes public

### Phase 2 (~6-12 meses pós-v0.1, projeto separado)

**Tema:** "Editor visual + learning loop"

Sibling projects (separados do `titan-chordpro-lib`):

- **`titan-chordpro-render`** (TypeScript/JS): ChordProDocument JSON → semantic HTML com data-attrs ricos
- **`titan-chordpro-theme-default`** (CSS): tema referência (light/dark, accessible, mono)
- **Editor app** (TBD framework): web app que usa render + adiciona drag-to-correct, captura `Correction`s no schema do v0.1, salva `CorrectionLog`
- **`LearnableChordEngine`** (de volta na lib Python): wraps base ChordRecognitionEngine + aplica `CorrectionLog`. Loop de melhoria: usuário corrige → próxima run aprende

---

## Como ler este spec depois (para futuro Claude / contributor)

Este spec foi consolidado de 6 seções de design + 9 streams de pesquisa em `docs/research/`. Para recuperar contexto:

1. Comece por `docs/research/00-synthesis.md` (TL;DR + decisões macro)
2. Para cada subsistema, consulte:
   - `docs/research/01-source-separation.md` — Module A
   - `docs/research/02-transcription-and-alignment.md` — Module B
   - `docs/research/03-chord-recognition.md` — Module C
   - `docs/research/04-beat-tracking.md` — Module D
   - `docs/research/05-chordpro-format.md` — Module E (output)
   - `docs/research/06-hardware-platforms.md` — strategy decisions
   - `docs/research/07-competitive-landscape.md` — gap + MVP
   - `docs/research/08-tab-and-solo.md` — solo/tab feasibility
   - `docs/research/09-chord-on-syllable.md` — fusion engine algorithm
3. Este spec consolidado: `docs/superpowers/specs/2026-05-08-titan-v0.1-design.md` (após consolidação das 6 seções)

---

## Pontos para review

- **Estimativa de 10 semanas focadas / 3-5 meses calendário** — realista pela tua disponibilidade ou ajustar?
- **Fase B engine order** — BeatThis primeiro (mais simples), Chordino último (mais arriscado). OK ou prefere outra ordem?
- **Definition of Done — WCSR ≥ 70% como threshold** — adequado para baseline Chordino (~75-80% paper) ou ajustar?
- **v0.2 timeline ~3 meses pós-v0.1** — agressivo demais ou OK considerando que abstração já está pronta?
- **Phase 2 fora desta lib** — confirmado e documentado em Seções 1 e 4. OK?
- **`docs/troubleshooting.md` no DoD** — vale o esforço inicial ou popular ao longo de 0.1.x conforme bugs aparecem?
- **`v0.1.0-rc.X` preview tags** — adoptar ou ir direto para `v0.1.0`?

Quando terminar o review, me avise no chat — depois consolido as 6 seções no spec final + invoco `writing-plans`.

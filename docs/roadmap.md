# Titan ChordPro Lib — Roadmap

> **Living document** — Atualize sempre que mudar status de uma tarefa, terminar uma fase, ou repriorizar. Substitui o `docs/research/00-original-roadmap.md` (artefato histórico de pesquisa inicial).
>
> **Última atualização:** 2026-08-04
> **Fase atual:** Phase C — ✅ closed at package `0.1.0c0` (ready for operator tag `v0.1.0-c0`)
> **Versão no código:** `0.1.0c0`
> **Próxima milestone:** Henry tags `v0.1.0-c0` after final review → Phase D

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
- **Design spec:** [`docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`](superpowers/specs/2026-05-09-titan-v0.1-design.md)
- **Phase C plan:** [`docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md`](superpowers/plans/2026-05-19-titan-v0.1-phase-c.md)
- **T70 placement handoff:** [`docs/superpowers/handoff-phase-c-iter4-placement.md`](superpowers/handoff-phase-c-iter4-placement.md)
- **Original roadmap (histórico):** [`docs/research/00-original-roadmap.md`](research/00-original-roadmap.md)
- **Project status:** [`.atomic-skills/PROJECT-STATUS.md`](../.atomic-skills/PROJECT-STATUS.md)

---

## Phase 0 — Research + Design ✅ COMPLETA

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

### Design sections + closeout

| Tarefa | Status |
|---|---|
| 6 seções em `docs/superpowers/specs/drafts/` | ✅ Aprovado |
| Spec consolidado [`2026-05-09-titan-v0.1-design.md`](superpowers/specs/2026-05-09-titan-v0.1-design.md) | ✅ |
| Phase A plan (34 tasks) | ✅ |

---

## v0.1.0 — Phase A: Foundation (no GPU) | Semanas 1-3 ✅ COMPLETA

Tag: **`v0.1.0-a0`** (2026-05-17) — 259 testes, ~93% coverage.

| Week | Entregas | Status |
|---|---|---|
| 1 | Bootstrap, schemas, protocols, exceptions | ✅ |
| 2 | Fusion engine (syllabifier, stress, beat_snap, onset_fusion, melisma, sectioner, placer) | ✅ |
| 3 | Writer 5 profiles, CLI, factory, orchestrator, mocks | ✅ |

**Deferred from A (still open in DoD where noted):**
- Snapshot tests dos 5 profiles → Phase D
- CI dual-platform — **later landed** in Phase B (see Phase B)

---

## v0.1.0 — Phase B: ML Integration (Mac-first) | Semanas 4-7 ✅ COMPLETA

Tags: **`v0.1.0-b0`** (2026-05-18) → hot-fix **`v0.1.0-b1`** (2026-05-19).

| Week | Engine / entrega | Status |
|---|---|---|
| 4 | BeatThis beat tracking | ✅ |
| 5 | htdemucs_ft separation (`audio-separator`) | ✅ |
| 6 | whisper.cpp + torchaudio forced alignment | ✅ |
| 7 | Chordino (VAMP) + gruut PT + g2p_en EN | ✅ |
| — | CI matrix macOS-14 + ubuntu-latest | ✅ |
| — | Codex hot-fix b1 (8/9 findings; F-004 → Phase C) | ✅ |

---

## v0.1.0 — Phase C: End-to-end + Validation harness | Semanas 8-9 ✅ CLOSED (c0 ready)

**Initiative:** `titan-phase-c` / plan `titan-v01` F2  
**Package version:** **`0.1.0c0`**  
**Git tag:** `v0.1.0-c0` — **operator-owned** (do not auto-tag; Henry after final review)

### Week 8 — Validation harness + F-004 + cache

| Tarefa | Status |
|---|---|
| T60 — `[validation]` extra + `docs/setup-validation.md` | ✅ |
| T61 — `benchmarks/corpus.py` (songs.csv → Song) | ✅ |
| T62 — `benchmarks/audio_downloader.py` (yt-dlp + disk cache) | ✅ |
| T63/T64 — F-004 `bass_chroma.py` + Chordino inversions | ✅ |
| T65/T66 — cache `dump_stage`/`load_stage` + orchestrator wiring | ✅ |
| T67 — `validation_runner` + `metrics` + `chordpro_parser` | ✅ |
| T67b — Beat F cross-librosa diagnostic; gates honestas (WCSR + top-N) | ✅ |
| T68 — `divergence_ranker` + `benchmarks/reports/` | ✅ |
| T69 — `.github/workflows/nightly.yml` + marker `corpus_full` | ✅ |
| Chordino arm64 build from source + `install_vamp.sh` rewrite | ✅ |
| whisper default `medium` + word-level + anti-hallucination | ✅ |
| Adaptive sectioner; surface `beat_grid` on document | ✅ |
| Align chunked emissions; GPU release between stages | ✅ |

### Week 9 — Sample iteration + polish

| Tarefa | Status |
|---|---|
| **T70** — Sample / quality loop (detection + placement) | ⚠️ shipped improvements; WCSR gate **not met** (~0.26 sample) |
| T70-iter2 — 4 gaps (chordino offline, whisper base, sectioner, gates) | ✅ |
| T70-iter3 — word-level whisper, adaptive sectioner, anti-hallucination | ✅ |
| T70-iter4 — placement diagnosis (stacking report) | ✅ |
| T70-iter5 — structural fixes (reindex, orphans, sectioner coverage, stress, beat_snap) | ✅ 2026-08-04 |
| T70-iter6 — harmonic mix, chord postprocess, placer destack | ✅ 2026-08-04 (WCSR 0.211→0.259) |
| T71 — CLI rich progress + `--validate` | ✅ |
| T72 — README badges + validation section | ✅ |
| T73 — roadmap + CHANGELOG + version `0.1.0c0` | ✅ (tag left to operator) |

### Ad-hoc (2026-05-20+)

| Entrega | Status |
|---|---|
| `scripts/install.sh`, `render_from_url.py`, `render_beatgrid.py` | ✅ |
| README setup + quick-start | ✅ |
| Extra `[audio]` (beat/stems/whisper subset p/ consumidores tipo curta) | ✅ |

### Validação fim Phase C

| Gate | Status | Notas |
|---|---|---|
| WCSR-majmin ≥ 70% | ⚠️ not met | sample 3 songs (2026-08-04 post T70): mean **0.259** |
| Top-N ≤ 3 “Titan errado” | ⚠️ pending Henry GO | report `benchmarks/reports/2026-08-04/top-divergences.md` |
| Beat F ≥ 0.85 vs GT | ⏸ | corpus sem beat timestamps — diagnóstico cross-librosa only |
| Word offset &lt; 100ms | ⏸ | corpus sem word timestamps |
| Package `0.1.0c0` + CHANGELOG | ✅ | tag `v0.1.0-c0` operator |

### T70 quality backlog (carry-over / known issues)

| Item | Status |
|---|---|
| Chord stacking / wrong placement | ✅ destack + structural fixes; residual musical error remains |
| Orphans discarded by orchestrator | ✅ orphans → InstrumentalLine |
| Sectioner gaps dropping chords | ✅ midpoint coverage |
| `parent_word_idx` global vs local in placer | ✅ reindex |
| WCSR → 0.70 (Chordino ceiling + equal-interval GT) | ⚠️ open — needs stronger ACR (v0.2 BTC) and/or timed GT |
| Downbeat noise / fragmented lyric lines / off-by-1 syllable | ⏳ residual |

---

## Pós Phase C (shipped fora do plano C formal)

| Entrega | Status | Notas |
|---|---|---|
| **titan-core-decoupling F0** | ✅ | Lazy root exports; `core.hardware` public contract; version **`0.1.0b2`** / tag `v0.1.0b2` |
| Extra `[audio]` | ✅ | Subset ML sem Chordino/gruut — branch `feat/audio-extra` |

---

## v0.1.0 — Phase D: Pre-release | Semana 10 ⏳

**Blocked by:** Phase C tag `v0.1.0-c0`. Plano D ainda não escrito.

| Tarefa | Status |
|---|---|
| Docs: `method.md`, `profiles.md`, `troubleshooting.md` | ⏳ |
| Demo GIF/video | ⏳ |
| `LICENSE` MIT | ✅ (arquivo já no root) |
| `CHANGELOG.md` → `[0.1.0]` | ⏳ |
| Snapshot tests 5 profiles | ⏳ |
| `docs/known-issues.md` | ⏳ |
| `git tag v0.1.0` + GitHub release | ⏳ |
| (Opcional) PyPI publish | ⏳ |
| CI ubuntu matrix | ✅ (já em Phase B) |
| Tier 3 corpus / top-20 review | ⚠️ absorvido por T70 (corpus 151) — re-run se placement fix |

---

## Definition of Done — v0.1.0

### Funcionalidade
- [x] CLI `titan-chordpro song.mp3` produz `.chordpro` (mock e real path)
- [x] CLI: `--profile=`, `--language=`, `--output=`, `--keep-stems`, `--cache` (keep_stems wiring still imperfect)
- [x] Library API: `transcribe()` + `doc.write()` / `doc.to_string()`
- [x] Pipeline em Apple Silicon
- [x] `inline_slash` default

### Qualidade
- [x] Tier 1 CI macOS-14 + ubuntu-latest (workflow present)
- [x] Coverage ≥ 80% (met in A/B; maintain)
- [ ] Tier 2: WCSR-majmin ≥ 70% (Phase C sample ~0.26 — carry to v0.2 ACR)
- [ ] Top divergências revisadas (Henry GO)
- [ ] Snapshot tests 5 profiles
- [ ] `chordpro` CLI parseia `chordpro_ref`

### Documentação / Distribuição
- [x] README install + quick-start + Validation harness
- [x] Badges (CI / Nightly / License / version)
- [ ] method/profiles/troubleshooting (Phase D / F3)
- [x] CHANGELOG.md (`[0.1.0c0]`)
- [x] `pyproject.toml` extras `[mac]`, `[cuda]`, `[audio]`, `[validation]`
- [x] LICENSE MIT
- [x] nightly workflow

---

## v0.2 — Roadmap (preview, ~3 meses pós-v0.1)

**Tema:** "CUDA + Apple Silicon dual-platform completo"

| Tarefa | Status |
|---|---|
| Fork BTC-ISMIR19 → port PyTorch 2.x + MPS | ⏸ |
| `engines/transcription/mlx_whisper.py` | ⏸ |
| `engines/transcription/faster_whisper.py` | ⏸ |
| `engines/separation/demucs_mlx.py` | ⏸ |
| Pipeline em RTX 5070Ti + `cuda-mps-validation` initiative | ⚠️ hardware |
| Multi-evidence onset fusion (`fuse_onsets_v02`) | ⏸ |
| Acoustic prosody fallback no stress | ⏸ |
| All-In-One sectioning model | ⏸ |
| Vocab `extended_170` | ⏸ |
| Variable BPM handling | ⏸ |

---

## v0.3 — Roadmap (preview, ~6 meses pós-v0.1)

**Tema:** "Solo / tab (approximate) + extensões harmônicas"

| Tarefa | Status |
|---|---|
| Solo → ASCII tab watermarked | ⏸ |
| Vocab sus/add9/dim/aug | ⏸ |
| Meter / key change detection | ⏸ |
| ChordFormer / BACHI (se público) | ⏸ |
| Pre-chorus detection | ⏸ |

---

## Phase 2 — Sibling projects (vision)

| Projeto | Status |
|---|---|
| `titan-chordpro-render` | ⏸ |
| Theme CSS + editor drag-to-correct | ⏸ |
| `LearnableChordEngine` | ⏸ (`CorrectionLog` schema reserved) |

---

## Updates log

> Mais recente em cima.

### 2026-08-04 (Phase C — v0.1.0c0 ready for tag)

**Status:** ✅ Phase C closed at package **`0.1.0c0`**. Tag `v0.1.0-c0` is **operator-owned**
(`git tag -a v0.1.0-c0 -m "Phase C closeout"` after final review — do not auto-tag from automate).

Phase C delivers:

1. **Validation harness** — `benchmarks/` (corpus, yt-dlp, mir_eval runner, divergence ranker), nightly cron, `docs/setup-validation.md`.
2. **F-004 Chordino bass inversions** — `bass_chroma.py` + chordino wiring (T63/T64).
3. **Cache JSON** — `transcribe(cache=True)` 8-stage dump/load (T65/T66).
4. **T70 quality loop** — structural placement + harmonic mix + chord postprocess + destack; sample mean WCSR **0.259** (gate 0.70 **not met** — known issue / v0.2 ACR).
5. **T71 CLI** — `--validate` + rich Progress.
6. **T72 README** — badges + Validation harness section.
7. **T73** — CHANGELOG `[0.1.0c0]`, version bump, this roadmap entry.

**Operator tag command (after Henry GO):**

```bash
git tag -a v0.1.0-c0 -m "Phase C: validation harness + F-004 + cache + CLI polish (0.1.0c0)"
```

Carry-overs: WCSR ≥ 0.70 (BTC-ISMIR19 / timed GT), Henry top-N GO, Phase D docs (method/profiles/troubleshooting).

### 2026-08-04 earlier (roadmap sync + T70 structural fix campaign + sample re-run)
- ✅ Roadmap sync: Phase C T60–T69 done; T70 structural placement campaign.
- ✅ Documentado `0.1.0b2` / core-decoupling + extra `[audio]` (fora do plano C formal).
- ✅ **Structural placement fixes (T70-iter5):** reindex, orphans, sectioner coverage, beat_snap, stress.
- ✅ Sample re-run mean WCSR-majmin **0.211** pre quality-loop postprocess.

### 2026-06-24/25 (titan-core-decoupling F0)
- ✅ Lazy package-root exports; `titan_chordpro.core.hardware` isolated public contract for **curta**.
- ✅ Version **`0.1.0b2`** / tag `v0.1.0b2`. Import-isolation tests green.

### 2026-05-20 (T70 sample + ad-hoc tooling)
- 🚧 Sample 3 songs: mean WCSR-majmin ~0.21; lyrics ~95%; chords placement still bad.
- ✅ `install.sh`, `render_from_url.py`, `render_beatgrid.py`, README quick-start.
- 📌 Handoff: `docs/superpowers/handoff-phase-c-iter4-placement.md`.

### 2026-05-19 (Phase C plan + Week 8 harness + Codex b1)
- ✅ Phase C plan written + Codex plan review (6 findings applied).
- ✅ Hot-fix `v0.1.0-b1` (8/9 A+B findings); F-004 deferred then **implemented in Phase C**.
- ✅ Week 8 tasks T60–T69 landed (harness, F-004, cache, nightly).

### 2026-05-18 (Phase B complete)
- ✅ 7 ML engines; tag `v0.1.0-b0`.

### 2026-05-17 (Phase A complete)
- ✅ 259 tests, ~93% coverage; tag `v0.1.0-a0`.

### 2026-05-09 / 05-12
- ✅ Spec consolidado + Phase A plan (34 tasks).

### 2026-05-08
- 📝 Roadmap criado.

<!-- Adicione novas entradas acima desta linha -->

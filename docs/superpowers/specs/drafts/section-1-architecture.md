# Design — Seção 1: Architecture overview + Module structure

> Parte do design do Titan ChordPro Lib v0.1. Esta é a primeira de 6 seções, apresentada para review antes de consolidar no spec final.
> Decisões já tomadas que esta seção reflete: Mac-first, Chordino-now/BTC-later, dual-emit output profiles, abstração via Engine Protocols desde dia 1.
> Data: 2026-05-08

---

## Visão geral conceitual

A lib é uma **pipeline determinística** que recebe um arquivo de áudio e produz um documento ChordPro. Cinco estágios + um orquestrador + um writer:

```
                    ┌─────────────────────────────────────────────────┐
                    │           titan_chordpro.transcribe()            │
                    │              (orchestrator)                      │
                    └────────────────────┬────────────────────────────┘
                                         │
              ┌──────────┬──────────┬────┴─────┬──────────┐
              ▼          ▼          ▼          ▼          ▼
        ┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
        │  Sep    │ │ Trans  │ │ Beat   │ │ Chord  │ │ Lang     │
        │ (stems) │ │ (words)│ │ (grid) │ │ (chords)│ │(syllab.)│
        └─────────┘ └────────┘ └────────┘ └────────┘ └──────────┘
              │          │          │          │          │
              └──────────┴──────────┴──────────┴──────────┘
                                         │
                                         ▼
                                ┌──────────────────┐
                                │  Fusion Engine   │  ← IP central da lib
                                │ (place chord on  │
                                │   syllable)      │
                                └────────┬─────────┘
                                         │
                                         ▼
                              ┌────────────────────┐
                              │ ChordPro Writer    │
                              │ (output profiles)  │
                              └────────────────────┘
                                         │
                                         ▼
                                  song.chordpro
```

## Princípios arquiteturais

1. **Engines são plugáveis via Protocol** — orquestrador depende só de interfaces, nunca de implementações concretas. (Decisão Mac-first com abstração desde dia 1.)
2. **Pure-Python core** — Fusion Engine, Writer, Schemas, CLI rodam sem qualquer ML. Testáveis com mocks.
3. **ML é encapsulado nos Engines** — modelos rodam dentro de implementações concretas (`whisper_cpp`, `chordino`, etc.); fusion/writer/schemas não importam torch/whisper diretamente. **Isso não restringe o uso de ML — pelo contrário, habilita evolução**: trocar modelos por melhores sem refactor, plugar Engines "learnable" (que aplicam correções salvas) na phase 2, fine-tuning futuro de modelos próprios da lib.
4. **Provenance everywhere** — cada output do pipeline carrega confidence + version + engine name. Auditável end-to-end.
5. **Fail-fast com exception específica** — `TranscriptionError`, `ChordRecognitionError`, `BeatTrackingError`, `FusionError`. Cada erro carrega contexto debugável.
6. **Idempotência e cacheability** — separation/transcription/etc são caros; cada engine pode opcionalmente cachear outputs em `.titan-cache/<sha256-do-audio>/<stage>.json`.
7. **Outputs editáveis + audit trail para aprendizado** — `ChordProDocument` é Pydantic mutable; cada chord/word/syllable event carrega `confidence` + `source_engine`. Apps downstream (ex: editor visual de phase 2) podem aplicar correções do usuário e re-emitir ChordPro. Schema `CorrectionLog` (definido em v0.1 mas não consumido) reserva o ponto de extensão para Engines `Learnable*` na phase 2 — fundação para "drag-to-correct → save → improve next time".

## Estrutura de pacotes

```
titan_chordpro/
├── __init__.py                   # API pública: transcribe(), ChordProDocument
├── core/
│   ├── __init__.py
│   ├── schemas.py                # Pydantic: TimeStamp, WordEvent, ChordEvent,
│   │                             #   PhonemeEvent, BeatGrid, StemSet,
│   │                             #   SyllableEvent, FusedEvent, ChordProDocument,
│   │                             #   Correction, CorrectionLog (phase-2 extension)
│   ├── protocols.py              # Engine Protocols (interfaces)
│   ├── exceptions.py             # Hierarchy: TitanError → {Transcription,
│   │                             #   Separation, ChordRecognition, BeatTracking,
│   │                             #   Fusion, Writer}Error
│   └── confidence.py             # Confidence aggregation utilities
├── engines/                      # Concrete engine implementations
│   ├── __init__.py
│   ├── separation/
│   │   ├── __init__.py
│   │   ├── htdemucs.py           # via python-audio-separator (default)
│   │   └── demucs_mlx.py         # Apple Silicon fast-path (v0.2)
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── whisper_cpp.py        # universal default
│   │   ├── mlx_whisper.py        # Apple fast-path (v0.2)
│   │   └── faster_whisper.py     # CUDA fast-path (v0.2)
│   ├── alignment/
│   │   ├── __init__.py
│   │   └── torchaudio_align.py   # forced alignment (CUDA + MPS)
│   ├── chord/
│   │   ├── __init__.py
│   │   ├── chordino.py           # v0.1 default (chord-extractor wrapper)
│   │   ├── btc_ismir19.py        # v0.2 (ported to PyTorch 2.x + MPS)
│   │   └── learnable.py          # phase-2 pattern: wraps base engine +
│   │                             #   applies CorrectionLog (NOT in v0.1)
│   ├── beat/
│   │   ├── __init__.py
│   │   └── beatthis.py           # CPJKU 2024
│   └── lang/                     # Language-specific syllabification
│       ├── __init__.py
│       ├── base.py               # SyllabificationEngine Protocol
│       ├── english.py            # g2p_en + CMU dict
│       └── portuguese.py         # gruut + pyphen + orthographic stress
├── fusion/                       # IP CENTRAL — pure Python
│   ├── __init__.py
│   ├── syllabifier.py            # Maximum Onset Principle
│   ├── stress.py                 # Stress detection (per language)
│   ├── beat_snap.py              # Quantization to beat grid (mir_eval tolerances)
│   ├── onset_fusion.py           # Multi-evidence chord onset (v0.1: chord+beat;
│   │                             #   v0.2: +bass+vocal)
│   ├── melisma.py                # Detection + handling
│   └── placer.py                 # place_chord_in_lyrics() — main algorithm
├── writer/
│   ├── __init__.py
│   ├── document.py               # ChordProDocument structure
│   ├── profiles/
│   │   ├── __init__.py
│   │   ├── base.py               # OutputProfile Protocol
│   │   ├── chordpro_ref.py       # default — uses {sog}/{eog}
│   │   ├── onsong.py             # inline-only, no grids
│   │   ├── propresenter.py
│   │   └── songbookpro.py
│   └── serializer.py             # ChordProDocument → str
├── orchestrator.py               # transcribe() — wires everything via Protocols
├── cli.py                        # argparse wrapper
├── factory.py                    # Engine selection: hardware detection +
│                                 #   user preference + extras availability
└── version.py
```

Companion paths (não dentro do pacote):

```
docs/research/         # Já existe — pesquisa
docs/superpowers/      # Specs de design
tests/
├── unit/              # Testes de cada módulo isolado (mocks)
├── integration/       # Pipeline end-to-end com fixtures
└── corpus/            # Test corpus (5-10 músicas) com ground-truth JSON
benchmarks/            # Validation harness (Isophonics WCSR)
```

## Mapeamento das decisões já tomadas

| Decisão | Reflexão na arquitetura |
|---|---|
| Mac-first | `engines/separation/demucs_mlx.py`, `engines/transcription/mlx_whisper.py` ficam para v0.2; v0.1 usa htdemucs cross-platform e whisper.cpp |
| Chordino-now, BTC-later | `engines/chord/chordino.py` é o default v0.1; `engines/chord/btc_ismir19.py` chega em v0.2 |
| Output profiles dual-emit | `writer/profiles/` modular, `chordpro_ref` como default |
| Engine abstraction day 1 | `core/protocols.py` é foundational; `factory.py` faz a escolha |
| Pure-Python fusion | `fusion/` zero-deps de ML, totalmente testável |
| PT-BR + EN syllabification | `engines/lang/portuguese.py` (gruut+pyphen) e `engines/lang/english.py` (g2p_en) |
| Phase-2 learning (drag-to-correct → save → improve) | Schemas `Correction` + `CorrectionLog` em `core/schemas.py`; pattern `engines/chord/learnable.py` documentado mas não implementado em v0.1 |

## Distribuição via pip extras

```toml
[project]
name = "titan-chordpro-lib"
version = "0.1.0"
dependencies = [
    "pydantic>=2.0",
    "librosa>=0.10",
    "soundfile",
    "numpy",
    "pyyaml",
    "rich",  # CLI progress
    # Engines that work cross-platform without extras:
    "python-audio-separator>=0.17",  # htdemucs_ft
    "pywhispercpp",                  # whisper.cpp Python binding
    "torchaudio",                    # forced alignment
    "torch",                         # backbone
    "beat-this",                     # beat tracking
    "chord-extractor",               # Chordino wrapper
    "g2p-en",                        # English syllabification
    "gruut",                         # Portuguese syllabification
    "pyphen",                        # PT-BR boundaries
]

[project.optional-dependencies]
mac = [
    "mlx",
    "mlx-whisper",
    # demucs-mlx pinned when available
]
cuda = [
    "faster-whisper",  # CUDA fast-path for transcription
    # Note: CTranslate2 is bundled with faster-whisper
]
dev = [
    "pytest",
    "pytest-cov",
    "ruff",
    "mypy",
    "mir_eval",  # for validation harness
]
```

## API pública (top-level)

```python
from titan_chordpro import transcribe, ChordProDocument

# Simplest usage
doc = transcribe("song.mp3")
doc.write("song.chordpro")

# With overrides
doc = transcribe(
    "song.mp3",
    language="pt-BR",
    output_profile="onsong",
    transcription_engine="mlx-whisper",  # explicit override
    keep_stems=True,
)

# Inspect intermediate results
print(doc.metadata)          # title, key, tempo, time_sig
print(doc.confidence)        # aggregated confidence per stage
print(doc.sections)          # verses, choruses, instrumentals
```

## Ecossistema futuro (informational)

Esta lib é o **núcleo Python** do ecossistema Titan ChordPro. Sibling projects planejados (NOT em v0.1 desta lib) usarão a saída JSON do `ChordProDocument.model_dump_json()` como API de integração:

```
titan-chordpro-lib (este repo, Python)
    │
    │ ChordProDocument JSON (Pydantic serialization)
    ▼
titan-chordpro-render (futuro repo, TypeScript/JS)
    │
    │ Semantic HTML com data-attrs (data-confidence, data-stressed,
    │ data-placement-strategy, data-bass, data-melisma, etc.)
    ▼
titan-chordpro-theme-default (futuro repo, CSS)
    │
    └─→ Apps consumidores (phase-2 editor, worship live apps, etc.)
```

**Por que TypeScript/JS para o renderer:** HTML/DOM/CSS é domínio JS — frameworks (React/Vue), accessibility libs, animation, web fundamentals. Forçar Python a emitir HTML semântico viola o fit-de-linguagem e cria manutenção dupla.

**Bridge é grátis:** Pydantic `model_dump_json()` já serializa toda a estrutura (incluindo confidence, stressed flags, placement_strategy, melisma data). Renderer consome JSON; não precisa parsear texto `.chordpro`.

**Implicação para esta lib:** ZERO mudança de escopo em v0.1. O JSON serialization já vem grátis com Pydantic. Apenas mantemos consciência de que essa API existe e protegemos sua estabilidade (schema versioning eventual).

## Pontos de atenção arquitetural

1. **`pyphen` é GPL** — uso via subprocess ou substituir por hand-rolled algorithm. **Decisão pendente:** hand-roll ou aceitar GPL? `gruut` (MIT) cobre maior parte de PT-BR sozinho — talvez `pyphen` seja desnecessário. Validar.
2. **`chord-extractor` requer Chordino instalado externamente** — isso implica setup script no README ou Docker. Não pip-install puro. Documentar friction.
3. **`pywhispercpp` maturity** — flagged como `[UNCERTAIN]` na pesquisa. Spec deve incluir teste de smoke contra `pywhispercpp` antes de wiring no orchestrator.
4. **Cache strategy** — opt-in via `transcribe(..., cache=True)`. Default off (avoid surprise disk writes). Documentar diretório.

---

## Pontos para review

Áreas onde feedback seu é especialmente útil:

- **Estrutura de pacotes** — granularidade dos módulos, nomes, hierarquia
- **`engines/lang/`** — separar syllabification em `engines/` ou em `fusion/`? (atualmente em `engines/`)
- **`pyphen` GPL** — aceitar via subprocess, hand-roll, ou descartar e usar só `gruut`?
- **Pip extras** — nome `[mac]` vs `[apple]` vs `[apple-silicon]`?
- **API pública** — `transcribe()` retorna `ChordProDocument` ou `(ChordProDocument, Provenance)` (tupla com metadata explícita)?
- **Cache strategy** — opt-in (default off) ou opt-out (default on com flag de override)?
- **`factory.py`** — separar do orchestrator ou fundir?

Quando terminar, me avise no chat.

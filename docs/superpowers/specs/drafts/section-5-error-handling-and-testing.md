# Design — Seção 5: Error handling + Testing strategy

> Parte 5 de 6 do design do Titan ChordPro Lib v0.1.
> Esta seção define COMO falhas são propagadas e tratadas, E como a lib é testada/validada — incluindo o **harness de validação 147 songs** decidido nas seções anteriores (export do banco do owner, audio download, divergence ranker, 3 tiers de validação).
> Data: 2026-05-08

---

# Parte A — Error handling

## Filosofia: fail-fast com contexto rico

Princípios:

1. **Fail-fast**: se um stage do pipeline falha, a pipeline inteira para. Não há "best effort com partial output" em v0.1. Razão: outputs parciais silenciosamente errados são piores que nenhum output.
2. **Exceções específicas por stage**: usuário deve saber QUAL stage falhou e POR QUÊ.
3. **Contexto debugável**: cada exception carrega audio_id, engine info, stage, e raw error from underlying lib.
4. **Sem retry automático**: ML inference determinística não se beneficia de retry. Bugs de download de modelo, etc., são raised e o usuário decide.
5. **Validação Pydantic = exception precoce**: schemas inválidos lançam ANTES de processamento caro.

---

## Exception hierarchy

Em `core/exceptions.py`:

```python
class TitanError(Exception):
    """Base class for all Titan ChordPro errors."""
    
    def __init__(
        self,
        message: str,
        *,
        audio_id: str | None = None,
        stage: str | None = None,
        engine: str | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.audio_id = audio_id
        self.stage = stage
        self.engine = engine
        self.cause = cause
    
    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.stage:
            parts.append(f"stage={self.stage}")
        if self.engine:
            parts.append(f"engine={self.engine}")
        if self.audio_id:
            parts.append(f"audio_id={self.audio_id[:12]}")
        if self.cause:
            parts.append(f"caused_by={type(self.cause).__name__}: {self.cause}")
        return " | ".join(parts)


# Stage-specific subclasses

class SeparationError(TitanError):
    """Source separation failed."""

class TranscriptionError(TitanError):
    """Transcription of vocals failed (or produced unparseable output)."""

class AlignmentError(TitanError):
    """Forced alignment of words failed."""

class ChordRecognitionError(TitanError):
    """Chord recognition failed."""

class BeatTrackingError(TitanError):
    """Beat tracking failed."""

class SyllabificationError(TitanError):
    """Syllabification failed (rare — usually OOV words)."""

class FusionError(TitanError):
    """Fusion engine failed (placement, sectioning, etc.)."""

class WriterError(TitanError):
    """Output writer failed (profile rendering, file IO)."""


# Configuration / environment errors

class TitanConfigError(TitanError):
    """User-supplied configuration is invalid."""

class EngineUnavailableError(TitanConfigError):
    """Requested engine is not installed or hardware not supported."""
    # e.g., user passes transcription_engine='mlx-whisper' on Linux
```

---

## Error context — exemplo concreto

Quando faster-whisper falha por OOM:

```python
try:
    words, phonemes = engine.transcribe(stems.vocals, language=lang)
except RuntimeError as e:
    raise TranscriptionError(
        f"Transcription failed for {stems.vocals.name}: {e}",
        audio_id=audio_id,
        stage='transcription',
        engine=engine.info.name,
        cause=e,
    ) from e
```

CLI output para usuário:

```
$ titan-chordpro song.mp3
ERROR: Transcription failed for song-vocals.wav: CUDA out of memory.
       stage=transcription | engine=faster_whisper | audio_id=a1b2c3d4
       caused_by=RuntimeError: CUDA out of memory. Tried to allocate 2.50 GiB.
       
       Suggestions:
       - Try a smaller model: --transcription-engine=whisper_cpp
       - Or run on CPU: --device=cpu
       - See docs/troubleshooting.md
```

---

## Failure modes por stage — comportamento esperado

**Regra de partial output (consistente):**

> Se um stage produz output **válido vazio** (ex: instrumental sem letras → `words=[]`, percussivo sem harmonia → `chord_events=[]`): pipeline **continua**. Stages downstream lidam com listas vazias graciosamente.
>
> Se um stage **lança exception** OU **retorna output corrompido** (ex: timestamps negativos, schema-inválido): pipeline **fail-fast**. Validação Pydantic pega corrupção precoce.

| Stage | Falha | Comportamento v0.1 |
|---|---|---|
| Separation | Audio file corrupted/unsupported | `SeparationError` raised antes de qualquer ML inference (fail-fast) |
| Separation | Out-of-memory | `SeparationError` com sugestão de modelo menor (fail-fast) |
| Transcription | OOM | `TranscriptionError` com sugestão de engine menor (fail-fast) |
| Transcription | Audio puramente instrumental (Whisper retorna `words=[]`) | Pipeline continua — output será só `InstrumentalLine`s (vazio válido) |
| Transcription | Whisper hallucina (silêncio retorna texto falso) | Detectado por VAD pre-pass; se VAD falhar, output gerado mas com `confidence` baixa flagada |
| Alignment | Modelo wav2vec2 falta para o language | `AlignmentError` com sugestão "use --language=auto ou install wav2vec2-{lang}" (fail-fast) |
| Chord | Áudio puramente percussivo / silencioso (`chord_events=[]`) | Pipeline continua — todas LyricLines sem chord markers (vazio válido) |
| Chord | Engine retorna ChordEvents com timestamps negativos | `ChordRecognitionError` (output corrompido — fail-fast) |
| Beat | Audio menor que 5s (BeatThis precisa janela mínima) | `BeatTrackingError` com sugestão "audio too short for beat tracking" (fail-fast) |
| Beat | BeatThis retorna `beats=[]` | `BeatTrackingError` — fusion engine precisa de beats para snap (fail-fast) |
| Syllabification | OOV word (não está em dict, não tem phonemes) | Fallback heurístico CV-split; warning logado mas pipeline continua (vazio válido com warning) |
| Fusion | Não consegue fundir nada (ex: chord events totalmente fora do span dos words) | `FusionError` raised — caso patológico, não deveria acontecer com inputs válidos (fail-fast) |
| Writer | Profile não existe | `WriterError` ("Unknown output profile: 'foo'") (fail-fast) |

**Princípio:** cada falha tem mensagem que sugere ação. Usuário não recebe stacktrace cru sem orientação.

---

## Logging strategy

Em `core/logging.py`:

```python
import logging

# Library logger root: 'titan_chordpro'
# Engine sublogers: 'titan_chordpro.engines.transcription', etc.
# Fusion subloger: 'titan_chordpro.fusion'

# Default level: WARNING (silencioso para usuário lib)
# CLI passes --verbose to bump down to INFO
# --debug to bump down to DEBUG

# All log records include:
# - audio_id (when in pipeline context)
# - stage
# - engine (when applicable)
# - elapsed_ms (timing)

class ContextFilter(logging.Filter):
    """Adds audio_id/stage/engine to log record from contextvars."""
    ...
```

CLI `--verbose` mostra:

```
[2026-05-08 11:23:45] INFO  titan_chordpro.orchestrator    [a1b2c3d4] starting pipeline
[2026-05-08 11:23:45] INFO  titan_chordpro.engines.separation [a1b2c3d4] separating with htdemucs_ft (mps)
[2026-05-08 11:23:50] INFO  titan_chordpro.engines.separation [a1b2c3d4] done in 4823ms
[2026-05-08 11:23:50] INFO  titan_chordpro.engines.transcription [a1b2c3d4] transcribing with whisper_cpp
[2026-05-08 11:24:02] INFO  titan_chordpro.engines.transcription [a1b2c3d4] 142 words, language=pt, confidence=0.89
[2026-05-08 11:24:02] INFO  titan_chordpro.fusion           [a1b2c3d4] placing 38 chords across 14 lines
[2026-05-08 11:24:03] INFO  titan_chordpro.orchestrator    [a1b2c3d4] complete in 18.2s
```

---

# Parte B — Testing strategy

## Filosofia

1. **Pure-Python core é trivialmente testável** — fusion, writer, schemas, orchestrator (com mocks) não precisam GPU. Tests rodam em CI commodity hardware.
2. **ML engines são testados via integration** — usar engines reais é caro; testes de unidade usam mocks.
3. **Validation harness ≠ tests** — corpus 147 songs valida QUALIDADE algoritmica; tests verificam CORRETUDE de código.
4. **Golden fixtures deterministas** — outputs do fusion engine são diffable; mudanças no algoritmo aparecem como diffs em CI.
5. **Snapshot tests para writer** — cada profile tem `expected.<profile>.chordpro` no corpus.

---

## Test layers

```
tests/
├── unit/                         # Per-module, fast, no I/O
│   ├── core/
│   │   ├── test_schemas.py       # Pydantic validation rules
│   │   ├── test_exceptions.py
│   │   └── test_protocols.py     # Mock impls satisfy Protocols
│   ├── fusion/
│   │   ├── test_syllabifier.py   # MOP, language-specific rules
│   │   ├── test_stress.py        # PT orthographic + EN CMU
│   │   ├── test_beat_snap.py     # ±70ms / ±150ms tolerances
│   │   ├── test_onset_fusion.py
│   │   ├── test_melisma.py
│   │   ├── test_sectioner.py
│   │   └── test_placer.py        # The hierarchical placement algorithm
│   ├── writer/
│   │   ├── test_profiles.py
│   │   └── test_serializer.py
│   └── engines/
│       └── lang/
│           ├── test_english.py   # g2p_en wrapping
│           └── test_portuguese.py # gruut wrapping
├── integration/                  # Real-ish pipeline, mock engines
│   ├── test_orchestrator.py      # Full pipeline with mocks
│   ├── test_factory.py           # Engine selection logic
│   └── test_cli.py               # CLI invocation
├── corpus/                       # Real ML, real audio (slow tier)
│   ├── README.md                 # How to populate, what's expected
│   ├── songs/
│   │   ├── deus_e_refugio/
│   │   │   ├── audio.mp3         # 30s snippet (CI) or full song (local)
│   │   │   ├── ground_truth.chordpro  # baixado do site
│   │   │   ├── expected.inline_slash.chordpro  # snapshot do que Titan emite
│   │   │   └── notes.md
│   │   └── ... (5 outras)
│   └── fixtures/
│       └── ground_truth_schema.json  # JSON schema do ground truth
├── benchmarks/                   # Validation harness (Tiers 2+3)
│   ├── export_corpus.py          # SQL → JSON do banco do owner
│   ├── audio_downloader.py       # yt-dlp wrapper
│   ├── validation_runner.py      # Run Titan against corpus, collect metrics
│   ├── divergence_ranker.py      # Rank diffs by severity
│   └── reports/                  # Output dir (gitignored)
└── conftest.py                   # pytest fixtures + mocks
```

---

## Mock engines (cross-reference Seção 2)

`tests/conftest.py` provê fixtures pytest que retornam mock engines:

```python
@pytest.fixture
def mock_separation_engine(tmp_path):
    """Returns a SourceSeparationEngine that produces silent stem files."""
    class _Mock:
        def separate(self, audio):
            stems_dir = tmp_path / "stems"
            stems_dir.mkdir()
            for stem in ['vocals', 'bass', 'drums', 'other']:
                (stems_dir / f"{stem}.wav").write_bytes(_silent_wav())
            return StemSet(
                audio_id=sha256(audio.read_bytes()),
                vocals=stems_dir / "vocals.wav",
                bass=stems_dir / "bass.wav",
                drums=stems_dir / "drums.wav",
                other=stems_dir / "other.wav",
                duration=30.0,
                source_engine='mock_separation',
            )
        @property
        def info(self):
            return EngineInfo(name='mock', version='0', backend='cpu')
    return _Mock()
```

Mocks aderem aos Protocols (Seção 2) — typecheck via `runtime_checkable` em testes.

---

## Tier 1 — CI tests (per-commit)

**Roda em:** GitHub Actions, macOS-14 (Apple Silicon) + ubuntu-latest, no fork do PR.
**Tempo alvo:** < 5 min total
**Cobertura:**

- All unit tests (~600 expected, mocked)
- Integration tests com mock engines
- Snapshot tests dos 5 profiles
- 6 corpus songs: 30s snippets, fast pipeline run with REAL engines (sanity check)

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: unit tests (fast, no I/O)",
    "integration: pipeline tests with mocks",
    "corpus_quick: corpus tests on 30s snippets (CI)",
    "corpus_full: full-song corpus tests (nightly only)",
    "benchmark: validation harness against 147 songs (manual)",
]
```

CI command: `pytest -m "unit or integration or corpus_quick"`

---

## Tier 2 — Nightly tests (1×/day cron)

**Roda em:** GitHub Actions com self-hosted runner que tem audio + GPU disponível.
**Tempo alvo:** ~30-60 min
**Cobertura:**

- Tudo do Tier 1
- 30 corpus songs **estratificadas por edge case** (não amostragem aleatória):
  - 5+ com slash chords (testar bass-stem post-correction)
  - 3+ com time signature ambíguo / 6/8 (testar BeatThis)
  - 3+ com melisma sustentado (testar fusion engine melisma path)
  - 3+ com modulação / mudança de tom (testar key change handling)
  - 3+ com vocais difíceis (testar Whisper degradação)
  - Restante: amostra aleatória do catálogo para coverage de gêneros gerais
  - Sample size override via env: `BENCHMARKS_SAMPLE_SIZE=50 pytest -m corpus_full`
- Métricas computadas:
  - **Chord WCSR-majmin** (Weighted Chord Symbol Recall, vocab majmin) — via `mir_eval.chord`
  - **Chord WCSR-sevenths** (extended vocab)
  - **Beat F-measure** — via `mir_eval.beat`
  - **Word alignment median offset** (ms)
  - **Placement strategy distribution** (% stressed_syllable / any_syllable / before_word / orphan)
  - **Confidence aggregates** por stage

Output: `benchmarks/reports/<date>/metrics.json` + markdown report no PR description.

Trigger: cron job + manual via GitHub UI.

CI command: `pytest -m "corpus_full" --benchmarks-corpus=tests/corpus-export.json --report-dir=benchmarks/reports/$(date +%Y%m%d)`

---

## Tier 3 — Pre-release validation (manual)

**Roda em:** Local machine do owner ou self-hosted runner (M4).
**Tempo alvo:** ~5-7h, single run
**Cobertura:**

- 147 songs (full catálogo)
- Métricas idênticas a Tier 2 mas em escala
- **Divergence ranker** ranqueia top N diffs por severidade
- Owner revisa top 20 manualmente; corrige Titan OU corrige chord chart no site
- Report final é parte do release notes

Trigger: manual antes de cada `git tag v0.X.0`.

---

## Validation harness — componentes

### Componente 1 — `benchmarks/export_corpus.py`

Roda no servidor do owner (acesso SQL). Exporta JSON com todas as músicas que têm `is_canonical=True` no chordpro.

```python
# Pseudocode (real impl uses ORM or direct SQL)
import json
from pathlib import Path

def export_corpus(db_conn, output: Path):
    query = """
    SELECT 
        s.id, s.title, s.artist, s.key, s.tempo, s.time_signature,
        s.youtube_id, s.duration_seconds,
        cp.content as chordpro_canonical
    FROM songs s
    INNER JOIN chordpros cp 
        ON cp.song_id = s.id 
        AND cp.is_canonical = true
    WHERE s.status = 'in_use'
    ORDER BY s.id;
    """
    rows = db_conn.execute(query).fetchall()
    output.write_text(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
    print(f"Exported {len(rows)} songs to {output}")
```

Run uma vez antes de Tier 2/3. Output é **commitado no repo**: `tests/corpus-export.json` (~1MB, ChordPro+metadata em JSON).

**Decisão fixada (commit do JSON):**
- CI fica self-contained — sem GitHub Secrets, sem rede, sem dependência de banco rodando
- License é zero issue (owner é dono do site e do repo)
- Re-export é manual quando catálogo expande significativamente (raro)
- Reproducibilidade total: qualquer dev clona o repo e roda Tier 2 sem credenciais

`tests/corpus-export.json` schema:

```json
[
  {
    "id": 58,
    "title": "Grande Deus",
    "artist": "Adoradores 2",
    "key": "E",
    "tempo": 85,
    "time_signature": "4/4",
    "youtube_id": "nS80ThKhfZQ",
    "duration_seconds": 296,
    "chordpro_canonical": "{title:059 - Grande Deus}\n..."
  },
  ...
]
```

### Componente 2 — `benchmarks/audio_downloader.py`

Baixa audio via yt-dlp usando `youtube_id` do JSON exportado.

```python
import subprocess
from pathlib import Path

def download_audio(youtube_id: str, output_dir: Path) -> Path:
    """Downloads audio as best-quality MP3 using yt-dlp."""
    output = output_dir / f"{youtube_id}.mp3"
    if output.exists():
        return output  # cached
    
    subprocess.run([
        'yt-dlp',
        '-x', '--audio-format', 'mp3',
        '--audio-quality', '0',
        '-o', str(output_dir / '%(id)s.%(ext)s'),
        f'https://youtu.be/{youtube_id}',
    ], check=True)
    return output
```

**Cache strategy:**

- Local apenas em v0.1: `~/.cache/titan-chordpro/audio/<youtube_id>.mp3`
- **Cache key documentada e estável** para evolução futura: `<youtube_id>.<format>.<quality>` (ex: `nS80ThKhfZQ.mp3.0`)
- Gitignored — depende do user baixar; CI nightly baixa on-demand; cache persiste entre runs
- Migração futura para S3/R2 (quando virou time distribuído): mesma cache key, só backend muda — refactor mínimo

### Componente 3 — `benchmarks/validation_runner.py`

Itera o JSON exportado, baixa audio, roda Titan, compara com chordpro_canonical.

```python
def run_validation(corpus: list[dict], audio_dir: Path) -> ValidationReport:
    results = []
    for song in tqdm(corpus, desc="Validating"):
        try:
            audio = download_audio(song['youtube_id'], audio_dir)
            doc = transcribe(audio, language='pt')
            actual = doc.to_string(profile='inline_slash')
            
            metrics = compute_metrics(
                actual=actual,
                expected=song['chordpro_canonical'],
                song_id=song['id'],
            )
            results.append(metrics)
        except Exception as e:
            results.append(FailedMetric(song_id=song['id'], error=str(e)))
    
    return ValidationReport(
        results=results,
        summary=summarize(results),
    )
```

`compute_metrics` usa `mir_eval` para WCSR e F-measure; também faz string-diff de chordpro normalizados.

### Componente 4 — `benchmarks/divergence_ranker.py`

Ranqueia divergências por severidade para review manual:

```python
class Severity(Enum):
    CRITICAL = 1   # WCSR < 50% — algoritmo claramente errou
    HIGH = 2       # WCSR 50-70% OR placement_strategy='orphan' > 30% chords
    MEDIUM = 3     # WCSR 70-85% — fixable
    LOW = 4        # WCSR 85-95% — likely chart errado, não Titan
    NEGLIGIBLE = 5 # WCSR > 95% — match basicamente

def rank_divergences(report: ValidationReport, top_n: int = 20) -> list[Divergence]:
    """Returns the top N divergences ranked by severity for manual review."""
    ...
```

Output: `benchmarks/reports/<date>/top-divergences.md` com:
- Song ID + title
- Severity score
- Side-by-side diff (Titan vs site)
- Suggested action (fix Titan / fix chart / verify ambiguous)

---

## Snapshot tests (output profiles)

```python
@pytest.mark.parametrize('profile_name', ['inline_slash', 'chordpro_ref', 'onsong'])
def test_profile_snapshot(song_id: str, profile_name: str):
    truth = load_ground_truth(song_id)
    doc = build_doc_from_truth(truth)
    profile = get_profile(profile_name)
    rendered = profile.render(doc)
    
    snapshot_path = f"tests/corpus/songs/{song_id}/expected.{profile_name}.chordpro"
    if os.environ.get('UPDATE_SNAPSHOTS'):
        Path(snapshot_path).write_text(rendered)
    else:
        expected = Path(snapshot_path).read_text()
        assert rendered == expected, f"Snapshot mismatch for {song_id}/{profile_name}"
```

`UPDATE_SNAPSHOTS=1 pytest` regenera; PR diff mostra changes claros.

**Validação extra do `chordpro_ref` profile via parser oficial:**

```python
def test_chordpro_ref_parseable_by_official_cli(song_id):
    """Validates that chordpro_ref output passes the canonical chordpro CLI parser."""
    snapshot = load_snapshot(song_id, 'chordpro_ref')
    result = subprocess.run(
        ['chordpro', '--output=/dev/null', '-'],
        input=snapshot,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"chordpro CLI failed to parse: {result.stderr}"
    )
```

Custo: `chordpro` CLI install via brew/apt em CI (~30s). Pega não-conformance que diff de string não pega.

**Outros profiles (`inline_slash`, `onsong`, etc.) não recebem essa validação** — não há parser oficial neutro para eles. São testados via snapshot match contra `expected.<profile>.chordpro` e (eventualmente) testes manuais nos apps reais.

---

## CI/CD configuration (high-level)

`.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check .
      - run: mypy src/
  
  unit-tests:
    strategy:
      matrix:
        os: [macos-14, ubuntu-latest]
        python: ['3.11', '3.12']
    runs-on: ${{ matrix.os }}
    steps:
      - run: pip install -e ".[dev]"
      - run: pytest -m "unit or integration"
  
  corpus-quick:
    runs-on: macos-14
    steps:
      - run: pip install -e ".[dev,mac]"
      - run: pytest -m "corpus_quick" --maxfail=1
```

`.github/workflows/nightly.yml`:

```yaml
name: Nightly
on:
  schedule:
    - cron: '0 6 * * *'  # 06:00 UTC daily
  workflow_dispatch:
jobs:
  full-corpus:
    runs-on: [self-hosted, gpu]
    steps:
      - run: pytest -m "corpus_full" --report-dir=benchmarks/reports/$(date +%Y%m%d)
      - uses: actions/upload-artifact@v4
        with: { name: benchmark-report, path: benchmarks/reports/ }
```

---

## Coverage targets

**Gate (PR não merge se < 80%):** `pytest --cov --cov-fail-under=80`

**Targets aspiracionais por módulo (medidos mas não bloqueiam):**

- **Core schemas + protocols:** 100% (trivial, deterministic)
- **Fusion engine:** ≥ 90% (heart of the lib)
- **Writer profiles:** 100% (deterministic functions)
- **Engines (mock-tested):** 80% (ML internals difícil de cobrir bem com mocks)
- **CLI:** 80%

Razão de 80% gate vs 90% aspiracional: 80% evita "test for coverage" anti-pattern (testes triviais para subir cobertura); aspiracionais por módulo são meta de saúde do código sem virar blocker.

---

## Pontos para review

Os 8 itens em aberto foram resolvidos via auto-review (sugestões aplicadas):

- ✅ **Corpus export:** commit do JSON em `tests/corpus-export.json` (CI self-contained, license OK)
- ✅ **Tier 2 sample size:** 30 estratificado por edge case + env var `BENCHMARKS_SAMPLE_SIZE` para override
- ✅ **Severity thresholds:** mantidos absolutos (50/70/85/95% WCSR) v0.1; baseline-relative em v0.2 se necessário
- ✅ **Partial output policy:** regra explícita "vazio válido continua / corrompido ou exception fail-fast" + tabela de failure modes ampliada
- ✅ **Logging library:** stdlib `logging` + `ContextFilter` custom (zero deps adicionais)
- ✅ **Coverage gate:** 80% gate (PR blocker) + targets aspiracionais por módulo (100% schemas, 90% fusion, 100% profiles)
- ✅ **Snapshot validation:** `chordpro_ref` validado via `chordpro` CLI parser oficial (~30s install em CI); outros profiles via snapshot match apenas
- ✅ **Audio cache:** local-only v0.1 em `~/.cache/titan-chordpro/audio/<youtube_id>.<format>.<quality>` com cache key estável para futura migração S3/R2

Sem itens abertos restantes nesta seção. Quando terminar o review, me avise no chat.

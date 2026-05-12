# Design — Seção 2: Engine Protocols + Schemas

> Parte 2 de 6 do design do Titan ChordPro Lib v0.1.
> Esta seção define a fronteira entre o orquestrador (pure-Python) e as implementações de ML (Engines): as **interfaces** que o orquestrador chama e os **dados** que circulam pela pipeline.
> Inclui os schemas `Correction` / `CorrectionLog` aprovados na revisão da Seção 1.
> Data: 2026-05-08

---

## Por que Pydantic v2

Toda comunicação inter-módulo passa por modelos Pydantic v2. Razões:

1. **Validação automática** — `timestamp.end > timestamp.start`, `confidence ∈ [0,1]`, etc., garantidos no momento de construção. Evita classe inteira de bugs.
2. **JSON nativo** — `.model_dump_json()` / `.model_validate_json()` sem boilerplate. Necessário para (a) cache opcional, (b) `CorrectionLog` para phase 2, (c) round-trip via API REST se phase 2 expor uma.
3. **FastAPI / web frontend ready** — phase 2 (editor) provavelmente terá uma camada web. Pydantic é a lingua franca.
4. **Imutabilidade opcional** — `model_config = ConfigDict(frozen=True)` para shapes que não devem mutar (ex: `Provenance`).
5. **Discriminated unions** — para `LyricLine | InstrumentalLine`, `Correction.field` etc.

---

## Engine Protocols

Seis Protocols definidos em `core/protocols.py`. O orquestrador depende EXCLUSIVAMENTE destas interfaces:

### 1. SourceSeparationEngine

```python
from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class SourceSeparationEngine(Protocol):
    """Separates a mixed audio file into 4 stems: vocals, bass, drums, other."""
    
    def separate(self, audio: Path) -> StemSet:
        """Args:
            audio: Path to source audio file (any format librosa accepts).
        
        Returns:
            StemSet with file paths to 4 separated stems.
        
        Raises:
            SeparationError: if separation fails for any reason.
        """
        ...
    
    @property
    def info(self) -> EngineInfo:
        """Engine identification for provenance tracking."""
        ...
```

**Implementações v0.1:** `engines/separation/htdemucs.py` (default cross-platform via `python-audio-separator`).
**Implementações v0.2:** `engines/separation/demucs_mlx.py` (Apple Silicon fast-path).

---

### 2. TranscriptionEngine

```python
@runtime_checkable
class TranscriptionEngine(Protocol):
    """Transcribes vocal stem to words. Optionally returns phonemes if the engine
    has phoneme-level alignment built-in (e.g. WhisperX wav2vec2 path)."""
    
    def transcribe(
        self,
        vocals: Path,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Args:
            vocals: Path to vocal stem (post-separation).
            language: ISO 639-1 code ('en', 'pt'). If None, engine auto-detects.
        
        Returns:
            TranscriptionResult containing words and (optionally) phonemes.
        
        Raises:
            TranscriptionError.
        """
        ...
    
    @property
    def info(self) -> EngineInfo: ...
```

> **Note:** to check if the engine produced phonemes, the orchestrator just checks `result.phonemes is not None`. No separate property needed.

**Implementações v0.1:** `engines/transcription/whisper_cpp.py` (universal default via `pywhispercpp`).
**Implementações v0.2:** `engines/transcription/mlx_whisper.py` (Apple fast-path), `engines/transcription/faster_whisper.py` (CUDA fast-path).

---

### 3. AlignmentEngine

```python
@runtime_checkable
class AlignmentEngine(Protocol):
    """Refines word timestamps using forced phonetic alignment.
    
    Used as a post-pass when the TranscriptionEngine does NOT produce
    phoneme-level output natively (i.e., engine.supports_phoneme_alignment is False).
    
    The orchestrator skips this step when transcription already includes phonemes."""
    
    def align(
        self,
        vocals: Path,
        words: list[WordEvent],
        language: str,
    ) -> AlignmentResult:
        """Args:
            vocals: Vocal stem.
            words: WordEvents from transcription (timestamps may be coarse).
            language: ISO 639-1.
        
        Returns:
            AlignmentResult with refined words + phonemes.
        
        Raises:
            AlignmentError.
        """
        ...
    
    @property
    def info(self) -> EngineInfo: ...
```

**Implementações v0.1:** `engines/alignment/torchaudio_align.py` (forced alignment via `torchaudio.functional.forced_align`, MPS+CUDA).

---

### 4. ChordRecognitionEngine

```python
@runtime_checkable
class ChordRecognitionEngine(Protocol):
    """Detects chord progression from harmonic content."""
    
    def detect(
        self,
        harmonic_mix: Path,
        bass_stem: Path | None = None,
    ) -> list[ChordEvent]:
        """Args:
            harmonic_mix: Audio file (typically `other` stem + `bass` stem mixed,
                or full mix if separation isn't desired).
            bass_stem: Optional separate bass stem. When provided, engine MAY
                use it for slash-chord (inversion) detection.
        
        Returns:
            Sequence of ChordEvent ordered by timestamp.start.
        
        Raises:
            ChordRecognitionError.
        """
        ...
    
    @property
    def info(self) -> EngineInfo: ...
    
    @property
    def vocabulary(self) -> Literal['majmin', 'sevenths', 'tetrads', 'extended_170']:
        """Self-reported chord vocabulary support.
        - 'majmin': 24 + N (major/minor + no-chord). Chordino baseline.
        - 'sevenths': adds 7th-chord variants. ~50 classes.
        - 'tetrads': adds tetrad qualities (sus2, sus4, dim7, etc.).
        - 'extended_170': BTC-ISMIR19 vocabulary including slash chords. 170 classes.
        """
        ...
    
    @property
    def supports_inversions(self) -> bool: ...
```

**Implementações v0.1:** `engines/chord/chordino.py` (vocab=`majmin` + bass note → derive inversions).
**Implementações v0.2:** `engines/chord/btc_ismir19.py` (vocab=`170-class`).
**Phase-2 pattern:** `engines/chord/learnable.py` wraps qualquer base engine + aplica `CorrectionLog`.

---

### 5. BeatTrackingEngine

```python
@runtime_checkable
class BeatTrackingEngine(Protocol):
    """Tracks beats, downbeats, tempo, and meter."""
    
    def track(self, audio: Path) -> BeatGrid:
        """Args:
            audio: Source audio (full mix preferred, can be drum stem).
        
        Returns:
            BeatGrid with beats, downbeats, BPM, meter, confidence.
        
        Raises:
            BeatTrackingError.
        """
        ...
    
    @property
    def info(self) -> EngineInfo: ...
    
    @property
    def supports_variable_tempo(self) -> bool: ...
    
    @property
    def supports_meter_detection(self) -> bool:
        """True if engine outputs (numerator, denominator) detection.
        False means engine assumes 4/4 unless overridden."""
        ...
```

**Implementações v0.1:** `engines/beat/beatthis.py` (CPJKU 2024, MPS+CUDA).

---

### 6. SyllabificationEngine

```python
@runtime_checkable
class SyllabificationEngine(Protocol):
    """Decomposes words into syllables, with stress detection.
    
    One implementation per language (English, Portuguese)."""
    
    def syllabify(
        self,
        words: list[WordEvent],
        phonemes: list[PhonemeEvent] | None = None,
    ) -> list[SyllableEvent]:
        """Args:
            words: WordEvents to decompose.
            phonemes: Phoneme-level alignments if available.
                When provided, syllable timestamps are derived from phoneme spans
                via Maximum Onset Principle. When None, syllables are derived from
                orthography only and timestamps are linearly interpolated within
                the parent word.
        
        Returns:
            SyllableEvents ordered by timestamp.start.
        """
        ...
    
    @property
    def language(self) -> str:
        """ISO 639-1 code: 'en', 'pt'."""
        ...
    
    @property
    def info(self) -> EngineInfo: ...
```

**Implementações v0.1:** `engines/lang/english.py` (g2p_en + CMU stress), `engines/lang/portuguese.py` (gruut + orthographic stress).

---

## Core Data Schemas

Definidos em `core/schemas.py`:

### Time and confidence primitives

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Self
from datetime import datetime
from pathlib import Path

class TimeStamp(BaseModel):
    """Time interval in seconds from start of audio."""
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    
    @field_validator('end')
    @classmethod
    def end_after_start(cls, v: float, info) -> float:
        if 'start' in info.data and v < info.data['start']:
            raise ValueError('end must be >= start')
        return v
    
    @property
    def duration(self) -> float:
        return self.end - self.start
```

```python
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
```

### Event types (transcription, chord, beat, etc.)

```python
class WordEvent(BaseModel):
    """A transcribed word with timestamp and confidence."""
    text: str
    timestamp: TimeStamp
    confidence: Confidence = 1.0
    source_engine: str
    language: str | None = None  # ISO 639-1

class PhonemeEvent(BaseModel):
    """A phoneme (IPA or ARPABET) with timestamp and word reference."""
    symbol: str
    timestamp: TimeStamp
    parent_word_idx: int = Field(ge=0)
    confidence: Confidence = 1.0

class SyllableEvent(BaseModel):
    """A syllable derived from phonemes via Maximum Onset Principle, or from
    orthography when phonemes are unavailable."""
    text: str  # orthographic form, e.g. "hel" of "hello"
    phoneme_indices: list[int] = []  # indices into the phoneme list
    timestamp: TimeStamp
    is_stressed: bool
    parent_word_idx: int = Field(ge=0)
    confidence: Confidence = 1.0

class ChordEvent(BaseModel):
    """A detected chord with optional bass note for slash-chord support.
    
    `bass_note` may be supplied independently when the engine extracted bass
    from the bass stem (e.g. Chordino). When `symbol` already encodes a slash
    chord (e.g. "C/E"), `bass_note` MUST agree or be None — enforced by validator."""
    
    symbol: str  # "C", "Am", "Cmaj7", "G/B"
    timestamp: TimeStamp
    bass_note: str | None = None
    confidence: Confidence = 1.0
    source_engine: str
    
    @model_validator(mode='after')
    def validate_bass_consistency(self) -> Self:
        if '/' in self.symbol and self.bass_note is not None:
            symbol_bass = self.symbol.rsplit('/', 1)[1].strip()
            if symbol_bass != self.bass_note:
                raise ValueError(
                    f"chord symbol bass {symbol_bass!r} disagrees with "
                    f"bass_note field {self.bass_note!r}"
                )
        return self
    
    @property
    def is_slash(self) -> bool:
        return '/' in self.symbol or self.bass_note is not None
    
    @property
    def effective_bass(self) -> str | None:
        """Returns the bass note from either source, normalized."""
        if self.bass_note:
            return self.bass_note
        if '/' in self.symbol:
            return self.symbol.rsplit('/', 1)[1].strip()
        return None
```

### Beat grid

```python
class BeatGrid(BaseModel):
    """Beat positions, downbeats, tempo, and meter for a song."""
    beats: list[float]  # seconds, monotonically increasing
    downbeat_indices: list[int]  # indices into beats[] that are beat 1 of measure
    bpm: float = Field(gt=0)
    bpm_variable: bool = False
    meter: tuple[int, int] = (4, 4)  # (numerator, denominator)
    confidence: Confidence = 1.0
    source_engine: str
    
    @field_validator('beats')
    @classmethod
    def beats_monotonic(cls, v: list[float]) -> list[float]:
        if any(v[i] >= v[i+1] for i in range(len(v)-1)):
            raise ValueError('beats must be strictly monotonically increasing')
        return v
    
    @field_validator('meter')
    @classmethod
    def meter_valid(cls, v: tuple[int, int]) -> tuple[int, int]:
        if v[0] <= 0 or v[1] not in {2, 4, 8, 16}:
            raise ValueError(f'invalid meter {v}')
        return v
```

### Stems

```python
class StemSet(BaseModel):
    """Output of source separation: 4 stem files + metadata."""
    audio_id: str  # sha256 of source audio
    vocals: Path
    bass: Path
    drums: Path
    other: Path
    sample_rate: int = 44100
    duration: float = Field(gt=0)
    source_engine: str
```

### Result wrappers (for engine returns)

```python
class TranscriptionResult(BaseModel):
    words: list[WordEvent]
    phonemes: list[PhonemeEvent] | None = None
    detected_language: str | None = None

class AlignmentResult(BaseModel):
    words: list[WordEvent]      # refined timestamps
    phonemes: list[PhonemeEvent]
```

---

## Document Schemas

A saída final, modelada como árvore. Em `writer/document.py`:

```python
class ChordMarker(BaseModel):
    """A chord pinned to a specific character position in a rendered line."""
    chord: ChordEvent
    char_position: int = Field(ge=0)
    placement_strategy: Literal[
        'stressed_syllable',
        'any_syllable',
        'before_word',
        'beat_boundary',
    ]

class LyricLine(BaseModel):
    """A line of lyrics with chord markers placed at character positions."""
    line_type: Literal['lyric'] = 'lyric'
    text: str  # plain text
    chord_markers: list[ChordMarker]
    word_alignments: list[WordEvent] = []  # for traceability / phase-2 editing
    syllable_alignments: list[SyllableEvent] = []
    confidence: Confidence = 1.0

class InstrumentalLine(BaseModel):
    """A line representing instrumental measures (intro, solo break, outro)."""
    line_type: Literal['instrumental'] = 'instrumental'
    chords: list[ChordEvent]  # chords sounding during these measures
    measures: int = Field(gt=0)
    pattern_hint: Literal['full_measure', 'half_measure', 'beat'] = 'full_measure'
    label: str | None = None  # 'Intro', 'Solo', etc.

# Discriminated union for type-safe section content
Line = Annotated[LyricLine | InstrumentalLine, Field(discriminator='line_type')]

class Section(BaseModel):
    """A song section: verse, chorus, bridge, instrumental."""
    type: Literal[
        'verse', 'chorus', 'bridge', 'pre-chorus',
        'instrumental', 'intro', 'outro',
    ]
    label: str  # 'Verse 1', 'Chorus', 'Solo'
    lines: list[Line]
    timestamp: TimeStamp

class Metadata(BaseModel):
    """Structured song metadata. Maps to ChordPro {directives}."""
    title: str
    artist: str | None = None
    key: str | None = None  # 'C', 'Am', 'F# major'
    tempo: int | None = Field(None, ge=20, le=300)  # BPM
    time_signature: tuple[int, int] | None = None
    capo: int = Field(0, ge=0, le=12)
    extensions: dict[str, str] = {}  # for {meta: titan_*} pass-through

class ChordProDocument(BaseModel):
    """The final output document, renderable to a .chordpro file."""
    metadata: Metadata
    sections: list[Section]
    provenance: Provenance
    
    def to_string(self, profile: str = 'chordpro_ref') -> str:
        """Render the document using the specified output profile."""
        ...
    
    def write(self, path: Path, profile: str = 'chordpro_ref') -> None:
        path.write_text(self.to_string(profile), encoding='utf-8')
```

---

## Provenance

Em `core/schemas.py`. Cada documento carrega audit trail completo:

```python
class EngineInfo(BaseModel):
    """Identification of a concrete engine instance."""
    name: str          # 'whisper.cpp', 'chordino', 'beatthis'
    version: str       # '0.5.0'
    backend: Literal['cuda', 'mps', 'mlx', 'coreml', 'cpu']
    model_id: str | None = None  # 'large-v3-turbo', etc.
    
    model_config = ConfigDict(frozen=True)

class StageConfidence(BaseModel):
    """Aggregated confidence for a pipeline stage."""
    stage: Literal[
        'separation', 'transcription', 'alignment',
        'chord_recognition', 'beat_tracking', 'syllabification',
        'fusion',
    ]
    mean: Confidence
    median: Confidence
    p10: Confidence  # bottom 10% — flags unreliable regions

class EngineRegistry(BaseModel):
    """Type-safe map of pipeline stages to the EngineInfo that produced their output."""
    separation: EngineInfo
    transcription: EngineInfo
    alignment: EngineInfo | None = None  # None when transcription engine
                                         # produces phonemes natively
    chord_recognition: EngineInfo
    beat_tracking: EngineInfo
    syllabification: EngineInfo  # the language-specific impl that ran
    
    model_config = ConfigDict(frozen=True)

class Provenance(BaseModel):
    """Audit trail for a ChordProDocument: what produced it, when, with what confidence."""
    titan_version: str
    audio_id: str  # sha256 of source audio
    engines: EngineRegistry
    started_at: datetime
    completed_at: datetime
    confidence: list[StageConfidence]
    
    model_config = ConfigDict(frozen=True)
```

---

## Phase-2 Schemas (Correction + CorrectionLog)

Em `core/schemas.py`. **Definidos em v0.1, não consumidos em v0.1**. Reservam o ponto de extensão para a phase 2 (editor app).

```python
class Correction(BaseModel):
    """A single user correction to a Titan output, captured by a phase-2 app."""
    audio_id: str  # ties correction to specific audio
    timestamp: float = Field(ge=0)  # second in original audio
    field: Literal[
        'chord_symbol',         # changed C → Cm
        'chord_position',       # moved chord to different syllable/char
        'word_text',            # fixed transcription error
        'word_timestamp',       # adjusted word timing
        'syllable_position',    # different syllable carries the chord
        'beat_position',        # corrected a misdetected beat
        'meter',                # changed 4/4 → 6/8
    ]
    original: dict  # serialized original event (json-safe)
    corrected: dict  # serialized corrected event
    user_id: str | None = None  # for multi-user phase-2 deployments
    note: str | None = None  # optional user comment
    created_at: datetime

class CorrectionLog(BaseModel):
    """A bundle of corrections for one audio file. Persisted as JSON."""
    audio_id: str
    corrections: list[Correction] = []
    schema_version: int = 1
    
    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.model_validate_json(path.read_text())
    
    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2))
```

**Como phase-2 usa isso:**

```python
# Phase 2 pseudocode (NOT in v0.1 — just illustrating how schemas are reused):

# 1. User opens a song in the editor, drags a chord:
correction = Correction(
    audio_id="abc123...",
    timestamp=12.45,
    field='chord_position',
    original={'symbol': 'C', 'char_position': 0, 'syllable_idx': 0},
    corrected={'symbol': 'C', 'char_position': 4, 'syllable_idx': 1},
    created_at=datetime.now(),
)
log.corrections.append(correction)
log.save("corrections/abc123.json")

# 2. Next time the song is processed, a LearnableChordEngine wraps the base:
class LearnableChordEngine:
    def __init__(self, base: ChordRecognitionEngine, log: CorrectionLog):
        self.base = base
        self.log = log
    
    def detect(self, harmonic_mix, bass_stem=None):
        events = self.base.detect(harmonic_mix, bass_stem)
        return apply_corrections(events, self.log)
```

V0.1 não implementa nada disso, mas as estruturas estão prontas.

---

## Validation rules (cheat-sheet)

| Schema | Regra |
|---|---|
| `TimeStamp` | `start >= 0`, `end >= start` |
| `Confidence` | `0 <= x <= 1` |
| `BeatGrid.beats` | strictly monotonically increasing |
| `BeatGrid.bpm` | `> 0` |
| `BeatGrid.meter` | numerator `> 0`, denominator ∈ {2,4,8,16} |
| `StemSet.duration` | `> 0` |
| `ChordMarker.char_position` | `>= 0` |
| `Section.lines` | non-empty |

Validações são **fail-fast**: violações lançam `pydantic.ValidationError` na construção.

---

## JSON serialization (cache + phase-2)

Toda a hierarquia de schemas é JSON-serializável. Caso de uso primário em v0.1: **cache opcional**.

```python
# Pipeline cache layout (when cache=True):
.titan-cache/
└── <sha256-do-audio>/
    ├── stems.json              # StemSet
    ├── transcription.json      # TranscriptionResult
    ├── alignment.json          # AlignmentResult
    ├── chords.json             # list[ChordEvent]
    ├── beats.json              # BeatGrid
    ├── document.json           # ChordProDocument (final)
    └── provenance.json         # Provenance
```

Cache é opt-in (`transcribe(..., cache=True)`). Default off para evitar surprise disk writes.

Phase-2 usa o mesmo formato JSON para `corrections/<audio_id>.json` (`CorrectionLog`).

---

## Test strategy: mock engines

Para testar `fusion/`, `writer/`, `orchestrator.py` sem rodar nenhum modelo, cada Protocol tem mock:

```python
# tests/mocks/engines.py

class MockTranscriptionEngine:
    """Returns hardcoded WordEvents from a JSON fixture file."""
    
    def __init__(self, fixture_path: Path):
        self.fixture = fixture_path
    
    def transcribe(self, vocals: Path, language=None) -> TranscriptionResult:
        return TranscriptionResult.model_validate_json(
            self.fixture.read_text()
        )
    
    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name='mock', version='0', backend='cpu')
    
    @property
    def supports_phoneme_alignment(self) -> bool:
        return True
```

Idem para todos os Engines. Permite:
- Testes unitários do fusion engine sem GPU
- Reprodutibilidade total (fixtures versionados)
- Testes de regressão do orchestrator
- CI sem dependência de modelos pesados

---

## Pontos para review

Áreas onde feedback seu é especialmente útil:

- **Granularidade dos Protocols** — 6 protocols é certo? Algum deve ser fundido (ex: AlignmentEngine pode virar parte do TranscriptionEngine)?
- **`SyllabificationEngine` em `engines/lang/`** — ela é menos "ML" que as outras (mais regras + dicionário). Faz sentido estar em `engines/` ou deveria ir para `fusion/syllabifier.py` direto?
- **`ChordEvent.bass_note` separado vs codificado em `symbol`** — atualmente permito ambos. Deveria ser obrigatoriamente um ou outro?
- **`SyllableEvent.phoneme_indices`** vs guardar `list[PhonemeEvent]` direto — eficiência (referência) vs simplicidade (dado direto)?
- **`Provenance.confidence`** — incluir agregados (`mean`, `median`, `p10`) ou só média?
- **`CorrectionLog` schema** — campos suficientes? Falta algum (ex: device de origem, app version)?
- **Cache layout `.titan-cache/`** — diretório no cwd ou `~/.cache/titan-chordpro/` (XDG)? Ou ambos selecionáveis?
- **`Correction.original` e `corrected` como `dict`** — sacrifica type safety; alternativa seria union de schemas concretos. Qual prefere?
- **Discriminated union para `Line`** — `LyricLine | InstrumentalLine` precisa de mais variantes (ex: `RepeatLine` para `:|`, `CommentLine` para `{c: ...}`)?

Quando terminar o review, me avise no chat.

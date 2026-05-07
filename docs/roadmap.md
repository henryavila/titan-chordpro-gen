# Project: Audio-to-ChordPro Local Pipeline (Roadmap)

## Objective
Develop a local Python-based tool utilizing the power of the GTX 5070Ti GPU to convert audio files into **ChordPro** format (`.chordpro` / `.pro`). The focus is on professional precision: perfect syllabic alignment, quantized rhythmic grids, and transcription of instrumental sections (solos).

## 1. Problem and Vision
Current software often generates "floating" chords without musical time context. The goal here is to treat music as a **grid**. By identifying BPM and Measures (Downbeats), the system can generate a chart that serves as a real guide for musicians, indicating exactly how long each chord lasts.

## 2. Detailed Solution Architecture

### Module A: Source Separation & Pre-processing (Demucs)
*   **Action:** Separate original audio into 4 stems: `vocals`, `bass`, `drums`, and `other`.
*   **Usage:**
    *   `vocals` -> Feeds Whisper (Module B).
    *   `bass` -> Defines the root note to prevent incorrect inversions.
    *   `other` + `bass` -> Chord and solo detection (Module C).
    *   `drums` -> Assists Beat Tracking in percussive tracks.

### Module B: Syllabic Transcription (Whisper + Timestamps)
*   **Model:** `OpenAI Whisper large-v3` via `faster-whisper`.
*   **Alignment Technology:** `stable-ts` or `whisper-timestamped`.
*   **Requirement:** Output must be a JSON with start/end timestamps for **every word**. This ensures the chord marker `[C]` lands exactly on the correct tonic/syllable.

### Module C: Chord, Solo, and Multi-path Detection
*   **Models:** `BTC-ISM` or `Chordino`.
*   **Instrumental Analysis:**
    *   Extract independent chord sheets for `bass` and `other` tracks.
    *   **Solo Logic:** If `vocals` are silent and there is high melodic activity in `other`, the system activates **Solo Transcription** mode.
*   **Tablature (ChordPro Syntax):** Utilize transcription models (such as `GuitarSet` based models) to generate plain text tabs:
    ```chordpro
    {start_of_tab}
    E|---0---1---0---|
    B|-1---3---1---3-|
    {end_of_tab}
    ```

### Module D: Master Clock (BPM & Beat Tracking)
*   **Tools:** `BeatNet` (Recurrent Neural Networks) or `Madmom`.
*   **Extracted Data:** BPM (static or variable) and **Downbeat** locations (Beat 1 of each measure).
*   **Grid Logic:** Create a timeline where each "slot" corresponds to a musical beat.
*   **Quantization:** If a chord is detected at 1.9s and Beat 2 is at 2.0s, the system "snaps" the chord to the exact musical beat (2.0s).
*   **Note:** The **Beat Tracking** system takes priority over raw chord detector timestamps to ensure the rhythmic aesthetic of the final file.

### Module E: Fusion Engine & Rhythmic Notation
*   **Intro/Instrumental Logic:** For measures without lyrics, apply the "slash" pattern:
    *   **4/4:** `[C] x///` (Full measure) | `[C] x/ [G] x/` (Half measure).
    *   **6/8:** `[C] x// ///` (Grouped visualization).
*   **Lyrics Alignment:** Interpolate word timestamps within the quantized chord grid.

## 3. Technical Specifications
*   **Hardware:** GTX 5070Ti (CUDA 12.x).
*   **Key Libraries:**
    *   `demucs`: Source separation.
    *   `faster-whisper`: Fast transcription.
    *   `beatnet`: Rhythmic intelligence.
    *   `pydantic`: For internal data structure validation (Time Schema).

## 4. Workflow (MVP)
1.  **Ingestion:** Audio upload and hardware analysis.
2.  **Separation:** Execute Demucs HT.
3.  **Rhythmic Analysis:** BPM definition and measure "Grid" creation.
4.  **Harmonic/Textual Analysis:** Lyric transcription and per-instrument chord/solo detection.
5.  **Quantized Fusion:** The script "fits" lyrics and chords into the rhythmic grid.
6.  **Export:** Save the `.chordpro` file.

## 5. Research & Development (docs/research)
The AI Coding Agent must mandatory research and document:
*   **Official Tab Tags:** Validation of `{sot}`/`{eot}` (start/end of tab) tags and support in apps (e.g., ChordPro.org).
*   **Inversion Handling:** How the `bass` stem should influence naming (e.g., `C` chord with an `E` bass generating `C/E`).
*   **Solo Heuristics:** Define note density thresholds to differentiate "rhythm guitar" from "guitar solos."

## 6. Scope Declaration
The MVP must deliver a functional CLI that processes a track and outputs a ChordPro file with rhythmic intros (`x///`), word-aligned verses, and solo sections represented in simple tablature. Future expansions will include a GUI and playback of isolated stems.


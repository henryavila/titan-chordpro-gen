# Titan ChordPro Lib 🚀

[![Python Version](https://shields.io)](https://python.org)
[![CUDA Acceleration](https://shields.io)](https://nvidia.com)
[![License: MIT](https://shields.io)](https://opensource.org)

**Titan ChordPro Lib** is a high-precision, AI-powered music transcription library. Unlike standard transcribers, Titan focuses on **musical metrics**, generating ChordPro files with a quantized rhythmic grid and perfect syllabic alignment.

## ✨ Key Features
*   **Rhythmic Grid (BPM Sync):** Goes beyond simple chord detection by organizing them into measures (e.g., `[C] x///`).
*   **Stem-Based Analysis:** Leverages source separation (Demucs) to independently analyze bass, harmonic instruments, and vocals.
*   **Syllabic Alignment:** Word-for-word synchronization of lyrics and chords using optimized Whisper models.
*   **Solo-to-Tab:** Automatically identifies instrumental sections and generates tabs within `{sot}`/`{eot}` tags.

## 🛠️ Pipeline Architecture
The project is divided into independent modules. You can explore the full details in our [Architecture Documentation and Roadmap](docs/roadmap.md):
1.  **Isolation (Demucs):** Source separation for clean analysis.
2.  **Transcription (Faster-Whisper):** Lyrics with precise millisecond timestamps.
3.  **Harmony (BTC-ISM/Chordino):** Chord detection with support for inversions (slash chords).
4.  **Beat Tracking (BeatNet):** The "master clock" that defines BPM and the measure grid.

## 🚀 Hardware Requirements
Optimized for NVIDIA GPUs with CUDA support for real-time or ultra-fast performance.
*   **Recommended Hardware:** NVIDIA RTX 30-series / 40-series or higher (Developed and tested on a **GTX 5070Ti**).
*   **VRAM:** 8GB minimum (12GB+ recommended for running `large-v3` models).

## 📦 Installation (Preview)
```bash
# Clone the repository
git clone https://github.com

# Install dependencies (Requires CUDA 12.x drivers)
pip install -r requirements.txt
```

## 🗺️ Roadmap
Development is staged from a CLI-based MVP to full tab extraction and support for complex time signatures (6/8, 7/8). See `docs/roadmap.md` for details.

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

---
Built by music and technology enthusiasts.


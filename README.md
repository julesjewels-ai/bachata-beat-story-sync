# Bachata Beat-Story Sync

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![FFmpeg 4.0+](https://img.shields.io/badge/ffmpeg-4.0%2B-green.svg)
![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)

An automated video editing tool that analyzes Bachata audio tracks (`.wav` / `.mp3`) to detect rhythm, beats, and emotional peaks, then intelligently syncs video clips to the musical dynamics to produce a cohesive montage.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Available Scripts](#available-scripts)
- [Architecture](#architecture)
- [Testing](#testing)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

| Feature | Status |
|---------|--------|
| Audio Beat & Onset Detection (Librosa) | ✅ |
| Video Motion-Intensity Scoring (OpenCV) | ✅ |
| Automated Video Montage Generation (FFmpeg) | ✅ |
| Excel Analysis Reports with Charts & Thumbnails | ✅ |
| Rich Console Progress Feedback | ✅ |
| B-roll Clip Insertion | ✅ |
| Slow-Motion Frame Interpolation (FEAT-010) | ✅ |
| Forced Clip Sequence Ordering | ✅ |
| Musical Section Segmentation (FEAT-008) | ✅ |
| Intensity-Matched Clip Selection (FEAT-009) | ✅ |
| Section-Aware Transitions / xfade (FEAT-011) | ✅ |
| Video Style / Color Grading (FEAT-012) | ✅ |
| Audio-Reactive Visualizer Overlay (FEAT-013) | ✅ |
| Waveform Overlay Padding / Margins (FEAT-021) | ✅ |
| Full Pipeline Orchestrator (FEAT-014) | ✅ |
| YouTube Shorts Batch Generator (FEAT-015) | ✅ |
| Audio Track Mixing with Crossfades | ✅ |
| Decision Explainability Log `--explain` (FEAT-025) | ✅ |
| Intro Effects — Bloom & Vignette Breathe (FEAT-022) | ✅ |
| Pacing Visual Effects (FEAT-023) | ✅ |
| Advanced Beat-Synced Effects (FEAT-024) | ✅ |
| Dry-Run Plan Mode `--dry-run` (FEAT-026) | ✅ |
| Genre Preset System `--genre` (FEAT-027) | ✅ |
| Structured JSON Output `--output-json` (FEAT-028) | ✅ |
| File Watcher `--watch` (FEAT-029) | ✅ |
| Per-Track Video Clip Pools (FEAT-030) | ✅ |
| Per-Track Video Style Filters (FEAT-031) | ✅ |
| Organic Per-Beat Speed Ramping (FEAT-036) | ✅ |
| Smart Start Detection | ✅ |
| Shared Video Scan Mode | ✅ |
| Sentiment-based Clip Matching | 🔜 Planned |
| Narrative Arc Construction | 🔜 Planned |
| AI Multimodal Analysis (Gemini) | 🔜 Planned |

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Core runtime |
| Librosa | Audio analysis (BPM, beats, sections) |
| OpenCV | Video frame analysis & intensity scoring |
| FFmpeg | Video/audio extraction, assembly, transitions, & visualizers |
| Pydantic | Input validation & DTOs |
| openpyxl | Excel report generation |
| Rich | Console progress bars |
| PyYAML | Configuration loading |
| Pillow | Image processing & thumbnails |

---

## Prerequisites

- **Python** 3.11+ — the Makefile targets 3.13
- **FFmpeg** 4.0+ ([install guide](https://ffmpeg.org/download.html))
- **uv** (recommended) or **pip** — the Makefile uses `uv` for environment setup

---

## Getting Started

### 1. Clone and Install

```bash
git clone https://github.com/julesjewels-ai/bachata-beat-story-sync.git
cd bachata-beat-story-sync
make install
source venv/bin/activate
```

### 2. Configure Environment

```bash
cp .env.example .env   # LOG_LEVEL and FFMPEG_BINARY_PATH
```

### 3. Verify Installation

```bash
make test
```

### 4. Run Your First Montage

```bash
# Basic montage
python main.py --audio my_track.wav --video-dir ./clips/

# Test mode — 4 clips, 10s of music, fast iteration
python main.py --audio my_track.wav --video-dir ./clips/ --test-mode

# With Excel report
python main.py --audio my_track.wav --video-dir ./clips/ --export-report report.xlsx
```

### 5. Go Further

```bash
# B-roll + vintage grading + intro effect
make run AUDIO=my_track.wav VIDEO_DIR=./clips/ VIDEO_STYLE=vintage INTRO_EFFECT=bloom

# Audio-reactive overlay
make run AUDIO=my_track.wav VIDEO_DIR=./clips/ AUDIO_OVERLAY=waveform

# Decision explainability — see why each clip was chosen
make run AUDIO=my_track.wav VIDEO_DIR=./clips/ EXPLAIN=1

# YouTube Shorts
make run-shorts AUDIO=my_track.wav VIDEO_DIR=./clips/ SHORTS_COUNT=3

# Full pipeline — mix + individual videos + shorts
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ TEST_MODE=1
```

---

## Available Scripts

| Command | Description | Key Variables |
|---------|-------------|---------------|
| `make install` | Create venv (uv) and install all deps | — |
| `make run` | Single-track montage | `AUDIO`, `VIDEO_DIR`, `TEST_MODE`, `MAX_CLIPS`, `MAX_DURATION`, `VIDEO_STYLE`, `AUDIO_OVERLAY`, `EXPLAIN`, `INTRO_EFFECT`, `SMART_START` |
| `make run-shorts` | Generate YouTube Shorts | `AUDIO`, `VIDEO_DIR`, `SHORTS_COUNT`, `SHORTS_DURATION` |
| `make full-pipeline` | Mix + videos + shorts | All `run` vars + `OUTPUT_DIR`, `SHARED_SCAN` |
| `make test` | Run pytest suite | — |
| `make lint` | Lint with ruff | — |
| `make format` | Auto-format + import sort | — |
| `make check-types` | Type-check with mypy | — |
| `make clean` | Remove venv, caches, outputs | — |

All montage behavior is further configurable via [`montage_config.yaml`](montage_config.yaml) — see [docs/user/configuration.md](docs/user/configuration.md) for the full reference.

---

## Architecture

```
├── main.py                    # CLI entry point (single-track mode)
├── montage_config.yaml        # Default pacing & effects config
├── src/
│   ├── core/                  # Domain logic
│   │   ├── app.py             #   BachataSyncEngine orchestrator
│   │   ├── audio_analyzer.py  #   Librosa beat detection & sections
│   │   ├── video_analyzer.py  #   OpenCV motion-intensity scoring
│   │   ├── montage.py         #   Clip selection & sequencing engine
│   │   ├── ffmpeg_renderer.py #   FFmpeg command assembly & rendering
│   │   ├── ffmpeg_utils.py    #   Shared FFmpeg filter helpers
│   │   ├── audio_mixer.py     #   Multi-track mixing & crossfades
│   │   ├── genre_presets.py   #   Genre-specific default configurations
│   │   ├── models.py          #   Pydantic DTOs (PacingConfig, etc.)
│   │   ├── interfaces.py      #   Observer protocols
│   │   └── validation.py      #   Input guards
│   ├── services/reporting/    #   Excel report generation
│   ├── ui/console.py          #   Rich progress observer
│   ├── cli_utils.py           #   Shared CLI argument building
│   ├── pipeline.py            #   Full-pipeline orchestrator
│   └── shorts_maker.py        #   YouTube Shorts generator
├── tests/unit/                #   9 pytest test files
└── docs/                      #   7 documentation files
```

### Data Flow

```
Audio (.wav/.mp3)                    Video Clips (.mp4)
       │                                    │
       ▼                                    ▼
  Audio Analyzer                     Video Analyzer
  (BPM, beats, sections)            (motion intensity)
       │                                    │
       └──────────────┬─────────────────────┘
                      ▼
              Montage Engine
        (match, sequence, pace)
                      │
                      ▼
              FFmpeg Renderer
        (assemble, grade, overlay)
                      │
                      ▼
               output_story.mp4
```

---

## Testing

```bash
make test                              # all tests
venv/bin/pytest tests/unit/test_montage.py   # single file
venv/bin/pytest -k "section"           # by keyword
```

---

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [User Guide](docs/user/user-guide.md) | Users | Installation, CLI usage, troubleshooting |
| [API Reference](docs/user/api-reference.md) | Developers | Class/function signatures and behavior |
| [Configuration](docs/user/configuration.md) | Users & Devs | CLI args, env vars, output specs |
| [Contributing](docs/user/contributing.md) | Developers | Dev setup, coding standards, testing |
| [Security](docs/user/security.md) | Stakeholders | Security posture, mitigations, risks |

For internal documentation (team/stakeholders only), see [`docs/internal/`](docs/internal/README.md).

---

## Troubleshooting

### FFmpeg Not Found

Verify with `ffmpeg -version`. If installed but not found, set `FFMPEG_BINARY_PATH` in `.env`:
```
FFMPEG_BINARY_PATH=/opt/homebrew/bin/ffmpeg
```

### Python Version Mismatch

This project requires **Python 3.11+**. The Makefile targets 3.13. If `python3.13` isn't available, update the `PYTHON` variable in the `Makefile`.

### Missing Audio or Video Files

`--audio` must point to a valid `.wav`/`.mp3` file, `--video-dir` to a directory with `.mp4` files. B-roll is auto-detected from a `broll/` subdirectory inside `--video-dir`.

### Dependency Issues

```bash
make clean && make install && source venv/bin/activate
```

---

## License

See [LICENSE](LICENSE) for details.

# Bachata Beat-Story Sync

An automated video editing tool that analyzes Bachata audio tracks (`.wav` / `.mp3`) to detect rhythm, beats, and emotional peaks, then intelligently syncs video clips to the musical dynamics to produce a cohesive montage.

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
| Full Pipeline Orchestrator (FEAT-014) | ✅ |
| YouTube Shorts Batch Generator (FEAT-015) | ✅ |
| Audio Track Mixing with Crossfades | ✅ |
| Decision Explainability Log `--explain` (FEAT-025) | ✅ |
| Sentiment-based Clip Matching | 🔜 Planned |
| Narrative Arc Construction | 🔜 Planned |
| AI Multimodal Analysis (Gemini) | 🔜 Planned |

## Prerequisites

- **Python** 3.9+
- **ffmpeg** 4.0+ ([install guide](https://ffmpeg.org/download.html))
- **pip** (latest)

## Quick Start

<p align="center">
  <img src="docs/assets/editor_banner.png" alt="Video editor compiling footage" width="100%">
</p>

```bash
# Clone and install
git clone <repo-url>
cd bachata-beat-story-sync
make install
source venv/bin/activate

# Single-track montage
python main.py --audio my_track.wav --video-dir ./clips/

# With Excel report
python main.py --audio my_track.wav --video-dir ./clips/ --export-report report.xlsx

# With B-roll and video style (options: none, bw, vintage, warm, cool, golden)
python main.py --audio my_track.wav --video-dir ./clips/ --broll-dir ./broll/ --video-style vintage

# With audio-reactive waveform overlay
make run AUDIO=my_track.wav VIDEO_DIR=./clips/ AUDIO_OVERLAY=waveform

# With frequency bars at custom opacity
make run AUDIO=my_track.wav VIDEO_DIR=./clips/ AUDIO_OVERLAY=bars AUDIO_OVERLAY_OPACITY=0.7

# Full pipeline — mix + individual videos + shorts (recommended)
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ TEST_MODE=1

# Full pipeline with vintage color grading
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ VIDEO_STYLE=vintage

# YouTube Shorts only
make run-shorts AUDIO=my_track.wav VIDEO_DIR=./clips/ SHORTS_COUNT=3

# Decision explainability log — see why each clip was chosen
make run AUDIO=my_track.wav VIDEO_DIR=./clips/ EXPLAIN=1

# Test mode (limits to max 4 clips and 10s of music)
python main.py --audio my_track.wav --video-dir ./clips/ --test-mode
```

## Development

```bash
make install         # Create venv and install dependencies
make run             # Run single-track montage
make run-shorts      # Generate YouTube Shorts
make full-pipeline   # Run full pipeline (mix + videos + shorts)
make test            # Run test suite (pytest)
make lint            # Lint with ruff
make format          # Auto-format with ruff
make check-types     # Type-check with mypy
make clean           # Remove venv, caches, and output files
```

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [User Guide](docs/user-guide.md) | Users | Installation, CLI usage, troubleshooting |
| [Architecture](docs/architecture.md) | Developers | System design, diagrams, patterns |
| [API Reference](docs/api-reference.md) | Developers | Class/function signatures and behavior |
| [Configuration](docs/configuration.md) | Users & Devs | CLI args, env vars, output specs |
| [Contributing](docs/contributing.md) | Developers | Dev setup, coding standards, testing |
| [Security](docs/security.md) | Stakeholders | Security posture, mitigations, risks |
| [Audit Report](docs/audit-report.md) | Stakeholders | Full project audit findings |

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.9+ | Core runtime |
| Librosa | Audio analysis (BPM, beats, sections) |
| OpenCV | Video frame analysis & intensity scoring |
| FFmpeg | Video/audio extraction, assembly, transitions, & visualizers |
| Pydantic | Input validation & DTOs |
| openpyxl | Excel report generation |
| Rich | Console progress bars |
| PyYAML | Configuration loading |

## License

See [LICENSE](LICENSE) for details.

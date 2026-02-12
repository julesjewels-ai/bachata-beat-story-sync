# Bachata Beat-Story Sync

An automated video editing tool that analyzes Bachata audio tracks (`.wav` / `.mp3`) to detect rhythm, beats, and emotional peaks, then intelligently syncs video clips to the musical dynamics to produce a cohesive montage.

## Features

| Feature | Status |
|---------|--------|
| Audio Beat & Onset Detection (Librosa) | ✅ |
| Video Motion-Intensity Scoring (OpenCV) | ✅ |
| Automated Video Montage Generation (MoviePy) | ✅ |
| Excel Analysis Reports with Charts & Thumbnails | ✅ |
| Rich Console Progress Feedback | ✅ |
| Musical Section Segmentation | 🔜 Planned |
| Sentiment-based Clip Matching | 🔜 Planned |
| Narrative Arc Construction | 🔜 Planned |
| AI Multimodal Analysis (Gemini) | 🔜 Planned |

## Prerequisites

- **Python** 3.9+
- **ffmpeg** 4.0+ ([install guide](https://ffmpeg.org/download.html))
- **pip** (latest)

## Quick Start

```bash
# Clone and install
git clone <repo-url>
cd bachata-beat-story-sync
make install
source venv/bin/activate

# Run
python main.py --audio my_track.wav --video-dir ./clips/

# With Excel report
python main.py --audio my_track.wav --video-dir ./clips/ --export-report report.xlsx
```

## Development

```bash
make install  # Create venv and install dependencies
make run      # Run the application
make test     # Run test suite (pytest)
make clean    # Remove venv, caches, and output files
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
| Librosa | Audio analysis |
| OpenCV | Video frame analysis |
| MoviePy | Video editing & export |
| Pydantic | Input validation & DTOs |
| openpyxl | Excel report generation |
| Rich | Console progress bars |

## License

See [LICENSE](LICENSE) for details.

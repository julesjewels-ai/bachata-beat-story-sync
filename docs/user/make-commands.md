# Make Commands Guide

This guide explains all available `make` commands and how to use them with variables.

---

## TL;DR — Common Commands

```bash
# 🎬 Generate a single video from one song
make run AUDIO=song.wav VIDEO_DIR=./clips/

# 🎬 Same, but fast iteration (test mode)
make run AUDIO=song.wav VIDEO_DIR=./clips/ TEST_MODE=1

# 📺 Generate YouTube Shorts (6-second clips)
make run-shorts AUDIO=song.wav VIDEO_DIR=./clips/ SHORTS_COUNT=5

# 🎵 Mix multiple songs + generate all videos
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/

# 🎵 Same, but also concatenate individual tracks into one compilation
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ COMPILATION=1

# ⚡ Development — format, lint, and test
make format lint-fix check-types test
```

---

## Installation & Setup

### `make install`

Creates a Python virtual environment and installs all dependencies.

```bash
make install
```

**What it does:**
- Creates `venv/` folder with Python 3.13
- Installs all packages from `requirements.txt`
- Installs development tools: `ruff`, `pytest`, `mypy`

**Run this once** after cloning the repo, or if `requirements.txt` changes.

---

## Single-Track Montage Generation

### `make run`

Generates a single video from one audio file and a directory of clips.

**Basic usage:**

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/
```

**Output:**
- `output_story.mp4` (default) — your generated montage

**Key variables:**

| Variable | Example | Purpose |
|----------|---------|---------|
| `AUDIO` | `song.wav` | **(Required)** Audio file to analyze and sync to |
| `VIDEO_DIR` | `./clips/` | **(Required)** Folder containing `.mp4` clips |
| `TEST_MODE` | `1` | Limits to 4 clips + 10 seconds — fast for iteration |
| `MAX_CLIPS` | `20` | Override max number of clips used |
| `MAX_DURATION` | `30` | Override max montage duration (seconds) |
| `VIDEO_STYLE` | `warm` | Color grading: `none`, `bw`, `vintage`, `warm`, `cool`, `golden` |
| `AUDIO_OVERLAY` | `waveform` | Visualizer: `waveform`, `bars` (or empty for none) |
| `AUDIO_OVERLAY_OPACITY` | `0.7` | Visualizer opacity (0.0–1.0) |
| `AUDIO_OVERLAY_POSITION` | `right` | Visualizer position: `left`, `center`, `right` |
| `INTRO_EFFECT` | `bloom` | Intro effect on first clip: `bloom`, `vignette_breathe`, `none` |
| `INTRO_EFFECT_DURATION` | `2.0` | Intro effect duration in seconds |
| `EXPLAIN` | `1` | Generate an explainability report showing why each clip was chosen |
| `DRY_RUN` | `1` | Plan only — skip rendering (fast preview) |
| `GENRE` | `bachata` | Apply a genre preset: `bachata`, `salsa`, `reggaeton`, `kizomba`, `merengue`, `pop` |
| `BROLL_INTERVAL` | `15` | Target interval between B-roll clips (seconds) |
| `BROLL_VARIANCE` | `2` | Allowed variance (± seconds) around B-roll interval |
| `ZOOM` | `1.1` | Ken Burns zoom factor (1.0 = no zoom) |

### Examples

**Fast test (10 seconds, 4 clips):**
```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ TEST_MODE=1
```

**With audio visualizer (waveform):**
```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ AUDIO_OVERLAY=waveform
```

**With color grading (warm vintage):**
```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ VIDEO_STYLE=warm
```

**With intro effect (bloom):**
```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ INTRO_EFFECT=bloom INTRO_EFFECT_DURATION=2
```

**With decision explainability log:**
```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ EXPLAIN=1
```
Generates `output_story_explain.md` showing why each clip was selected.

**Combined: Test mode + visualizer + color grade:**
```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ TEST_MODE=1 VIDEO_STYLE=golden AUDIO_OVERLAY=bars
```

---

## YouTube Shorts Generator

### `make run-shorts`

Generates short-form videos (YouTube Shorts format: 9:16 aspect ratio, 15–60 seconds).

**Basic usage:**

```bash
make run-shorts AUDIO=song.wav VIDEO_DIR=./clips/
```

**Output:**
- `shorts_001.mp4`, `shorts_002.mp4`, etc. — in the working directory

**Key variables:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIO` | — | **(Required)** Audio file |
| `VIDEO_DIR` | — | **(Required)** Clips folder |
| `SHORTS_COUNT` | `1` | How many shorts to generate |
| `SHORTS_DURATION` | `60` | Duration per short in seconds |
| `TEST_MODE` | `0` | Set to `1` for fast iteration |
| `VIDEO_STYLE` | — | Color grading (same options as `make run`) |
| `AUDIO_OVERLAY` | — | Visualizer (same options as `make run`) |

### Examples

**Generate 3 shorts, 30 seconds each:**
```bash
make run-shorts AUDIO=song.wav VIDEO_DIR=./clips/ SHORTS_COUNT=3 SHORTS_DURATION=30
```

**Generate 5 shorts in test mode (fast):**
```bash
make run-shorts AUDIO=song.wav VIDEO_DIR=./clips/ SHORTS_COUNT=5 TEST_MODE=1
```

---

## Full Pipeline

### `make full-pipeline`

Orchestrates the complete workflow:
1. **Mixes** multiple audio tracks with crossfades
2. **Generates** individual track videos (each synced to its own track)
3. **Optionally generates** a compilation video (concatenates individual tracks with transitions)
4. **Generates** YouTube Shorts

**Basic usage:**

```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/
```

**Output:**
- `output_pipeline/mix_video.mp4` — mixed audio + montage
- `output_pipeline/track_01.mp4`, `track_02.mp4`, etc. — individual track videos
- `output_pipeline/shorts/` — folder with YouTube Shorts
- (Optional) `output_pipeline/compilation.mp4` — concatenated track videos with transitions
- (Optional) `output_pipeline/compilation_chapters.json` + `.txt` — YouTube chapter markers

**Key variables:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDIO` | — | **(Required)** Path to folder containing `.wav`/`.mp3` audio files |
| `VIDEO_DIR` | — | **(Required)** Folder containing `.mp4` clips |
| `OUTPUT_DIR` | `output_pipeline` | Where to save all outputs |
| `COMPILATION` | `0` | Set to `1` to generate a compilation video; `0` to skip |
| `SKIP_MIX` | `0` | Set to `1` to skip generating the combined mix video (useful when you only want individual track videos or the compilation) |
| `SHARED_SCAN` | `0` | Set to `1` to reuse the same video analysis for all tracks (faster, less variation) |
| `TEST_MODE` | `0` | Set to `1` to generate test outputs (4 clips, 10s each) |
| `VIDEO_STYLE` | — | Color grading applied to all videos |
| `AUDIO_OVERLAY` | — | Visualizer applied to all videos |
| *All `make run` variables* | — | Can also use `MAX_CLIPS`, `MAX_DURATION`, `EXPLAIN`, etc. |

### Examples

**Full pipeline (mix + individual videos + shorts, no compilation):**
```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/
```

**Full pipeline with compilation:**
```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ COMPILATION=1
```

This also generates:
- `compilation.mp4` — all individual track videos concatenated with fade transitions
- `compilation_chapters.json` + `compilation_chapters.txt` — YouTube-ready chapter markers (track timestamps)

**Full pipeline with compilation + color grading:**
```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ COMPILATION=1 VIDEO_STYLE=warm
```

**Skip the mix video, generate only individual track videos + compilation:**
```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ SKIP_MIX=1 COMPILATION=1
```

Use this when the combined mix isn't coming out well and you just want the per-track videos concatenated together.

**Full pipeline in test mode (fast iteration):**
```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ TEST_MODE=1
```

**Full pipeline with shared video scan (faster, less clip variety):**
```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ SHARED_SCAN=1
```

**Full pipeline with custom output directory:**
```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ OUTPUT_DIR=./my_outputs/
```

---

## Web UI (Streamlit)

### `make ui`

Launches an interactive web interface for the montage generator.

```bash
make ui
```

**Opens:** `http://localhost:8501` in your browser

**Features:**
- Upload audio and video files
- Adjust pacing, effects, and style in real-time
- Preview settings before generating
- Download generated videos

---

## Development & Testing

### `make test`

Runs the full test suite via pytest.

```bash
make test
```

**Output:** Test results with pass/fail status

**Run a single test file:**
```bash
venv/bin/pytest tests/unit/test_montage.py -v
```

**Run tests matching a keyword:**
```bash
venv/bin/pytest -k "section" -v
```

---

### `make lint`

Checks code for style violations and potential bugs (uses `ruff`).

```bash
make lint
```

**Does NOT modify code** — only reports issues.

---

### `make format`

Auto-formats code and sorts imports.

```bash
make format
```

**Modifies code in-place** to match style standards:
- PEP 8 formatting via `ruff`
- Import sorting via `isort`

---

### `make check-types`

Type-checks Python code via `mypy` (catches type errors before runtime).

```bash
make check-types
```

---

### `make refactor`

Runs the complete developer workflow:
1. Formats code
2. Auto-fixes lint issues
3. Type-checks
4. Runs tests

```bash
make refactor
```

**Use this before committing** to ensure code quality.

---

### `make clean`

Removes all generated files and caches.

```bash
make clean
```

**Deletes:**
- `venv/` — virtual environment
- `__pycache__/` — bytecode caches
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` — tool caches
- `*.mp4` — generated videos

---

## Configuration via YAML

**All parameters above can also be set in [`montage_config.yaml`](../../montage_config.yaml)** at the project root. CLI flags always override YAML values.

Example `montage_config.yaml`:

```yaml
pacing:
  video_style: warm
  intro_effect: bloom
  intro_effect_duration: 2.0

compilation:
  enabled: true  # Default: generate compilation
  transition_type: fade
  transition_duration: 0.5
  include_chapter_markers: true

audio_mix:
  crossfade_duration: 1.0
```

---

## Environment Variables

Optional — set in `.env` file at project root:

```bash
LOG_LEVEL=DEBUG
FFMPEG_BINARY_PATH=/usr/bin/ffmpeg
```

See [docs/user/configuration.md](./configuration.md#environment-variables) for details.

---

## Troubleshooting

### Command not found: `make`

Install Make: [homebrew.io/](https://brew.sh/) (macOS) or apt/yum (Linux)

### Python version error

The Makefile targets Python 3.13. If you have a different version:

```bash
# Update Makefile's PYTHON variable
# PYTHON = python3.13  →  PYTHON = python3.11
```

### FFmpeg not found

```bash
# Install FFmpeg
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Linux
```

### Variables not being used

Variables are **case-sensitive** and require `=`:

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/  # ✅ Correct
make run audio=song.wav video_dir=./clips/  # ❌ Wrong (lowercase)
make run AUDIO song.wav VIDEO_DIR ./clips/  # ❌ Wrong (no =)
```

---

## Next Steps

- **Configuration deep-dive**: [docs/user/configuration.md](./configuration.md)
- **Genre presets**: [docs/user/configuration.md#pacing-configuration](./configuration.md#pacing-configuration-montageconfigyaml)
- **Troubleshooting**: [README.md#troubleshooting](../../README.md#troubleshooting)

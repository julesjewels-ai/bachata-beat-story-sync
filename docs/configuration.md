# Configuration Reference — Bachata Beat-Story Sync

> All configuration options, environment variables, and CLI arguments in one place.

---

## CLI Arguments

The tool is invoked via `python main.py` with the following arguments:

| Argument | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `--audio` | ✅ | `str` | — | Path to the input audio file (`.wav` or `.mp3`) |
| `--video-dir` | ✅ | `str` | — | Directory containing video clips to scan |
| `--output` | ❌ | `str` | `output_story.mp4` | Path for the generated output video |
| `--export-report` | ❌ | `str` | `None` | Path for the optional Excel analysis report |
| `--version` | ❌ | flag | — | Display version number and exit |

---

## Pacing Configuration (`montage_config.yaml`)

A YAML file in the project root that controls clip pacing — no code changes needed.

| Key | Default | Description |
|-----|---------|-------------|
| `min_clip_seconds` | `1.5` | Hard floor — no clip shorter than this |
| `high_intensity_seconds` | `2.5` | Target duration for energetic moments |
| `medium_intensity_seconds` | `4.0` | Target for standard pacing |
| `low_intensity_seconds` | `6.0` | Target for breathing room |
| `snap_to_beats` | `true` | Snap durations to beat boundaries |
| `high_intensity_threshold` | `0.65` | Intensity ≥ this is "high" |
| `low_intensity_threshold` | `0.35` | Intensity < this is "low" |

> If `montage_config.yaml` is missing, defaults above are used automatically.

---

## Environment Variables

Configured via a `.env` file in the project root. Copy `.env.example` to get started:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `FFMPEG_BINARY_PATH` | `/usr/bin/ffmpeg` | Path to the ffmpeg binary (used by MoviePy) |

> [!NOTE]
> Environment variables are currently not loaded by the application code — they serve as a template for future integration. Logging is hardcoded to `INFO` in `main.py`.

---

## Supported File Formats

### Audio Extensions
| Extension | Format |
|-----------|--------|
| `.wav` | Waveform Audio |
| `.mp3` | MPEG Audio Layer 3 |

### Video Extensions
| Extension | Format |
|-----------|--------|
| `.mp4` | MPEG-4 Part 14 |
| `.mov` | Apple QuickTime |
| `.avi` | Audio Video Interleave |
| `.mkv` | Matroska Video |

---

## Security Limits

These constants are defined in `src/core/video_analyzer.py` and protect against resource exhaustion:

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_VIDEO_FRAMES` | `100,000` | Rejects videos with more frames (~56 min at 30fps) |
| `MAX_VIDEO_DURATION_SECONDS` | `3,600` | Rejects videos longer than 1 hour |

---

## Output Specifications

The generated montage video uses these encoding settings (defined in `src/core/montage.py`):

| Setting | Value | Notes |
|---------|-------|-------|
| **Resolution** | 720p height | Width scales proportionally |
| **FPS** | 24 | Fixed frame rate |
| **Video codec** | `libx264` | H.264 encoding |
| **Audio codec** | `aac` | AAC encoding |
| **Preset** | `ultrafast` | Favors speed over compression |
| **Segment timing** | Time-based | Configurable via `montage_config.yaml` |

---

## Makefile Targets

| Target | Command | Description |
|--------|---------|-------------|
| `make install` | Create venv + install deps | Sets up `venv/` with all requirements |
| `make run` | Run `main.py` | Runs via venv Python (requires CLI args) |
| `make test` | Run pytest | Executes test suite via venv |
| `make clean` | Remove caches + outputs | Deletes `venv/`, `__pycache__/`, and `*.mp4` files |

---

## mypy Configuration

Type checking is configured in `mypy.ini`:

```ini
[mypy]
ignore_missing_imports = True    # Don't error on untyped third-party libs
check_untyped_defs = True        # Check function bodies even without annotations
disallow_untyped_defs = False    # Allow functions without type annotations
```

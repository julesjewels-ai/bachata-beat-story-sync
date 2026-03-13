# Configuration Reference — Bachata Beat-Story Sync

> All configuration options, environment variables, and CLI arguments in one place.

---

## CLI Arguments

The tool is invoked via `python main.py` with the following arguments:

| Argument | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `--audio` | ✅ | `str` | — | Path to the input audio file (`.wav` or `.mp3`) |
| `--video-dir` | ✅ | `str` | — | Directory containing video clips to scan |
| `--broll-dir` | ❌ | `str` | `video-dir/broll` | Optional directory for B-roll clips |
| `--output` | ❌ | `str` | `output_story.mp4` | Path for the generated output video |
| `--export-report` | ❌ | `str` | `None` | Path for the optional Excel analysis report |
| `--test-mode` | ❌ | flag | `False` | Run in test mode (limits to max 4 clips and 10s of music) |
| `--max-clips` | ❌ | `int` | `None` | Maximum number of clip segments (overrides test-mode) |
| `--max-duration`| ❌ | `float`| `None` | Maximum montage duration in seconds (overrides test-mode) |
| `--video-style` | ❌ | `str` | `none` | Color grading preset (see [Video Styles](#video-styles) below) |
| `--audio-overlay` | ❌ | `str` | `none` | Music-synced visualizer: `none`, `waveform` (lines), `bars` (frequency bars) |
| `--audio-overlay-opacity` | ❌ | `float` | `0.5` | Opacity of the audio visualizer (0.0–1.0) |
| `--audio-overlay-position` | ❌ | `str` | `bottom` | Vertical position of the visualizer: `top`, `center`, `bottom` |
| `--broll-interval` | ❌ | `float` | `13.5` | Target interval between B-roll clips in seconds |
| `--broll-variance` | ❌ | `float` | `1.5` | Allowed variance in B-roll intervals (± seconds) |
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
| `speed_ramp_enabled` | `true` | Enable speed ramping per intensity level |
| `high_intensity_speed` | `1.2` | Speed multiplier for high-intensity clips (>1 = fast) |
| `medium_intensity_speed` | `1.0` | Speed multiplier for medium-intensity clips |
| `low_intensity_speed` | `0.9` | Speed multiplier for low-intensity clips (<1 = slow-mo) |
| `clip_variety_enabled` | `true` | Randomize start offset within reused clips |
| `broll_interval_seconds` | `13.5` | Target interval between B-roll clips in seconds |
| `broll_interval_variance` | `1.5` | Allowed variance in B-roll intervals (± seconds) |
| `interpolation_method` | `blend` | Frame interpolation method for slow motion. Options: `none`, `blend`, `mci` |
| `accelerate_pacing` | `false` | Gradually decrease clip durations towards the end |
| `randomize_speed_ramps` | `false` | Apply random variance to speed ramps for a human touch |
| `abrupt_ending` | `false` | End sharply to create a cliffhanger effect |

> If `montage_config.yaml` is missing, defaults above are used automatically.

### Video Styles

Available presets for `--video-style`:

| Style | FFmpeg Filter | Effect |
|-------|---------------|--------|
| `none` | *(no filter)* | Original footage, no color grading |
| `bw` | `hue=s=0` | Black & white (full desaturation) |
| `vintage` | `curves=vintage,vignette` | Retro film look with darkened edges |
| `warm` | `colorchannelmixer` | Warm tones — boosted reds, reduced blues |
| `cool` | `colorchannelmixer` | Cool tones — boosted blues, reduced reds |
| `golden` | `colorchannelmixer` + `eq` + `vignette` | Nostalgic golden-hour amber — warm tones, soft desaturation, vignette |

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
| `make run` | Run `main.py` | Single-track montage via venv (requires `AUDIO` & `VIDEO_DIR`) |
| `make run-shorts` | Run `shorts_maker` | Generate YouTube Shorts (requires `AUDIO` & `VIDEO_DIR`) |
| `make full-pipeline` | Run `pipeline` | Full orchestration: mix + individual videos + shorts |
| `make test` | Run pytest | Executes test suite via venv |
| `make lint` | Run ruff check | Lint source and test files |
| `make format` | Run ruff format | Auto-format source and test files |
| `make check-types` | Run mypy | Type-check source and test files |
| `make clean` | Remove caches + outputs | Deletes `venv/`, `__pycache__/`, and `*.mp4` files |

### Makefile Variables

All variables below are **optional** and apply to `make run`, `make run-shorts`, and `make full-pipeline`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIO` | — | **(Required)** Path to audio file or directory of tracks |
| `VIDEO_DIR` | — | **(Required)** Directory of video clips to scan |
| `TEST_MODE` | `0` | Set to `1` to enable test mode (max 4 clips, 10s audio) |
| `MAX_CLIPS` | — | Override maximum number of clip segments |
| `MAX_DURATION` | — | Override maximum montage duration (seconds) |
| `VIDEO_STYLE` | — | Color grading preset: `none`, `bw`, `vintage`, `warm`, `cool`, `golden` |
| `AUDIO_OVERLAY` | — | Visualizer type: `waveform` (lines) or `bars` (frequency bars) |
| `AUDIO_OVERLAY_OPACITY` | — | Visualizer opacity (0.0–1.0) |
| `AUDIO_OVERLAY_POSITION` | — | Visualizer position: `top`, `center`, `bottom` |
| `SHORTS_COUNT` | `1` | Number of shorts to generate (pipeline/shorts targets) |
| `SHORTS_DURATION` | `60` | Duration per short in seconds |
| `BROLL_INTERVAL` | `13.5` | Target interval between B-roll clips in seconds |
| `BROLL_VARIANCE` | `1.5` | Allowed variance in B-roll intervals (± seconds) |
| `OUTPUT_DIR` | `output_pipeline` | Output directory (pipeline target only) |
| `SHARED_SCAN` | `0` | Set to `1` to share a single video scan across all tracks |

**Example — montage with waveform overlay:**

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ AUDIO_OVERLAY=waveform
```

**Example — full pipeline with bars visualizer at 70% opacity:**

```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ AUDIO_OVERLAY=bars AUDIO_OVERLAY_OPACITY=0.7
```

**Example — full pipeline with warm color grading:**

```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ VIDEO_STYLE=warm
```

**Example — B-roll every 20 seconds with ±3s variance:**

```bash
make full-pipeline AUDIO=./tracks/ VIDEO_DIR=./clips/ BROLL_INTERVAL=20 BROLL_VARIANCE=3
```

---

## mypy Configuration

Type checking is configured in `mypy.ini`:

```ini
[mypy]
ignore_missing_imports = True    # Don't error on untyped third-party libs
check_untyped_defs = True        # Check function bodies even without annotations
disallow_untyped_defs = False    # Allow functions without type annotations
```

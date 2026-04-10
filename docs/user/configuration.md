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
| `--audio-overlay-position` | ❌ | `str` | `right` | Horizontal position: `left`, `center`, `right` |
| `--audio-overlay-padding` | ❌ | `int` | `10` | Padding from screen edge in pixels |
| `--genre` | ❌ | `str` | `None` | Genre preset: `bachata`, `salsa`, `reggaeton`, `kizomba`, `merengue`, `pop` |
| `--output-json` | ❌ | `str` | `None` | Emit structured JSON output to a file or '-' for stdout |
| `--pacing-drift-zoom` | ❌ | flag | `False` | Slow 100→105% Ken Burns zoom drift on every segment |
| `--pacing-crop-tighten` | ❌ | flag | `False` | Zoom in over first 10s of each segment (caps at 105%) |
| `--pacing-saturation-pulse` | ❌ | flag | `False` | Brief saturation surge on each detected beat |
| `--pacing-micro-jitters` | ❌ | flag | `False` | Beat-synced 2px shake for rhythmic punch |
| `--pacing-light-leaks` | ❌ | flag | `False` | Warm amber colour flash on key beats (~200ms) |
| `--pacing-warm-wash` | ❌ | flag | `False` | Brief amber flash at transition boundaries |
| `--pacing-alternating-bokeh` | ❌ | flag | `False` | Subtle background blur on alternating segments |
| `--broll-interval` | ❌ | `float` | `13.5` | Target interval between B-roll clips in seconds |
| `--broll-variance` | ❌ | `float` | `1.5` | Allowed variance in B-roll intervals (± seconds) |
| `--explain` | ❌ | flag | `False` | Write a decision explainability log (`*_explain.md`) next to the output video |
| `--intro-effect` | ❌ | `str` | `none` | Visual effect on the first clip: `none`, `bloom`, `vignette_breathe` |
| `--intro-effect-duration` | ❌ | `float` | `1.5` | Duration of the intro effect in seconds |
| `--dry-run` | ❌ | flag | `False` | Run analysis and planning only — skip FFmpeg rendering |
| `--dry-run-output` | ❌ | `str` | `None` | Write the dry-run plan to a file instead of stdout |
| `--watch` | ❌ | flag | `False` | Watch input directories and config for changes and incrementally re-render |
| `--version` | ❌ | flag | — | Display version number and exit |

### Shorts CLI (`shorts_maker.py`)

| Argument | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `--smart-start` | ❌ | flag | `True` | Use audio hook detection for smart start selection |
| `--no-smart-start` | ❌ | flag | — | Disable smart start — all shorts start from beat 0 |

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
| `speed_ramp_organic` | `false` | Enable per-beat organic variable speed ramping (FEAT-036) |
| `speed_ramp_sensitivity` | `1.0` | Intensity→speed mapping strength (0.5=gentle, 1.0=normal, 2.0=aggressive) |
| `speed_ramp_curve` | `ease_in_out` | Smoothing curve type: `linear`, `ease_in`, `ease_out`, or `ease_in_out` |
| `speed_ramp_min` | `0.8` | Minimum speed multiplier for low-energy beats |
| `speed_ramp_max` | `1.3` | Maximum speed multiplier for high-energy beats |
| `clip_variety_enabled` | `true` | Randomize start offset within reused clips |
| `broll_interval_seconds` | `13.5` | Target interval between B-roll clips in seconds |
| `broll_interval_variance` | `1.5` | Allowed variance in B-roll intervals (± seconds) |
| `interpolation_method` | `blend` | Frame interpolation method for slow motion. Options: `none`, `blend`, `mci` |
| `accelerate_pacing` | `false` | Gradually decrease clip durations towards the end |
| `randomize_speed_ramps` | `false` | Apply random variance to speed ramps for a human touch |
| `abrupt_ending` | `false` | End sharply to create a cliffhanger effect |
| `audio_start_offset` | `0.0` | Start the montage from this point in the audio (seconds). Set automatically by smart-start hook detection. |
| `intro_effect` | `none` | Visual effect applied to the first segment only. Options: `none`, `bloom`, `vignette_breathe` |
| `intro_effect_duration` | `1.5` | Duration of the intro effect in seconds (0.5–3.0 recommended) |
| `audio_overlay_opacity` | `0.5` | Default opacity for the visualizer |
| `audio_overlay_position` | `right` | Default horizontal position (`left`, `center`, `right`) |
| `audio_overlay_padding` | `10` | Default padding from screen edge (pixels) |
| `pacing_drift_zoom` | `false` | Enable/disable drift zoom (Ken Burns) |
| `pacing_crop_tighten` | `false` | Enable/disable crop tightening |
| `pacing_saturation_pulse` | `false` | Enable/disable intensity-based saturation pulsing |
| `pacing_micro_jitters` | `false` | Enable/disable beat-synced micro-jitters |
| `pacing_light_leaks` | `false` | Enable/disable beat-synced light leaks |
| `pacing_warm_wash` | `false` | Enable/disable transition warm wash |
| `pacing_alternating_bokeh` | `false` | Enable/disable alternating segment blur |
| `dry_run` | `false` | If true, skip rendering and only output the plan |
| `genre` | `null` | Active genre preset name |
| `cold_open_wash_font_scale` | `0.06` | Opening wash text size as a fraction of video width (e.g. `0.06` = 6% of 1920px ≈ 115px). Capped at 90px internally. |
| `cold_open_wash_opacity` | `0.35` | Opacity of the wash text (0.0 = invisible, 1.0 = fully opaque). |
| `cold_open_wash_fade` | `0.8` | Max fade-in / fade-out duration in seconds. Capped at 1/3 of display time so short events don't spend all their time fading. |

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

### Organic Per-Beat Speed Ramping (FEAT-036)

When **disabled** (default), all clips use a scalar speed multiplier based on their intensity level (high/medium/low).

When **enabled** (`speed_ramp_organic: true`), playback speed **varies smoothly within each clip** on a beat-by-beat basis, driven by the audio's intensity curve. This creates an organic "breathing" effect where:

- **High-energy beats** → brief speed bursts (up to `speed_ramp_max`, default 1.3×)
- **Low-energy beats** → subtle slowdowns (down to `speed_ramp_min`, default 0.8×)
- **In-between** → smooth interpolation via `speed_ramp_curve`

**Parameters:**

| Parameter | Effect |
|-----------|--------|
| `speed_ramp_organic` | Enable/disable the feature |
| `speed_ramp_sensitivity` | Amplify or dampen the intensity→speed mapping. 0.5 = gentle, 1.0 = standard, 2.0 = aggressive |
| `speed_ramp_curve` | Smoothing function. `ease_in_out` = smooth at edges (cinematic), `linear` = direct mapping, `ease_in`/`ease_out` = asymmetric |
| `speed_ramp_min` | Slowest multiplier (e.g., 0.8 = 20% slow-mo on quietest beats) |
| `speed_ramp_max` | Fastest multiplier (e.g., 1.3 = 30% speed-up on loudest beats) |

**How to verify it's working:**

When enabled, watch for smooth speed changes within a single clip as the beat intensity rises and falls. The effect is most noticeable in sections with dynamic energy swings (e.g., buildup into a peak, or tail-off into breakdown). Compare the output with `speed_ramp_organic: false` to hear the difference—organic mode feels "alive," while scalar mode feels "steady."

**Configuration example:**

```yaml
pacing:
  speed_ramp_enabled: true          # Keep scalar fallback on
  speed_ramp_organic: true          # Enable per-beat variable speed
  speed_ramp_sensitivity: 1.2       # Slightly more pronounced
  speed_ramp_curve: ease_in_out     # Smooth cinematic effect
  speed_ramp_min: 0.75              # Down to 0.75× (more aggressive slowdown)
  speed_ramp_max: 1.4               # Up to 1.4× (faster bursts)
```

### Intro Effects

Applied to the first segment only (`--intro-effect`):

| Effect | FFmpeg Filter | Visual |
|--------|---------------|--------|
| `none` | *(no filter)* | Hard cut — original footage |
| `bloom` | `gblur` (animated sigma) | Dreamy gaussian reveal — starts fully blurred, clears over duration |
| `vignette_breathe` | `vignette` (animated angle) | Theatrical spotlight — opens from tight circle to full frame |

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
| `SMART_START` | *(on)* | Set to `0` to disable audio hook detection for shorts |
| `EXPLAIN` | `0` | Set to `1` to generate a decision explainability log alongside each output |
| `DRY_RUN` | `0` | Set to `1` to run analysis + planning only — no FFmpeg rendering |
| `DRY_RUN_OUTPUT` | — | Path to write the dry-run plan to a file instead of stdout |
| `WATCH` | `0` | Set to `1` to watch input directories and config for changes and incrementally re-render |
| `GENRE` | — | Genre preset: `bachata`, `salsa`, `reggaeton`, `kizomba`, `merengue`, `pop` |
| `OUTPUT_JSON` | — | Path for structured JSON output |
| `PACING_DRIFT_ZOOM` | `0` | Set to `1` to enable Ken Burns drift zoom |
| `PACING_CROP_TIGHTEN` | `0` | Set to `1` to enable crop tightening |
| `PACING_SATURATION_PULSE` | `0` | Set to `1` to enable saturation pulsing |
| `PACING_MICRO_JITTERS` | `0` | Set to `1` to enable micro-jitters |
| `PACING_LIGHT_LEAKS` | `0` | Set to `1` to enable light leaks |
| `PACING_WARM_WASH` | `0` | Set to `1` to enable warm wash |
| `PACING_ALTERNATING_BOKEH` | `0` | Set to `1` to enable alternating bokeh |

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

**Example — generate a decision explainability log:**

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ EXPLAIN=1
# → produces output_story.mp4 and output_story_explain.md
```

**Example — bloom intro effect on the first clip:**

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ INTRO_EFFECT=bloom
```

**Example — vignette breathe with 2-second duration:**

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ INTRO_EFFECT=vignette_breathe INTRO_EFFECT_DURATION=2.0
```

**Example — dry-run to preview the segment plan without rendering:**

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ DRY_RUN=1
```

**Example — dry-run with output saved to a file:**

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ DRY_RUN=1 DRY_RUN_OUTPUT=plan.txt
```

**Example — run in watch mode with test mode for fast iterations on configuration:**

```bash
make run AUDIO=song.wav VIDEO_DIR=./clips/ WATCH=1 TEST_MODE=1
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

# API Reference — Bachata Beat-Story Sync

> Module-by-module reference for all public classes and functions.

---

## `main.py` — Entry Point

### `parse_args() → argparse.Namespace`
Parses CLI arguments.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--audio` | `str` | Yes | — | Path to input `.wav`/`.mp3` audio |
| `--video-dir` | `str` | Yes | — | Directory containing video clips |
| `--broll-dir` | `str` | No | `video-dir/broll` | Optional directory for B-roll clips |
| `--output` | `str` | No | `output_story.mp4` | Output video path |
| `--export-report` | `str` | No | `None` | Excel report output path |
| `--test-mode` | flag | No | `False` | Run in test mode (max 4 clips, 10s of music) |
| `--max-clips` | `int` | No | `None` | Maximum number of clip segments |
| `--max-duration`| `float`| No | `None` | Maximum montage duration in seconds |
| `--explain` | flag | No | `False` | Write a decision explainability log (`*_explain.md`) |
| `--version` | flag | No | — | Show version (`0.1.0`) |

### `main() → None`
Runs the full pipeline: audio analysis → video scanning → montage generation → optional report.

---

## `src.application.batch_bridge` — Batch Handoff

### `load_batch(batch_path: str | os.PathLike[str]) → dict`
Load a batch JSON file from disk.

### `save_batch(batch_path: str | os.PathLike[str], batch: dict) → None`
Write a batch JSON file to disk.

### `plan_song_from_batch(batch_path: str | os.PathLike[str], song_id: str, video_dir: str, config_overrides: dict | None = None, engine: BachataSyncEngine | None = None) → list[dict]`
Plan a montage for one song inside a batch by resolving the stored audio path and scanning the clip directory.

### `render_song_from_batch(batch_path: str | os.PathLike[str], song_id: str, video_dir: str, output_path: str, config_overrides: dict | None = None, engine: BachataSyncEngine | None = None) → dict`
Render one song from a batch and write the updated video state back to the batch JSON.

**Stops early if:**
- the song has no audio asset path
- the clip directory is missing
- the video render cannot complete

---

## `mcp_server.py` — MCP Tools

### `load_batch(batch_path: str) → dict`
Load a batch JSON file and cache it in session state.

### `save_batch(batch_path: str, batch: dict) → dict`
Save a batch JSON file and cache it in session state.

### `plan_batch_song(batch_path: str, song_id: str, video_dir: str, config_overrides: dict | None = None) → list[dict]`
Plan one song from a batch through the MCP server.

### `render_batch_song(batch_path: str, song_id: str, video_dir: str, output_path: str, config_overrides: dict | None = None) → dict`
Render one song from a batch through the MCP server and update the in-memory batch cache.

---

## `src.core.app` — Engine

### `BachataSyncEngine`

The central orchestrator for the pipeline.

#### `__init__() → None`
Initializes `VideoAnalyzer` and `MontageGenerator` instances.

#### `scan_video_library(directory: str, observer: Optional[ProgressObserver] = None) → List[VideoAnalysisResult]`
Scans a directory recursively for supported video files with progress reporting.

| Parameter | Type | Description |
|-----------|------|-------------|
| `directory` | `str` | Root directory to scan |
| `observer` | `Optional[ProgressObserver]` | Callback for progress updates |

**Returns:** List of `VideoAnalysisResult` for each successfully analyzed video.

**Raises:** `FileNotFoundError` if directory doesn't exist.

#### `generate_story(audio_data: AudioAnalysisResult, video_clips: List[VideoAnalysisResult], output_path: str, broll_clips: Optional[List[VideoAnalysisResult]] = None, audio_path: Optional[str] = None, observer: Optional[ProgressObserver] = None, pacing: Optional[PacingConfig] = None) → str`
Delegates to `MontageGenerator.generate()`.

**Returns:** Path to the generated output video.

---

## `src.core.audio_analyzer` — Audio Analysis

### `AudioAnalysisInput(BaseModel)`

Pydantic input validation model.

| Field | Type | Validation |
|-------|------|------------|
| `file_path` | `str` | Must exist, extension in `{'.wav', '.mp3'}`, no path traversal |

### `AudioAnalyzer`

#### `analyze(input_data: AudioAnalysisInput) → AudioAnalysisResult`
Analyzes an audio file using Librosa to extract:
- **BPM** via `librosa.beat.beat_track()`
- **Onset times** via `librosa.onset.onset_detect()`
- **Duration** via `librosa.get_duration()`

**Raises:** `RuntimeError` if analysis fails.

---

## `src.core.video_analyzer` — Video Analysis

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_VIDEO_FRAMES` | `100,000` | DoS prevention (≈1hr at 30fps) |
| `MAX_VIDEO_DURATION_SECONDS` | `3,600` | Max 1 hour videos |
| `SUPPORTED_VIDEO_EXTENSIONS` | `{'.mp4', '.mov', '.avi', '.mkv'}` | Extension allowlist |
| `BLUR_KERNEL_SIZE` | `(21, 21)` | Gaussian blur for frame preprocessing |
| `NORMALIZATION_FACTOR` | `100` | Intensity score normalization divisor |

### `VideoAnalysisInput(BaseModel)`

| Field | Type | Validation |
|-------|------|------------|
| `file_path` | `str` | Must exist, extension in supported set, no path traversal |

### `VideoAnalyzer`

#### `analyze(input_data: VideoAnalysisInput) → VideoAnalysisResult`
Analyzes a video file using OpenCV:
1. Validates frame count and duration against DoS limits
2. Extracts a thumbnail from the middle frame
3. Calculates motion intensity via frame-by-frame delta analysis

**Raises:** `IOError` if video can't be opened. `ValueError` if limits exceeded.

---

## `src.core.montage` — Montage Generation

### `MontageGenerator`

#### `generate(audio_data: AudioAnalysisResult, video_clips: List[VideoAnalysisResult], output_path: str, audio_path: Optional[str] = None, observer: Optional[ProgressObserver] = None, pacing: Optional[PacingConfig] = None, broll_clips: Optional[List[VideoAnalysisResult]] = None) → str`
Builds a video montage:
1. Calculates required segment sequences mapping to musical beats and intensity
2. Randomises start offsets and speeds up or interpolates slow-motion clips (`minterpolate`)
3. Intersperses B-roll segments at configured intervals
4. Applies crop scale and resizing to normalise all segments
5. Concatenates and overlays audio track
6. Exports as H.264/AAC MP4

**Raises:** `ValueError` if no video clips. `FileNotFoundError` if audio missing. `RuntimeError` if no valid segments generated.

**Output:** 720p, 24fps, `libx264` codec, `aac` audio, `ultrafast` preset.

When `PacingConfig.explain` is `True`, writes a `*_explain.md` Markdown file next to the output video documenting every clip selection decision.

---

## `src.core.models` — Data Transfer Objects

### `AudioAnalysisResult(BaseModel)`
| Field | Type | Description |
|-------|------|-------------|
| `filename` | `str` | Audio file basename |
| `bpm` | `float` | Beats per minute |
| `duration` | `float` | Duration in seconds |
| `peaks` | `List[float]` | Timestamps of high intensity peaks |
| `sections` | `List[MusicalSection]` | Detected musical sections with labels and timestamps |
| `beat_times` | `List[float]` | Precise timestamps of each detected beat |
| `intensity_curve` | `List[float]` | Normalised RMS energy (0.0–1.0) at each beat position |

### `VideoAnalysisResult(BaseModel)`
| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Absolute path to video file |
| `intensity_score` | `float` | Visual motion intensity (0.0–1.0) |
| `duration` | `float` | Duration in seconds |
| `is_vertical` | `bool` | Whether the video is in vertical (9:16) format |
| `thumbnail_data` | `Optional[bytes]` | PNG thumbnail binary data |
| `scene_changes` | `List[float]` | Timestamps of detected visual cuts |
| `opening_intensity` | `float` | Visual motion intensity in the first 2 seconds |

### `PacingConfig(BaseModel)`
Controls montage clip pacing, effects, and transitions.

| Field | Default | Description |
|-------|---------|-------------|
| `min_clip_seconds` | `1.5` | Hard floor for clip duration |
| `high_intensity_seconds` | `2.5` | Target duration for high-intensity clips |
| `speed_ramp_enabled` | `True` | Enable intensity-based speed ramping |
| `video_style` | `'none'` | Color grading style (`bw`, `vintage`, etc.) |
| `audio_overlay` | `'none'` | Visualizer pattern (`waveform`, `bars`) |
| `pacing_drift_zoom` | `False` | Enable Ken Burns drift zoom |
| `intro_effect` | `'none'` | Visual effect on the first segment |
| `dry_run` | `False` | Skip rendering, output plan only |
| `genre` | `None` | Active genre preset |

---

## `src.core.interfaces` — Protocols

### `ProgressObserver(Protocol)`

#### `on_progress(current: int, total: int, message: str = "") → None`
Called during long-running operations to report progress.

---

## `src.core.validation` — Input Security

### `validate_file_path(path: str, allowed_extensions: Iterable[str]) → str`
Validates a file path for:
1. **Path traversal** — rejects paths containing `..`
2. **Existence** — confirms file exists on disk
3. **Extension allowlist** — checks against provided set

**Raises:** `ValueError` on any validation failure.

---

## `src.services.reporting` — Excel Reports

### `ExcelReportGenerator`

#### `generate_report(audio_data: AudioAnalysisResult, video_data: List[VideoAnalysisResult], output_path: str) → str`
Creates a multi-sheet Excel workbook:
- **Analysis Summary** — Audio metadata in key-value format
- **Video Library** — Table with paths, durations, intensity scores, thumbnails
- **Visualizations** — Bar chart of intensity distribution

### `ReportFormatter`
Handles Excel styling: bold headers, centered alignment, auto-column-widths (capped at 50 chars), and 3-color conditional formatting (red → yellow → green).

### `ChartBuilder`
Creates `BarChart` objects for intensity score visualization.

### `ThumbnailEmbedder`
Embeds PNG thumbnail images into worksheet cells with auto-sized row heights.

---

## `src.ui.console` — Console UI

### `RichProgressObserver`
Implements `ProgressObserver` using the Rich library with a spinner, text description, progress bar, and percentage display.

#### `on_progress(current: int, total: int, message: str = "") → None`
Auto-starts on first call, updates progress bar, and stops when `current >= total`.

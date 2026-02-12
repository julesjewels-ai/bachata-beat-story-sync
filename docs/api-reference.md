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
| `--output` | `str` | No | `output_story.mp4` | Output video path |
| `--export-report` | `str` | No | `None` | Excel report output path |
| `--version` | flag | No | — | Show version (`0.1.0`) |

### `main() → None`
Runs the full pipeline: audio analysis → video scanning → montage generation → optional report.

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

#### `generate_story(audio_data: AudioAnalysisResult, video_clips: List[VideoAnalysisResult], output_path: str) → str`
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

#### `generate(audio_result: AudioAnalysisResult, video_results: List[VideoAnalysisResult], output_path: str) → str`
Builds a video montage:
1. Calculates bar duration (4 beats) from BPM
2. Iterates through audio duration, selecting clips for each bar
3. Trims clips to bar duration from random start points
4. Resizes all clips to 720p height
5. Concatenates and overlays audio
6. Exports as H.264/AAC MP4

**Raises:** `ValueError` if no video clips. `FileNotFoundError` if audio missing. `RuntimeError` if no valid segments generated.

**Output:** 720p, 24fps, `libx264` codec, `aac` audio, `ultrafast` preset.

---

## `src.core.models` — Data Transfer Objects

### `AudioAnalysisResult(BaseModel)`

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `str` | Absolute path to audio file |
| `filename` | `str` | Audio file basename |
| `bpm` | `float` | Beats per minute |
| `duration` | `float` | Duration in seconds |
| `peaks` | `List[float]` | Timestamps of intensity peaks |
| `sections` | `List[str]` | Musical sections (currently placeholder) |

### `VideoAnalysisResult(BaseModel)`

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Absolute path to video file |
| `intensity_score` | `float` | Visual motion intensity (0.0–1.0) |
| `duration` | `float` | Duration in seconds |
| `thumbnail_data` | `Optional[bytes]` | PNG thumbnail binary data |

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

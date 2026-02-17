# Feature Backlog — Bachata Beat-Story Sync

> **🧹 Reset (2026-02-14):** Codebase stripped back to a clean, minimal foundation. All features reset to `PROPOSED` for re-implementation on solid ground. The core analysis engine (audio + video) remains stable and fully tested.

---

## FEAT-001: Variable Clip Duration Based on Intensity

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🔴 High                              |
| **Effort**  | Medium                               |
| **Impact**  | High — biggest single improvement    |

### Description
Vary clip segment duration based on audio intensity using time-based targets (not raw beat counts). Pacing is fully configurable via `montage_config.yaml`.

- **High intensity** (≥0.65) → ~2.5s clips (energetic but watchable)
- **Medium intensity** (0.35–0.65) → ~4.0s clips (standard pacing)
- **Low intensity** (<0.35) → ~6.0s clips (breathing room)
- **Minimum floor** → 1.5s (no flicker cuts)

All durations snap to beat boundaries so cuts feel musical.

### Architecture
Uses a memory-safe pattern: FFmpeg subprocess calls for segment extraction and concatenation. Pacing parameters loaded from `montage_config.yaml` (falls back to defaults if missing).

---

## FEAT-002: Speed Ramping (Slow-Mo / Fast-Forward)

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🟡 Medium                            |
| **Effort**  | Medium                               |
| **Impact**  | High — cinematic and professional    |

### Description
Apply speed effects to clips based on their matched audio intensity.

---

## FEAT-003: Musical Section Awareness

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🟡 Medium                            |
| **Effort**  | Medium (Approach C — intensity heuristic) |
| **Impact**  | Medium — improves narrative structure|

### Description
Detect musical sections (intro, verse, chorus, breakdown, outro) from audio analysis.

---

## FEAT-004: Beat-Snap Transitions

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🟢 Low                               |
| **Effort**  | Low–Medium (Approach C — hybrid concat + selective xfade) |
| **Impact**  | Medium — polish and professionalism  |

### Description
Align transition effects precisely to beat timestamps instead of hard-cutting.

---

## FEAT-005: Test Mode (Quick Iteration)

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🟡 Medium                            |
| **Effort**  | Low                                  |
| **Impact**  | High — enables fast dev iteration    |

### Description
Caps montage generation to a maximum of 4 clip segments and 10 seconds of music. Activated via `--test-mode` CLI flag or by setting `max_clips` / `max_duration_seconds` in `montage_config.yaml`.

---

## FEAT-006: Clip Variety & Start Offset

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🔴 High                              |
| **Effort**  | Low–Medium                           |
| **Impact**  | High — eliminates repetitive feel    |

### Description
When a clip is reused across multiple segments, the current code always extracts from `start_time=0.0`, making repeated clips look identical. This feature should:

- **Randomise or offset the start position** within each clip so repeated clips show different parts of the footage
- Optionally **match clip intensity to audio intensity** instead of pure round-robin selection
- Ensure the selected start offset never exceeds `clip.duration - segment_duration`

---

## FEAT-007: Multi-Track Folder Input (Mix Creation)

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `PROPOSED`                           |
| **Priority**| 🟡 Medium                            |
| **Effort**  | Medium                               |
| **Impact**  | High — enables full DJ-style mixes   |

### Description
Instead of supplying a single audio file, allow the user to specify a **folder** containing multiple audio tracks. The system should:

- Accept a folder path (via CLI arg or config) as an alternative to a single audio file
- **Discover** all supported audio files in the folder (e.g. `.mp3`, `.wav`, `.flac`, `.aac`)
- **Concatenate / join** the tracks in alphanumeric filename order into a single continuous mix
- Use the resulting combined audio as the input for beat analysis and montage generation
- Optionally support a **tracklist manifest** (e.g. `tracklist.txt` or `tracklist.yaml`) to control order, per-track trim points, and crossfade durations between tracks
- Apply a configurable **crossfade** between consecutive tracks (default ~2s) so the mix sounds seamless
- Store the joined mix as a cached intermediate file to avoid re-joining on subsequent runs

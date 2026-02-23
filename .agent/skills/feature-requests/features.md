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
| **Status**  | `IMPLEMENTED`                        |
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

---

## FEAT-008: Visual Intensity Matching

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `PROPOSED`                           |
| **Priority**| 🔴 High                              |
| **Effort**  | Medium                               |
| **Impact**  | High — makes the montage feel cohesive and responsive|

### Description
Currently, video clips are selected sequentially (round-robin style), meaning high-energy music can easily pair with low-energy clips, and vice versa. This feature will update the clip selection logic so that the visual intensity of the chosen clip matches the current audio intensity classification.

### Implementation Details
- In `MontageGenerator.build_segment_plan`, when deciding which clip to use for a particular musical section or beat segment:
  - Check the current audio `intensity_level` ('high', 'medium', 'low', derived from `intensity >= high_intensity_threshold`, etc.).
  - Distribute the available `video_clips` into buckets or pools based on their visual `intensity_score` (e.g., > 0.65 for high, < 0.35 for low).
  - Select clips from the pool that matches the current audio intensity, rather than uniformly iterating over `sorted_clips`.
- To prevent exhausting clips in a pool or excessive repetition:
  - Maintain a separate round-robin tracking index per intensity pool, rather than a single global `clip_idx`.
  - Implement **fallback logic**: If a pool is empty (e.g., no 'high' intensity clips exist), fallback to the next closest pool (e.g., 'medium') to prevent crashes and dead loops.

### Concerns & Considerations
- **Pool Starvation/Repetition Indexing**: If a user provides mostly low-energy clips, but the song is predominantly high-energy, the few high-energy clips will be repeated constantly. The system needs to intelligently balance matching intensity vs. maintaining `clip_variety_enabled` (FEAT-006). If a pool is too small, the system should deliberately borrow from adjacent pools to keep the visual feed fresh.
- **Score Calibration**: The threshold values for 'high', 'medium', and 'low' (e.g., `0.65` and `0.35` in `PacingConfig`) need to be reliable for both audio RMS and video motion/brightness analysis. If the video analyzer generally scores too low, the 'high' pool might remain permanently bare. We may need to investigate categorizing video clips using dynamic percentiles (e.g., the top 30% most intense clips are "high") rather than strictly hardcoded `<0.35` and `>0.65` thresholds.

---

## FEAT-009: Specific Clip Prefix Ordering

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `PROPOSED`                           |
| **Priority**| 🔴 High                              |
| **Effort**  | Low                                  |
| **Impact**  | High — allows editorial control over intos |

### Description
Allows the user to force specific clips to appear at the very beginning of the montage by prefixing their filenames with a number and an underscore (e.g., `1_intro.mp4`, `2_lead.mp4`).

### Implementation Details
- The system will detect clips with a numbering prefix in their filename.
- These clips will be sorted numerically (e.g. `1_` before `2_`) and used in that exact order for the first available beat segments.
- After all prefix forced clips are exhausted, the system returns to its normal intensity-driven, round-robin selection logic for the remainder of the montage.
- Because the forced clips still map directly to the calculated beat segments, they will inherently "match the song" (pacing, cuts, and transitions will trigger on the beats).

---

## FEAT-010: Structural Segmentation

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `PLANNED`                            |
| **Priority**| 🔴 High                              |
| **Effort**  | Medium                               |
| **Impact**  | High — enables musically meaningful section cuts |

### Description
Add harmonic structure detection to `AudioAnalyzer` to complement the existing intensity-based section detection. Uses Chroma features and Agglomerative Clustering (with temporal contiguity constraints) to identify structurally distinct regions of a track (e.g. verse vs. chorus boundaries), even when both sections are equally loud.

### Implementation Details

#### `segment_structure(y, sr, beat_frames, n_segments=4)` — new function in `audio_analyzer.py`
- Use `librosa.feature.chroma_stft` (not `chroma_cqt`) for speed and memory efficiency.
- Synchronize chroma features to beat intervals via `librosa.util.sync`.
- Build a temporal `kneighbors_graph` connectivity matrix using `sklearn.neighbors.kneighbors_graph(X, n_neighbors=3, mode='connectivity')` so that only temporally adjacent beats can be grouped — this prevents the "every chord change = boundary" bug from PR #134.
- Pass `connectivity` to `sklearn.cluster.AgglomerativeClustering(n_clusters=n_segments, linkage='ward', connectivity=conn)`.
- **Explicit memory cleanup**: after clustering, `del chroma, chroma_sync, X` and call `gc.collect()`.
- Return `[]` on any exception, logging a warning with the error reason.

#### `detect_sections(...)` — modified in `audio_analyzer.py`
- Add `structural_boundaries: Optional[list[int]] = None` parameter.
- When merging with intensity change-points, deduplicate boundaries within **4 beats** of each other before the union to avoid near-coincident double-cuts.
- Raise the short-section merge filter from `< 3` beats to `< 8` beats (one musical bar at ~120 BPM).

#### `AudioAnalyzer.analyze()` — modified
- Call `segment_structure(y=y, sr=sr, beat_frames=beat_frames)` and pass the result as `structural_boundaries` to `detect_sections`.
- Call site placed **before** the `del` block.

### Concerns & Considerations
- **`n_segments` is configurable** (default 4). Short tracks (<90s) should use a lower value — consider dynamically scaling it by `int(duration / 45)`.
- **scikit-learn dependency**: `scikit-learn>=1.3.0` must be added to `requirements.txt`. It's a substantial install (~30 MB); consider a lazy import with a clear warning if not installed.
- **CPU spike**: `AgglomerativeClustering` with Ward linkage is `O(n² log n)`. For typical 3–5 min tracks at ~120 BPM (~360–600 beat frames), this is fast enough, but it should be confirmed on longer DJ mixes (FEAT-007).

# Feature Backlog — Bachata Beat-Story Sync

> **🧹 Reset (2026-02-14):** Codebase stripped back to a clean, minimal foundation. All features reset to `PROPOSED` for re-implementation on solid ground. The core analysis engine (audio + video) remains stable and fully tested.
>
> **📋 Review (2026-02-23):** Backlog critically reviewed for end-user value. FEAT-010 (Structural Segmentation) removed — marginal visual impact vs. high complexity/dependency cost. Remaining features re-ordered by dependency and value.

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

## FEAT-008: Specific Clip Prefix Ordering

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `VERIFIED`                           |
| **Priority**| 🔴 High                              |
| **Effort**  | Low                                  |
| **Impact**  | High — gives editorial control over the most important moment (the intro) |

### Why this matters
The intro is the single most critical moment in any social video — viewers decide within 1–2 seconds whether to keep watching. Currently, the first clip is chosen by round-robin based on intensity sort order, giving the user **zero control** over what appears first.

### Description
Allows the user to force specific clips to appear at the very beginning of the montage by prefixing their filenames with a number and an underscore (e.g., `1_intro.mp4`, `2_lead.mp4`).

### Implementation Details
- Detect clips with a numbering prefix (`^\d+_`) in their filename.
- Sort these numerically (`1_` before `2_`) and use them in that exact order for the first available beat segments.
- After all prefix-forced clips are exhausted, return to the normal selection logic for the remainder.
- Forced clips still map to calculated beat segments, so pacing, cuts, and transitions stay musical.

### Scope
- **In scope:** Prefix detection, forced ordering, graceful fallback.
- **Out of scope:** Per-clip configuration files, drag-and-drop reordering.

---

## FEAT-009: Visual Intensity Matching

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `VERIFIED`                           |
| **Priority**| 🔴 High                              |
| **Effort**  | Medium                               |
| **Impact**  | High — the most noticeable remaining gap in montage quality |

### Why this matters
Right now, clip *pacing* responds to the music (fast cuts for high-energy sections) but the *visual content* does not. A calm, slow clip can appear during an explosive chorus, and an action-packed clip can appear during a gentle intro. This mismatch is the most obvious "something feels off" moment for an end viewer.

### Description
Replace round-robin clip selection with intensity-matched pools so that high-energy music pairs with high-motion clips, and low-energy sections get calmer footage.

### Implementation Details

#### Stage A — Pool-based selection (core value)
- Bucket available clips into `high` / `medium` / `low` pools based on their `intensity_score` using the same thresholds as audio (`PacingConfig.high_intensity_threshold`, `low_intensity_threshold`).
- When selecting a clip for a segment, draw from the matching pool.
- Maintain a per-pool round-robin index for variety.
- **Fallback:** If a pool is empty or exhausted, borrow from the nearest adjacent pool (high → medium → low), not crash.
- Must integrate with FEAT-009: prefix-forced clips are used first regardless of pool.

#### Stage B — Dynamic thresholds (enhancement, only if pool starvation is a real problem)
- If a user provides mostly low-motion clips, the `high` pool will be permanently empty.
- Replace hardcoded 0.35/0.65 thresholds with **percentile-based bucketing** (top 30% = high, bottom 30% = low) so pools are always roughly balanced.
- Only implement this if Stage A reveals pool starvation in real-world use.

### Concerns & Considerations
- **Pool starvation** is the main risk — mitigated by adjacent-pool fallback in Stage A and percentile bucketing in Stage B.
- **Score calibration**: Video intensity scores (motion-based) and audio intensity scores (RMS-based) use different scales. The thresholds may need tuning.
- The existing `test_round_robin_clip_assignment` test will intentionally break and must be replaced with pool-based assertions.

### Scope
- **In scope:** Pool bucketing, per-pool round-robin, fallback logic, FEAT-009 integration.
- **Out of scope:** AI-based semantic matching (e.g., "this clip shows spinning"), multi-dimensional clip scoring.

---

## FEAT-010: Smooth Slow Motion Interpolation

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🟡 Medium                            |
| **Effort**  | Low–Medium                           |
| **Impact**  | High — makes slow-motion professional and smooth |

### Why this matters
Currently, when clips are slowed down (speed ramping, `seg.speed_factor < 1.0`), the video stutters because standard timestamp manipulation (`setpts`) simply stretches the existing frames further apart in time. This lowers the effective framerate (e.g., a 30fps clip slowed to 50% plays like a choppy 15fps clip). To fix this and maintain a fluid, cinematic look, the video needs new frames generated between the existing ones.

### Description
Implement frame interpolation (optical flow or frame blending) during the FFmpeg segment extraction phase whenever a clip's speed factor is reduced below 1.0.

### Implementation Details
- During segment extraction in `montage.py`, detect if `seg.speed_factor < 1.0`.
- If true, append an interpolation filter to the video filter (`-vf`) chain in the FFmpeg command.
- **Option A (High Quality, Slower):** Motion-compensated interpolation using FFmpeg's `minterpolate=mi_mode=mci` (optical flow).
- **Option B (Faster, Acceptable):** Frame blending using `minterpolate=mi_mode=blend` or the `framerate` filter.
- Expose the interpolation method as a configurable option in `PacingConfig`, so users can opt for faster renders (blending) or higher cinematic quality (mci) based on their machine's capabilities.

### Scope
- **In scope:** Adding interpolation filters to the FFmpeg filter chain for slowed clips, configuration for interpolation method.
- **Out of scope:** Applying interpolation to clips that aren't speed-ramped (e.g., regular 1.0x playback), or integrating third-party AI upscaling/interpolation ML models.

---

## FEAT-011: Intermittent B-Roll Insertion

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `VERIFIED`                           |
| **Priority**| 🟢 Low                               |
| **Effort**  | Low                                  |
| **Impact**  | Medium — adds visual storytelling variety |

### Why this matters
To prevent visual fatigue, especially during longer montages, inserting B-Roll clips breaks up the constant action and gives the viewer's eyes a chance to rest or absorb the atmosphere, improving the overall pacing of the video.

### Description
Automatically interleave B-roll clips into the montage roughly every 12 to 15 seconds to provide visual variety, using a dedicated folder for the B-roll footage.

### Implementation Details
- B-roll intervals are randomized between 12 and 15 seconds using `broll_interval_seconds` and `broll_interval_variance` in `PacingConfig`.
- `main.py` accepts an optional `--broll-dir` argument, falling back to a nested `broll` directory inside the main video directory.
- `app.py` excludes the B-roll directory from the general video library scan to prevent duplication.

### Scope
- **In scope:** Interleaving B-roll clips at randomized intervals, separating B-roll clips into a separate scanning path.
- **Out of scope:** Semantic B-roll awareness (matching B-roll content to lyrics or emotion).

---

## FEAT-012: Video Style Filters (Color Grading)

| Field        | Value                                            |
|--------------|--------------------------------------------------|
| **Status**   | `IMPLEMENTED`                                    |
| **Priority** | 🟡 Medium                                         |
| **Effort**   | Low                                              |
| **Impact**   | Medium — adds mood and brand consistency          |

### Why this matters
Raw footage from different cameras and lighting conditions looks inconsistent. A single configurable color grade creates a consistent "mood" across all clips in the montage — the difference between amateur-looking footage and a cohesive production.

### Description
Apply a named color-grading filter to every segment during FFmpeg extraction. The style is set once via `PacingConfig` (or `montage_config.yaml`) and applied uniformly.

### Implementation Details
- Add a `video_style: str` field to `PacingConfig` (default `"none"`).
  - Supported values: `"none"`, `"bw"` (black & white), `"vintage"` (warm + faded), `"warm"`, `"cool"`.
- Inside `_extract_segments()` in `montage.py`, append the matching FFmpeg `-vf` filter to `vf_parts` based on `config.video_style`:
  - `"bw"` → `hue=s=0`
  - `"vintage"` → `curves=vintage,vignette`
  - `"warm"` → `colortemperature=warmth=200` *(or `colorchannelmixer`)*
  - `"cool"` → `colortemperature=warmth=-200`
- Add `--video-style` CLI argument to `main.py` and `shorts_maker.py`.

### Risk Assessment
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Filter names differ between FFmpeg versions | Low | Use widely-supported primitives (`hue`, `curves`, `colorchannelmixer`) |
| Slight re-encode quality loss | Low | CRF 23 already in use; negligible |
| Performance overhead | Low | Filters add ~5–10% to extraction time — acceptable |
| `colortemperature` filter not available | Medium | Fall back to `colorchannelmixer` equivalents |

### Scope
- **In scope:** `bw`, `vintage`, `warm`, `cool`, and `none` styles; `montage_config.yaml` and CLI support.
- **Out of scope:** AI-powered scene-specific grading, per-segment style variation, LUT (Look-Up Table) file support.

---

## FEAT-013: Music-Synced Waveform Overlay

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `IMPLEMENTED`                                        |
| **Priority** | 🟢 Low                                                |
| **Effort**   | Medium                                               |
| **Impact**   | Medium — eye-catching visual element for social video |

### Why this matters
Social media audiences are trained to expect visual reinforcement of the audio track. A subtle, music-synced waveform or equalizer bar at the bottom of the frame signals energy and production quality, encouraging viewers to keep watching with the sound on.

### Description
Render a live audio-reactive waveform overlay onto the final output video using FFmpeg's `showwaves` filter. The overlay reacts in real time to the music track and sits at the bottom of the frame.

### Implementation Details
- Add an `audio_overlay: str` field to `PacingConfig` (default `"none"`).
  - Supported values: `"none"`, `"waveform"` (line waveform), `"bars"` (frequency bars — requires `showfreqs` or `showcqt`).
- Modify `_overlay_audio()` in `montage.py`:
  - When `config.audio_overlay != "none"`, switch from `-c:v copy` to a `-filter_complex` chain:
    - `"waveform"` → `[1:a]showwaves=s={WIDTH}x280:mode=line:colors=White@0.5[wave];[0:v][wave]overlay=0:H-h[outv]`
    - `"bars"` → `[1:a]showcqt=s={WIDTH}x280[bars];[0:v][bars]overlay=0:H-h[outv]`
  - Map `[outv]` and re-encode with `libx264` + `aac` (cannot stream-copy when using filter_complex on video).
- WIDTH is inferred from `config.is_shorts` → 1080 or 1920.
- Add `--audio-overlay` CLI argument to `main.py` and `shorts_maker.py`.

### Risk Assessment
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Re-encoding required (cannot stream-copy with filter_complex) | **High (guaranteed)** | Budget for ~2–5 min extra processing per video; document clearly |
| `showcqt` not available on all FFmpeg builds | Medium | Default to `showwaves`; gate `bars` on FFmpeg capability check |
| Waveform too bright / distracting | Medium | Expose `audio_overlay_opacity` param (default 0.5); use `format=rgb24,colorchannelmixer` |
| No audio → overlay is flat / invisible | Low | Guard: only apply overlay if `audio_path` is provided |

### Scope
- **In scope:** `waveform` and `bars` overlays; opacity control; `montage_config.yaml` and CLI support.
- **Out of scope:** Custom overlay position, colour, or font; per-beat sticker animations; Lottie/After Effects-style motion graphics.

---

## FEAT-014: Full Pipeline Orchestrator (Core)

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PLANNED`                                            |
| **Priority** | 🔴 High                                              |
| **Effort**   | Low–Medium                                           |
| **Impact**   | High — single command to generate mix + separate tracks |

### Description
Create a new entry point (`src/pipeline.py`) that orchestrates the existing application classes. It should take a directory of audio tracks and:
1. **Discover** individual audio files in the `--audio` folder and sort them.
2. **Mix** them into a combined WAV via `AudioMixer` (saves `_mixed_audio.wav` as cache).
3. **Replicate B-roll logic** from `main.py` (auto-detect `broll/` inside `--video-dir` and exclude it from the main scan).
4. **Generate mix video** using the combined audio → `<output-dir>/mix.mp4`
5. **Loop over each track**:
   - Analyze the track's audio independently.
   - Re-scan the video library (to randomize clip order).
   - Strip `thumbnail_data` from clips before montage (memory management).
   - Generate a music video → `<output-dir>/track_01_<name>.mp4`

**CLI arguments required:**
- `--audio` (required): Folder of audio tracks
- `--video-dir` (required): Folder of video clips
- `--broll-dir`: Optional custom B-roll path
- `--output-dir`: defaults to `output_pipeline`
- `--skip-mix`: Flag to skip the combined mix video
- All visual args: `--video-style`, `--audio-overlay`, `--audio-overlay-opacity`, `--audio-overlay-position`, `--test-mode`

Includes adding a `make full-pipeline` target to `Makefile`.

---

## FEAT-015: Pipeline Shorts Integration

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PLANNED`                                            |
| **Priority** | 🟡 Medium                                            |
| **Effort**   | Low                                                  |
| **Impact**   | High — completes the content generation package        |

### Description
Extend the `full-pipeline` orchestrator to also generate YouTube Shorts for each individual track. After the main horizontal video is generated for a track, the pipeline should instantly run the equivalent of `shorts_maker.py` logic N times using the track's audio.

**CLI arguments required:**
- `--shorts-count` (default 1, 0 disables shorts)
- `--shorts-duration` (default 60, supports ranges like 10-15)

**Implementation edge cases:**
- Shorts should **not** use B-roll clips (matches `shorts_maker.py` behaviour).
- Shorts must inherit all visual pacing configs (video style, overlay settings) from the parent CLI args.
- Output path structure: `<output-dir>/shorts/track_01/short_001.mp4`

---

## FEAT-016: Shared Scan Optimization

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PLANNED`                                            |
| **Priority** | 🟡 Medium                                            |
| **Effort**   | Low                                                  |
| **Impact**   | Medium — significantly improves processing speed       |

### Description
Provide a `--shared-scan` flag for the pipeline to heavily optimize duration when processing many tracks.

- **Default (Independent Scan):** For every track (and the mix), the video library is re-scanned. This ensures that the "used clips" history is fresh, guaranteeing maximum visual variety for each video, but costs ~1 minute of CPU time per track.
- **Shared Scan:** When `--shared-scan` is set, the library is only scanned *once* at the beginning and the list of `VideoAnalysisResult` objects is passed to all tracks. This skips the scanning overhead at the cost of less variety (if a clip is used in track 1, it might have the same offset in track 2).

**Implementation details:**
- Must ensure that any mutation of the clip list (like `thumbnail_data=None`) does not break the shared state across iterations. Deep-copy the clip list before mutating.

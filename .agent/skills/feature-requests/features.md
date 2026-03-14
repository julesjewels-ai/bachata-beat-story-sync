# Feature Backlog — Bachata Beat-Story Sync

> **🧹 Reset (2026-02-14):** Codebase stripped back to a clean, minimal foundation. All features reset to `PROPOSED` for re-implementation on solid ground. The core analysis engine (audio + video) remains stable and fully tested.
>
> **📋 Review (2026-02-23):** Backlog critically reviewed for end-user value. FEAT-010 (Structural Segmentation) removed — marginal visual impact vs. high complexity/dependency cost. Remaining features re-ordered by dependency and value.
>
> **📦 Archive (2026-03-13):** Completed features (FEAT-001 through FEAT-019) moved to [`archive/completed.md`](archive/completed.md) to reduce agent context usage. Only active/proposed features remain below.

---

## Completed Features (Reference)

The following features are fully implemented and archived. See [`archive/completed.md`](archive/completed.md) for full specs.

| Feature | Name | Status |
|---------|------|--------|
| FEAT-001 | Variable Clip Duration Based on Intensity | `IMPLEMENTED` |
| FEAT-002 | Speed Ramping (Slow-Mo / Fast-Forward) | `IMPLEMENTED` |
| FEAT-003 | Musical Section Awareness | `IMPLEMENTED` |
| FEAT-004 | Beat-Snap Transitions | `IMPLEMENTED` |
| FEAT-005 | Test Mode (Quick Iteration) | `IMPLEMENTED` |
| FEAT-006 | Clip Variety & Start Offset | `IMPLEMENTED` |
| FEAT-007 | Multi-Track Folder Input (Mix Creation) | `IMPLEMENTED` |
| FEAT-008 | Specific Clip Prefix Ordering | `VERIFIED` |
| FEAT-009 | Visual Intensity Matching | `VERIFIED` |
| FEAT-010 | Smooth Slow Motion Interpolation | `IMPLEMENTED` |
| FEAT-011 | Intermittent B-Roll Insertion | `VERIFIED` |
| FEAT-012 | Video Style Filters (Color Grading) | `IMPLEMENTED` |
| FEAT-013 | Music-Synced Waveform Overlay | `IMPLEMENTED` |
| FEAT-014 | Full Pipeline Orchestrator (Core) | `IMPLEMENTED` |
| FEAT-015 | Pipeline Shorts Integration | `IMPLEMENTED` |
| FEAT-016 | Shared Scan Optimization | `IMPLEMENTED` |
| FEAT-017 | Per-Track Intro Variety (Pipeline) | `DONE` |
| FEAT-018 | CLI Logging & UX System | `IMPLEMENTED` |
| FEAT-019 | Audio Hook Detection for Smart Start Selection | `IMPLEMENTED` |

---

## FEAT-020: Visual Scene-Change Detection for Smart Start

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟡 Medium                                            |
| **Effort**   | Medium–High                                          |
| **Impact**   | Medium — enhances hook quality beyond audio-only      |
| **Depends**  | FEAT-019 (Audio Hook Detection — provides the scoring framework and `audio_start_offset` plumbing) |

### Why this matters
FEAT-019 ensures the audio hook is strong, but the **visual** component is still random — the first clip shown might be a static shot that doesn't capture attention. Additionally, around the 4-second mark, FEAT-019 can detect an audio pace shift, but there's no guarantee the *video* also has a visual change at that moment.

By pre-analysing video clips for scene-change timestamps, the engine can:
1. **Select an opening clip that starts at a visually dynamic moment** (e.g., a dancer beginning a spin rather than standing still).
2. **Prefer clips with an internal scene change around 3–5s** so the visual pace aligns with the audio pace shift detected by FEAT-019.

### Description
Extend the video analysis pipeline to detect **scene-change timestamps** within each clip using frame-difference analysis. Store these timestamps as metadata on `VideoAnalysisResult`. During shorts generation, the segment planner uses this data to:

1. Pick opening clips that have high visual energy in the first 2 seconds.
2. Prefer clips with a natural scene change 3–5s in (or use the scene change as the clip's start offset).

### Implementation Details

#### Stage A — Scene-Change Detection in Video Analyzer

Extend `VideoAnalyzer.analyze()` to detect scene changes:

```python
# In video_analyzer.py

def _detect_scene_changes(
    self, cap: cv2.VideoCapture, threshold: float = 30.0
) -> list[float]:
    """
    Detect timestamps where significant visual changes occur.

    Uses frame-to-frame absolute difference (same approach as
    intensity scoring) but tracks per-frame spikes instead of averaging.

    Args:
        cap: OpenCV VideoCapture object (position will be reset).
        threshold: Minimum mean absolute difference to register as a scene change.

    Returns:
        List of timestamps (seconds) where scene changes occur.
    """
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    skip = max(1, int(video_fps / ANALYSIS_FPS))  # Reuse existing 3 FPS sampling
    # ... frame diff logic, already similar to _calculate_intensity ...
```

**Key design decisions:**
- **Reuse existing sampling rate** (`ANALYSIS_FPS = 3.0`) and resolution (`320×180`) — no new performance cost beyond what intensity analysis already does.
- **Piggyback on the existing `_calculate_intensity()` pass** — capture scene-change timestamps during the same loop that computes motion scores, avoiding a second pass over the video.
- **Threshold tuning:** Default `30.0` mean absolute difference works well for bachata clips (tested against FFmpeg's `select='gt(scene,0.3)'` which uses a different scale). Expose as a config param.

#### Stage B — Model Updates

Add scene-change data to `VideoAnalysisResult`:

```python
class VideoAnalysisResult(BaseModel):
    # ... existing fields ...
    scene_changes: list[float] = Field(
        default_factory=list,
        description="Timestamps (seconds) of detected visual scene changes within the clip"
    )
    opening_intensity: float = Field(
        0.0,
        description="Average visual motion intensity in the first 2 seconds (0.0-1.0)"
    )
```

**`opening_intensity`** is computed during the same analysis pass — it's the mean motion score of frames sampled within the first 2 seconds. This gives the smart-start system a fast lookup for "how visually interesting is this clip's opening?"

#### Stage C — Integration with Segment Planning

Modify `build_segment_plan()` (or a new helper) to use scene-change data:

**For the opening clip (first segment):**
```python
# Score candidate opening clips:
# opening_score = (0.5 × opening_intensity) +
#                 (0.5 × has_scene_change_near_4s)
#
# has_scene_change_near_4s = 1.0 if any scene_change in [3.0, 5.0], else 0.0

best_opener = max(candidates, key=lambda c: opening_score(c))
```

**For within-clip start offset (existing `clip_variety_enabled` logic):**
```python
# Instead of pure hash-based random offset, prefer starting at a scene-change:
if clip.scene_changes:
    # Find scene changes that leave enough room for segment_duration
    viable = [sc for sc in clip.scene_changes if sc + segment_duration <= clip.duration]
    if viable:
        # Pick the closest scene change to the hash-based offset (preserves determinism)
        start_time = min(viable, key=lambda sc: abs(sc - hashed_offset))
```

#### Stage D — Optional FFmpeg-based Scene Detection (Alternative Approach)

Instead of OpenCV-based analysis in Python, use FFmpeg's `select` filter during a pre-scan:

```bash
ffmpeg -i clip.mp4 -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -f null - 2>&1 | grep showinfo
```

**Pros:** Uses FFmpeg's battle-tested scene detection; no Python loop needed.
**Cons:** Requires spawning a subprocess per clip (~1-2s per clip); output parsing is fragile; adds FFmpeg as a hard dependency for analysis (currently only needed for rendering).

**Recommendation:** Use OpenCV (Stage A) as the primary approach since it piggybacks on the existing analysis pass. Offer FFmpeg as a `--scene-detection-method ffmpeg` alternative for users who want higher accuracy.

### Performance Considerations

| Concern | Analysis | Budget |
|---------|----------|--------|
| Scene-change detection during analysis | Piggybacks on existing intensity loop — adds ~5 comparisons per sampled frame and a list append on spikes. | **< 1% slowdown** on video scan |
| `opening_intensity` computation | Mean of first ~6 frames (2s ÷ 3 FPS analysis rate). Trivial. | **~0 additional cost** |
| Additional model fields | Two new fields on `VideoAnalysisResult`: `scene_changes` (list of floats, typically 0–5 entries per clip) and `opening_intensity` (float). | **< 1KB per clip** |
| Clip scoring during segment planning | Linear scan over `scene_changes` per candidate clip (typically 0–5 entries). | **< 1ms total** |
| FFmpeg alternative (Stage D) | Spawns one subprocess per clip. At 50 clips × 2s each = 100s additional scan time. | **Significant — optional only** |
| Memory: `scene_changes` in shared scan mode | With `--shared-scan` (FEAT-016), scene-change data is held in memory for all clips across all tracks. At 100 clips × 5 changes × 8 bytes = 4KB total. | **Negligible** |
| Thumbnail stripping | `thumbnail_data` is already stripped before montage (`model_copy(update={"thumbnail_data": None})`). `scene_changes` and `opening_intensity` should be preserved (they're small and needed). | **No change needed** |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scene-change threshold too sensitive — every clip has 20+ "changes" | Medium | Noise overwhelms signal, opener selection becomes random | Cap at top-5 strongest changes per clip; expose threshold as config |
| Scene-change threshold too strict — no changes detected | Low | Falls back to existing hash-based offset (FEAT-006) | Graceful fallback: if `scene_changes` is empty, skip visual scoring |
| Opening intensity doesn't correlate with "interesting" visuals | Medium | Static but colourful shots score high; dynamic but dark shots score low | Combine motion score (existing) with colour variance for a richer signal |
| Different video codecs produce different frame-diff magnitudes | Low | Threshold calibration varies per codec | Normalise frame diffs to 0.0–1.0 range per clip (already done for intensity) |
| Extra model field breaks existing serialization / tests | High (guaranteed) | Test failures | `scene_changes` defaults to `[]`, `opening_intensity` defaults to `0.0` — backward compatible |
| Interaction with FEAT-008 prefix ordering — forced clip ignores scene-change | Low | Prefix clips use their natural start | Intentional: prefix ordering = editorial override; scene-change logic only applies to non-forced clips |

### Files Changed

| File | Change |
|------|--------|
| `src/core/video_analyzer.py` | Extend `_calculate_intensity()` to capture scene-changes and opening_intensity (~30 lines); add `_detect_scene_changes()` if separate pass (~40 lines) |
| `src/core/models.py` | Add `scene_changes` and `opening_intensity` to `VideoAnalysisResult` (~6 lines) |
| `src/core/montage.py` | Modify opening clip selection logic in `build_segment_plan()` (~25 lines); modify within-clip start offset (~15 lines) |
| `src/shorts_maker.py` | No direct changes (uses montage.py planner which handles it) |
| `docs/configuration.md` | Document new config params |
| `tests/unit/test_video_analyzer.py` | New tests for scene-change detection (~40 lines) |
| `tests/unit/test_montage.py` | Update segment plan tests for scene-aware clip selection (~20 lines) |

### Scope
- **In scope:** Scene-change timestamp detection (OpenCV-based), opening_intensity scoring, scene-aware clip selection for shorts opener, scene-aware within-clip start offset, fallback to existing behaviour when no scene data exists.
- **Out of scope:** Content-aware scene detection (e.g., "this scene shows a dancer" vs "this scene shows a crowd"), AI/ML-based visual hook detection, per-frame visual quality scoring, FFmpeg scene detection as default (optional alternative only).

---

## FEAT-021: Waveform Overlay Padding / Margins

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟢 Low                                                |
| **Effort**   | Low                                                  |
| **Impact**   | Low–Medium — visual polish for the audio overlay     |
| **Depends**  | FEAT-013 (Music-Synced Waveform Overlay)             |

### Why this matters
When the waveform overlay is positioned on the right (the default), it sits too close to the frame edges — particularly the bottom and right. This looks visually cramped, especially on smaller screens where the overlay appears to bleed into the edge of the video. Proper padding gives the overlay breathing room and a more polished, professional look.

### Description
Add configurable padding (margins) to the waveform / bars overlay so it doesn't sit flush against the frame edges. The padding should apply to both the X and Y offset calculations in `_overlay_audio()`.

### Implementation Details
- Add `audio_overlay_padding: int` field to `PacingConfig` (default `20` pixels).
- Update the X-position expressions in `_overlay_audio()`:
  - `right` → `W-{overlay_w}-{padding}`  (currently hardcoded to `W-{overlay_w}-10`)
  - `left`  → `{padding}`               (currently hardcoded to `10`)
  - `center` → unchanged (centered is inherently padded)
- Update the Y-position expression:
  - Currently: `H-h-10`
  - After: `H-h-{padding}` (applies the same padding value to bottom margin)
- Add `--audio-overlay-padding` CLI argument to `main.py`, `shorts_maker.py`, and `pipeline.py`.
- Update `docs/configuration.md` with the new parameter.

### Scope
- **In scope:** Configurable X/Y padding for waveform overlay; CLI + config support.
- **Out of scope:** Per-axis padding (separate X and Y values), overlay repositioning to top of frame, animated margin effects.

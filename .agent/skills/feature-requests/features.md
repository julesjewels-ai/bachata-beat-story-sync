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

---

## FEAT-022: Intro Visual Effects

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟠 High                                              |
| **Effort**   | Medium                                               |
| **Impact**   | High — first impressions drive retention              |
| **Depends**  | None (standalone)                                    |

### Why this matters
The first 1-3 seconds determine whether a viewer keeps watching. Currently, all videos start with a hard cut to the first clip — no visual "hook" to capture attention. Social media algorithms reward strong openers, and competing dance/music channels use intro effects to stand out.

### Description
Add a configurable **intro visual effect** applied exclusively to the first segment of any generated video. Effects create a cinematic reveal that draws the eye before cutting to the main content.

### Effects (Phase 1)

#### Gaussian Bloom Reveal (`bloom`)
Gaussian blur fades from σ30 → σ0 over the intro duration, creating a dreamlike reveal into sharp focus.

**FFmpeg filter:** `gblur=sigma='30*(1-t/{d})':enable='lt(t,{d})'`

**Technical notes:** FFmpeg `gblur` supports expression-based sigma. The `enable` clause limits the filter to the intro window. Zero performance overhead outside the intro window.

#### Warm Vignette Breathe (`vignette_breathe`)
Tight dark vignette starts at the frame edges and expands outward, creating a theatrical spotlight effect.

**FFmpeg filter:** `vignette=a='PI/2-t*PI/{2d}':enable='lt(t,{d})'`

**Technical notes:** FFmpeg `vignette` accepts expression-based angle. The vignette intensity decreases as the angle expression increases. Simple and elegant.

### Effects (Phase 2 — requires beat timestamp helper)

#### Staggered Scale Pop (`scale_pop`)
Beat-synced zoom pops (80% → 90% → 100%) with blur during expansion, creating a rhythmic "pop-in" entrance.

**Implementation:** Build a beat-to-expression helper that generates `if(between(t,b1,b2), scale, ...)` chains from audio beat timestamps. Apply `scale` + `gblur` during each pop phase. Requires `SegmentPlan.timeline_position` to compute beat-relative timing.

**Risk:** Expression chains for many beats become very long. Mitigate by capping to 3-4 beats within the intro window.

#### Whip Pan Slide-In (`whip_slide`)
Frame slides in from the edge with motion blur, simulating a camera whip-pan.

**Implementation:** Use `crop` with animated x expression + `tblend=all_mode=average` for synthetic motion blur. Requires two filters in sequence.

**Risk:** Filter chain is more complex than other effects. The `tblend` filter combines current and previous frames, which requires specific filter ordering.

### Implementation Details

**Config model changes (`PacingConfig`):**
```python
intro_effect: Literal["none", "bloom", "vignette_breathe", "scale_pop", "whip_slide"] = "none"
intro_effect_duration: float = 1.5
```

**Filter injection point (`extract_segments()`):** Detect `i == 0` (first segment) and prepend intro filters to `vf_parts` before the style filter. This ensures:
1. Intro filters are processed first
2. Style filters (color grading) still apply on top
3. Speed ramping is unaffected

**CLI args:** `--intro-effect` (choices) + `--intro-effect-duration` (float)

### Performance Considerations

| Concern | Impact |
|---------|--------|
| Intro filter only applies to segment 0 | **Zero cost** for all other segments |
| `gblur` with expression | ~5% overhead on one segment (~2-6s of video) |
| `vignette` with expression | ~2% overhead on one segment |
| Phase 2 `scale_pop` | ~10% overhead on one segment (multiple filter stages) |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `gblur` expression syntax varies across FFmpeg versions | Low | Build failure on older FFmpeg | Test with FFmpeg 5.x+ (already required for `xfade`) |
| Intro effect interacts with speed ramp on segment 0 | Medium | Visual artifact: blur stretches during slow-mo | Apply intro filter AFTER `setpts` in `vf_parts` order |
| Phase 2 beat expression chain too long | Medium | FFmpeg truncation or error | Cap to 4 beats; test with long expressions |

### Files Changed

| File | Change |
|------|--------|
| `src/core/models.py` | Add `intro_effect` + `intro_effect_duration` to `PacingConfig` |
| `src/core/ffmpeg_renderer.py` | Add `_build_intro_filters()` helper; inject in `extract_segments()` for `i == 0` |
| `src/cli_utils.py` | Add `intro_effect`, `intro_effect_duration` to `build_pacing_kwargs()` |
| `src/pipeline.py` | Add `--intro-effect`, `--intro-effect-duration` CLI args |
| `src/shorts_maker.py` | Add `--intro-effect`, `--intro-effect-duration` CLI args |
| `montage_config.yaml` | Add `intro_effect`, `intro_effect_duration` under `pacing:` |
| `tests/unit/test_montage.py` | New `TestIntroEffects` test class |

### Scope
- **In scope:** bloom + vignette_breathe (Phase 1), scale_pop + whip_slide (Phase 2), configurable duration, CLI + YAML config, all video types.
- **Out of scope:** AI-generated visual hooks, per-clip intro customization, combining multiple intro effects (mutually exclusive).

---

## FEAT-023: Pacing Visual Effects

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟡 Medium                                            |
| **Effort**   | Low                                                  |
| **Impact**   | Medium — adds cinematic motion and energy             |
| **Depends**  | None (standalone, but pairs well with FEAT-022)      |

### Why this matters
Static frame composition makes long-form videos feel flat. Subtle camera motion (drift zoom, progressive tightening) and rhythm-synced colour pulses add a professional, "alive" quality without changing the content. These are staples of professional music video editing.

### Description
Add **pacing visual effects** that apply to all segments (or a time window) to create sustained visual energy. Unlike intro effects (FEAT-022), these run throughout the video. Each effect is independently toggleable.

### Effects

#### Drift Zoom (`pacing_drift_zoom`)
Slow 100% → 105% zoom over the video duration. Classic Ken Burns effect that adds gentle motion to static shots.

**FFmpeg filter:** `zoompan=z='1+0.0025*in':d=1:s={w}x{h}`

**Technical notes:** `d=1` outputs one frame per input frame (no frame rate change). The zoom rate `0.0025` produces ~5% zoom over ~20s of content. Applied per-segment, accumulating the subtle zoom within each clip.

#### Progressive Crop Tightening (`pacing_crop_tighten`)
Slowly zoom in over the first 10 seconds of each segment, creating a gentle "pull-in" effect.

**FFmpeg filter:** `zoompan=z='if(lt(in,300),1+0.005*(in/30),1.05)':d=1:s={w}x{h}`

**Technical notes:** Similar to drift zoom but with a ceiling — stops tightening at 5% zoom after ~10s. The `if()` expression prevents infinite zoom.

#### Pulsing Saturation (`pacing_saturation_pulse`)
Brief saturation surges on each beat, making the image "breathe" with the music.

**FFmpeg filter:** `eq=saturation='1+0.3*{beat_expression}'`

Where `{beat_expression}` is a chain of `if(between(t,B,B+0.1),1,0)` for each beat within the segment.

**Technical notes:** The `eq` filter supports expressions natively. Beat timestamps are relative to the segment's timeline position. Active for only 100ms per beat (imperceptible flicker), creating a subtle "pulse" effect.

### Implementation Details

**Config model changes (`PacingConfig`):**
```python
pacing_drift_zoom: bool = False
pacing_crop_tighten: bool = False
pacing_saturation_pulse: bool = False
```

**Filter injection:** Add `_build_pacing_filters(config, segment)` helper that returns filter strings. Append to `vf_parts` for **every segment** in `extract_segments()`.

**CLI args:** `--pacing-drift-zoom` (flag), `--pacing-crop-tighten` (flag), `--pacing-saturation-pulse` (flag)

### Performance Considerations

| Concern | Impact |
|---------|--------|
| `zoompan` with d=1 | ~3% overhead per segment (lightweight) |
| `eq` saturation expression | ~1% overhead (simple math) |
| Multiple pacing effects stacked | Additive — 3 effects ≈ 7% total overhead per segment |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `zoompan` changes output resolution | Medium | Stretched/blurry output | Explicitly set `s={w}x{h}` to match source resolution |
| Saturation pulse looks "flickery" | Low | Distracting | Use smooth `between()` window (100ms); expose duration as future config |
| Combining drift_zoom + crop_tighten = double zoom | Medium | Over-zoomed output | Document as mutually exclusive in config; warn in CLI help |

### Files Changed

| File | Change |
|------|--------|
| `src/core/models.py` | Add 3 boolean fields to `PacingConfig` |
| `src/core/ffmpeg_renderer.py` | Add `_build_pacing_filters()` helper; inject in `extract_segments()` for all segments |
| `src/cli_utils.py` | Add 3 boolean keys to `build_pacing_kwargs()` |
| `src/pipeline.py` | Add 3 `--pacing-*` flag args |
| `src/shorts_maker.py` | Add 3 `--pacing-*` flag args |
| `montage_config.yaml` | Add 3 pacing fields under `pacing:` |
| `tests/unit/test_montage.py` | New `TestPacingEffects` test class |

### Scope
- **In scope:** drift_zoom, crop_tighten, saturation_pulse; each independently toggleable; CLI + YAML config; all video types.
- **Out of scope:** Dynamic effect intensity based on audio intensity, per-section effect customization, animated colour grading shifts.

---

## FEAT-024: Advanced Beat-Synced Effects

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟡 Medium                                            |
| **Effort**   | Medium–High                                          |
| **Impact**   | Medium — premium polish for advanced users            |
| **Depends**  | FEAT-022 Phase 2 (shares beat-to-expression helper)  |

### Why this matters
Beat-synced visual effects are the hallmark of professional music video editing. Micro-jitters create physical "punch" on impacts, light leaks add cinematic warmth at key moments, and alternating depth creates visual variety across clips. These effects separate amateur edits from professional ones.

### Description
Add **advanced visual effects** that leverage beat timestamps for precise synchronization. These require the `_beats_to_expression()` helper introduced in FEAT-022 Phase 2 and represent the most sophisticated tier of the effects system.

### Effects

#### Beat-Synced Micro-Jitters (`micro_jitters`)
2-4 pixel random offset on each beat, creating a subtle "shake" that emphasises rhythm.

**Implementation:** Use `geq` filter with beat-timed x/y offset expressions, or `overlay` with computed offset per beat. The offset alternates direction per beat for variety.

**Risk:** Long beat expression chains. Mitigate by computing relative beats within each segment (typically 5-15 beats per segment).

#### Light Leak Flashes (`light_leaks`)
Warm orange/amber colour sweep at key beats, simulating analog film light leaks.

**Implementation:** Use `colorbalance=rs=0.3:gs=0.1:bs=-0.1:enable='...'` with beat-timed `enable` expressions. Each flash lasts ~200ms with a 100ms fade-in/out.

**Alternative:** Overlay a pre-rendered gradient PNG with timed opacity. Simpler but requires an asset file.

#### Warm Wash Transitions (`warm_wash`)
Brief amber flash between cuts — applied in the transition system rather than per-segment filters.

**Implementation:** Modify `apply_transitions()` to insert a brief (~150ms) colour overlay between segment boundaries. Could use `xfade` with a custom expression or insert a short solid-colour clip.

**Risk:** Changes the transition pipeline, not just `extract_segments()`. Requires careful integration with existing `transition_type` config.

#### Alternating Focus Depth (`alternating_bokeh`)
Every other segment gets a subtle background blur, creating depth variety.

**Implementation:** Apply `boxblur=luma_radius=4:enable='1'` to even-numbered segments during `extract_segments()`. Toggle via segment index `i % 2 == 0`.

**Technical notes:** `boxblur` is a computationally cheap alternative to true Gaussian bokeh. The luma-only blur preserves colour accuracy.

### Implementation Details

**Config model changes (`PacingConfig`):**
```python
pacing_micro_jitters: bool = False
pacing_light_leaks: bool = False
pacing_warm_wash: bool = False
pacing_alternating_bokeh: bool = False
```

**Beat-to-expression helper** (shared with FEAT-022 Phase 2):
```python
def _beats_to_expression(
    beat_times: list[float],
    segment_start: float,
    segment_duration: float,
    pulse_duration: float = 0.1,
) -> str:
    """Convert absolute beat timestamps to FFmpeg time expression within a segment.

    Returns a string like '(if(between(t,0.5,0.6),1,0)+if(between(t,1.0,1.1),1,0)+...)'
    where each beat is relative to the segment start.
    """
```

### Performance Considerations

| Concern | Impact |
|---------|--------|
| `geq` for micro-jitters | ~8% overhead per segment (per-pixel evaluation) |
| `colorbalance` for light leaks | ~2% overhead per segment |
| `boxblur` for alternating bokeh | ~5% overhead for every other segment |
| Beat expression chain length | 10-15 beats per segment → ~200 char expression (within FFmpeg limits) |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Micro-jitters cause motion sickness | Low | Negative viewer experience | Default 2px offset; cap at 4px; provide amplitude config later |
| Light leaks clash with video_style colour grading | Medium | Muddy colours | Apply light leaks AFTER style filter (order in `vf_parts`) |
| Warm wash modifies transition system | Medium | Regression in existing transitions | Isolated code path; only activated when `pacing_warm_wash=True` |
| Expression chain exceeds FFmpeg inline limit | Low | FFmpeg error | Cap beats per expression; split into multiple filter stages if needed |

### Files Changed

| File | Change |
|------|--------|
| `src/core/models.py` | Add 4 boolean fields to `PacingConfig` |
| `src/core/ffmpeg_renderer.py` | Add `_beats_to_expression()` helper; add 4 effect builders; inject in `extract_segments()` |
| `src/core/montage.py` | Pass `beat_times` to `extract_segments()` for beat-relative computation |
| `src/cli_utils.py` | Add 4 boolean keys to `build_pacing_kwargs()` |
| `src/pipeline.py` | Add 4 `--pacing-*` flag args |
| `src/shorts_maker.py` | Add 4 `--pacing-*` flag args |
| `montage_config.yaml` | Add 4 pacing fields under `pacing:` |
| `tests/unit/test_montage.py` | New `TestAdvancedEffects` test class |

### Scope
- **In scope:** micro_jitters, light_leaks, warm_wash, alternating_bokeh; each independently toggleable; beat-to-expression helper; CLI + YAML config; all video types.
- **Out of scope:** AI-driven beat detection (uses existing beat_times from audio analysis), per-beat effect intensity variation, real-time preview.

---

## FEAT-025: Decision Explainability Log (`--explain`)

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟠 High                                              |
| **Effort**   | Medium                                               |
| **Impact**   | High — directly addresses "transparency" in the mission statement |
| **Depends**  | None (standalone; reads existing internal state)     |

### Why this matters
The tool makes dozens of editorial decisions during montage generation — which clip to use at each beat, what duration to assign, which speed ramp to apply, when to insert B-roll, and why a clip was skipped. Today, none of these decisions are surfaced to the user. The output is a black box: audio goes in, video comes out.

For **visual technicians escaping GUI fatigue**, the transparency of the decision pipeline is the primary value proposition over a traditional NLE. They chose a CLI *because* they want to understand and control the logic. A hidden decision engine defeats that purpose.

### Description
Add an `--explain` CLI flag that produces a timestamped, human-readable decision log alongside the video output. The log documents every editorial choice the engine makes during `build_segment_plan()` and `extract_segments()`.

### Output Format

A plain-text / Markdown file (default: `{output_stem}_explain.md`) with entries like:

```
## Segment Plan — song.wav (128 BPM, 3m42s)

| Time      | Clip              | Intensity | Section  | Duration | Speed | Reason                                  |
|-----------|-------------------|-----------|----------|----------|-------|-----------------------------------------|
| 00:00.0   | 1_intro.mp4       | 0.42      | intro    | 4.0s     | 1.0x  | Forced prefix ordering (FEAT-008)       |
| 00:04.0   | dance_spin.mp4    | 0.87      | verse    | 2.5s     | 1.2x  | High intensity → matched to high section|
| 00:06.5   | broll/sunset.mp4  | —         | —        | 2.5s     | 1.0x  | B-roll interval triggered (13.5s ± 1.5) |
| 00:09.0   | slow_walk.mp4     | 0.22      | bridge   | 6.0s     | 0.9x  | Low intensity → slow-motion pacing      |
| ...       |                   |           |          |          |       |                                         |

### Skipped Clips
| Clip             | Reason                                           |
|------------------|--------------------------------------------------|
| corrupt.mp4      | Analysis failed: could not open video capture    |
| tiny.mp4         | Duration < min_clip_seconds (1.5s)               |

### Config Applied
| Parameter                  | Value  |
|----------------------------|--------|
| high_intensity_threshold   | 0.65   |
| low_intensity_threshold    | 0.35   |
| snap_to_beats              | true   |
| broll_interval_seconds     | 13.5   |
```

### Implementation Details

#### Data Collection
Add an `ExplainCollector` class (or simple list) that accumulates decision records during montage generation:

```python
@dataclass
class SegmentDecision:
    timeline_start: float
    clip_path: str
    intensity_score: float
    section_label: str
    duration: float
    speed: float
    reason: str

@dataclass
class SkipDecision:
    clip_path: str
    reason: str
```

The `MontageGenerator.generate()` and `build_segment_plan()` functions already have all the data needed at each decision point — the collector just captures it.

#### Injection Points
1. **`build_segment_plan()`** — When a clip is selected for a segment, record why (intensity match, forced prefix, B-roll trigger).
2. **`extract_segments()`** — When a clip is skipped or fails, record the skip reason.
3. **`generate()`** — At the end, write the collected decisions to the explain file.

#### CLI Integration
- `--explain` flag on `main.py`, `shorts_maker.py`, `pipeline.py`
- Output path derived from `--output`: `output_story_explain.md` for `output_story.mp4`
- Wired through `PacingConfig` or a separate `ExplainConfig` (lightweight — just a bool + output path)

### Performance Considerations

| Concern | Impact |
|---------|--------|
| Decision collection during segment planning | **< 1% overhead** — appending dataclass instances to a list |
| File write at end of pipeline | **< 1ms** — small text file written once |
| Memory: holding decisions in memory | **< 10KB** for a typical 50-segment montage |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Decision reasons are too generic ("intensity match") | Medium | Low utility for power users | Pre-define ~10 specific reason strings; include numerical thresholds in the reason |
| Explain file path collides with existing output | Low | Overwrites user file | Use `_explain.md` suffix; warn if file exists |
| Section labels are placeholders (not yet implemented) | Medium | Log shows empty section column | Graceful fallback: show "—" when section data unavailable |

### Files Changed

| File | Change |
|------|--------|
| `src/core/models.py` | Add `SegmentDecision`, `SkipDecision` dataclasses; add `explain: bool` to `PacingConfig` |
| `src/core/montage.py` | Instrument `build_segment_plan()` and `generate()` to collect and write decision log |
| `src/core/ffmpeg_renderer.py` | Capture skip reasons during `extract_segments()` |
| `main.py` | Add `--explain` flag |
| `src/pipeline.py` | Add `--explain` flag |
| `src/shorts_maker.py` | Add `--explain` flag |
| `docs/configuration.md` | Document `--explain` flag and output format |
| `tests/unit/test_montage.py` | New `TestExplainLog` class verifying decision capture |

### Scope
- **In scope:** Timestamped decision log, skip reasons, config summary, Markdown output, CLI flag on all entry points.
- **Out of scope:** Interactive explain mode (step-by-step approval), JSON output format (see FEAT-028), explain for audio analysis decisions, per-frame decision logging.

---

## FEAT-026: Dry-Run Plan Mode (`--dry-run`)

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟠 High                                              |
| **Effort**   | Medium                                               |
| **Impact**   | High — preview results without expensive FFmpeg rendering |
| **Depends**  | None (standalone; partially complementary to FEAT-025) |

### Why this matters
A full pipeline render can take 5–30 minutes depending on clip count and duration. Users exhausted by GUI timelines don't want to wait for a render to discover the clip selection was wrong. They need a way to **inspect the plan before committing to the expensive FFmpeg pass**.

This is the CLI equivalent of a "timeline preview" — except instead of a visual timeline, it's a structured text plan that can be reviewed, diffed, and iterated on in seconds.

### Description
Add a `--dry-run` flag that runs the full analysis pipeline (audio analysis + video scanning + segment planning) but **stops before rendering**. It outputs the complete segment plan as a human-readable table and/or machine-readable file, showing exactly what the final video would contain.

### Output Format

Printed to stdout (or file with `--dry-run-output PATH`):

```
DRY RUN — No video will be rendered.

Audio: song.wav (128 BPM, 3m42s, 88 beats)
Clips: 23 analyzed, 21 usable, 2 skipped
Estimated output: 3m42s at 720p/24fps

Segment Plan (32 segments):
  #01  00:00.0 → 00:04.0  1_intro.mp4        [forced]    1.0x  4.0s
  #02  00:04.0 → 00:06.5  dance_spin.mp4     [high 0.87] 1.2x  2.5s
  #03  00:06.5 → 00:09.0  broll/sunset.mp4   [b-roll]    1.0x  2.5s
  #04  00:09.0 → 00:15.0  slow_walk.mp4      [low 0.22]  0.9x  6.0s
  ...

Skipped: corrupt.mp4 (analysis failed), tiny.mp4 (< 1.5s)
Config: montage_config.yaml (snap_to_beats=true, broll_interval=13.5s)

Run without --dry-run to render.
```

### Implementation Details

#### Pipeline Short-Circuit
The `main()` function currently runs:
1. `AudioAnalyzer.analyze()` → ✅ still runs
2. `BachataSyncEngine.scan_video_library()` → ✅ still runs
3. `BachataSyncEngine.generate_story()` → ❌ **skipped in dry-run**

The segment plan is currently built *inside* `MontageGenerator.generate()`. To support dry-run, the planning logic needs to be **extractable** without triggering FFmpeg:

```python
# Option A: Extract plan as a separate method
plan = montage_generator.build_plan(audio_data, video_clips, pacing)
if not dry_run:
    montage_generator.render(plan, output_path)
```

This is a minor refactor of `generate()` — split it into `build_plan()` + `render()`.

#### CLI Integration
- `--dry-run` flag on `main.py`, `shorts_maker.py`, `pipeline.py`
- `--dry-run-output PATH` optional file output (default: stdout)
- Combine with `--explain` for maximum transparency

### Performance Considerations

| Concern | Impact |
|---------|--------|
| Audio analysis still runs (~2-5s) | **Required** — plan depends on beat data |
| Video scan still runs (~1-3s per clip) | **Required** — plan depends on intensity scores |
| FFmpeg rendering skipped | **100% savings** — this is the expensive step (minutes) |
| Total dry-run time | **5–30 seconds** for a typical project (vs. 5–30 minutes for full render) |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Refactoring `generate()` into `build_plan()` + `render()` introduces regression | Medium | Broken montage generation | Comprehensive existing test suite covers `generate()` behavior |
| Plan output diverges from actual render due to FFmpeg-side decisions | Low | User confusion | Document that plan shows *intended* segments; FFmpeg may adjust frame boundaries |
| Dry-run for pipeline mode (multi-track) produces overwhelming output | Medium | Hard to read | Group by track; add `--dry-run-output` for file dumps |

### Files Changed

| File | Change |
|------|--------|
| `src/core/montage.py` | Refactor `generate()` → `build_plan()` + `render()`; add `SegmentPlan` data structure |
| `src/core/models.py` | Add `SegmentPlan` model (list of planned segments with metadata) |
| `main.py` | Add `--dry-run` and `--dry-run-output` flags; short-circuit after planning |
| `src/pipeline.py` | Add `--dry-run` flag; skip render per track |
| `src/shorts_maker.py` | Add `--dry-run` flag; skip render |
| `docs/configuration.md` | Document dry-run flags and output format |
| `tests/unit/test_montage.py` | New `TestDryRun` class; test `build_plan()` independently |

### Scope
- **In scope:** Dry-run flag, segment plan output (text), build_plan/render refactor, all entry points.
- **Out of scope:** Interactive plan editing (approve/reject segments), visual timeline rendering, exporting plan as EDL/AAF/XML for NLE import.

---

## FEAT-027: Genre Preset System

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟡 Medium                                            |
| **Effort**   | Low–Medium                                           |
| **Impact**   | High — unlocks the tool for non-Bachata users        |
| **Depends**  | None (standalone)                                    |

### Why this matters
The underlying technology (Librosa beat detection, OpenCV intensity scoring, FFmpeg assembly) is completely **genre-agnostic**. It works on hip-hop, salsa, corporate videos, wedding footage — anything with audio and video. But the project branding, config defaults, and documentation are locked to Bachata.

The mission statement says *"video-audio synchronization"* broadly. Users who find this tool attractive but work with different content genres would be deterred by the Bachata-specific naming or confused by pacing defaults tuned for Latin dance (e.g., `broll_interval: 13.5s` makes no sense for a 30-second corporate reel).

### Description
Introduce a **genre preset system** that ships pre-tuned `montage_config.yaml` profiles for different content types. A `--preset` CLI flag loads a named preset, overriding default pacing, effects, and timing values. Custom user configs still override presets (layered config resolution).

### Presets (Initial Set)

| Preset | BPM Range | Pacing Philosophy | Key Overrides |
|--------|-----------|-------------------|---------------|
| `bachata` | 120–140 | Sensual, flowing, musical breathing room | Current defaults (high: 2.5s, low: 6.0s, broll: 13.5s) |
| `salsa` | 160–220 | Fast cuts, high energy, minimal slow-motion | high: 1.5s, medium: 2.5s, low: 3.0s, speed_ramp_multiplier: 1.3, broll: 10s |
| `hiphop` | 70–100 | Beat-heavy, staccato cuts, hard transitions | high: 2.0s, medium: 3.0s, snap_to_beats: true, transition: none (hard cuts) |
| `cinematic` | — | Slow, emotional, long holds, dramatic pacing | high: 4.0s, medium: 6.0s, low: 10.0s, speed_ramp_enabled: false, broll: 25s |
| `corporate` | — | Even pacing, professional, no speed ramps | high: 3.0s, medium: 4.0s, low: 5.0s, speed_ramp_enabled: false, broll: 15s |
| `fast` | — | Quick social media cuts, maximum energy | high: 1.0s, medium: 1.5s, low: 2.0s, accelerate_pacing: true |

### Implementation Details

#### Preset Storage
Ship presets as YAML files in a `presets/` directory within the package:

```
src/
  presets/
    bachata.yaml
    salsa.yaml
    hiphop.yaml
    cinematic.yaml
    corporate.yaml
    fast.yaml
```

Each is a valid `montage_config.yaml` fragment containing only the fields that differ from defaults.

#### Config Resolution Order
```
CLI args → montage_config.yaml (user file) → preset YAML → hardcoded defaults
```

This means:
1. A `--preset salsa` loads `presets/salsa.yaml`
2. A user's `montage_config.yaml` overrides any preset values
3. CLI args override everything

#### CLI Integration
```bash
# Use the salsa preset
python main.py --audio track.wav --video-dir ./clips/ --preset salsa

# Use a preset but override one value
python main.py --audio track.wav --video-dir ./clips/ --preset cinematic --broll-interval 20

# List available presets
python main.py --list-presets
```

### Performance Considerations

| Concern | Impact |
|---------|--------|
| Loading a YAML preset file | **< 1ms** — small file, parsed once at startup |
| Config merge logic | **< 1ms** — dict.update() of ~15 keys |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Preset defaults are wrong for actual genre (e.g., "salsa" feels too fast) | Medium | Poor output quality | Document presets as starting points; encourage user overrides via `montage_config.yaml` |
| Users expect content-aware AI (e.g., "detect this is salsa") | Low | Feature confusion | Clearly document that presets are pacing profiles, not content recognition |
| Preset YAML format diverges from `montage_config.yaml` format | Low | Config bug | Both use the same `PacingConfig` model; presets are just partial YAML |

### Files Changed

| File | Change |
|------|--------|
| `src/presets/` | **[NEW]** Directory with 6 preset YAML files |
| `src/core/models.py` | Add `preset: Optional[str]` to config loading; add `list_presets()` helper |
| `main.py` | Add `--preset` and `--list-presets` flags; integrate config merge |
| `src/pipeline.py` | Add `--preset` flag |
| `src/shorts_maker.py` | Add `--preset` flag |
| `docs/configuration.md` | Document preset system, available presets, config resolution order |
| `tests/unit/test_config.py` | **[NEW]** Test preset loading, merge precedence, list-presets |

### Scope
- **In scope:** 6 shipped presets, `--preset` flag, `--list-presets`, config resolution order, preset YAML files.
- **Out of scope:** Auto-detecting genre from audio, user-defined preset directories, per-section presets (e.g., different pacing for verse vs. chorus), community preset sharing.

---

## FEAT-028: Structured JSON Output (`--output-json`)

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟡 Medium                                            |
| **Effort**   | Low                                                  |
| **Impact**   | Medium–High — enables scripting and pipeline composition |
| **Depends**  | FEAT-026 (Dry-Run Mode — shares the `SegmentPlan` data structure) |

### Why this matters
Power users fighting interface fatigue often work in **scripted pipelines** — bash scripts, Makefiles, Python orchestrators. They pipe the output of one tool into the next. Currently, the tool's output is purely side-effects (writes an MP4 file) with no structured data on stdout.

A JSON output mode enables:
- Piping analysis results into custom post-processing scripts
- Building CI/CD pipelines that conditionally render based on analysis data
- Integrating with external tools (e.g., feeding clip intensity data into a dashboard)
- Diff-ing analysis results between runs (`jq`, `diff`)

### Description
Add an `--output-json` flag that emits structured JSON to stdout (or file) containing the complete analysis results, segment plan, and render metadata. This makes every stage of the pipeline programmatically accessible.

### Output Schema

```json
{
  "version": "0.1.0",
  "timestamp": "2026-03-17T16:00:00Z",
  "audio": {
    "file_path": "/path/to/song.wav",
    "bpm": 128.0,
    "duration": 222.5,
    "beat_count": 88,
    "peaks": [0.5, 1.0, 1.5, ...],
    "sections": ["intro", "verse", "chorus", ...]
  },
  "clips": [
    {
      "path": "/path/to/clip.mp4",
      "intensity_score": 0.87,
      "duration": 12.3,
      "status": "used"
    }
  ],
  "segment_plan": [
    {
      "index": 0,
      "timeline_start": 0.0,
      "timeline_end": 4.0,
      "clip_path": "/path/to/clip.mp4",
      "speed": 1.2,
      "reason": "high intensity match"
    }
  ],
  "output": {
    "path": "/path/to/output_story.mp4",
    "duration": 222.5,
    "resolution": "1280x720",
    "codec": "libx264"
  },
  "config": {
    "preset": null,
    "snap_to_beats": true,
    "broll_interval_seconds": 13.5
  }
}
```

### Implementation Details

#### Serialisation
All core data models (`AudioAnalysisResult`, `VideoAnalysisResult`, `SegmentPlan`) are already Pydantic `BaseModel` subclasses — they have `.model_dump()` built in. The JSON output is essentially assembling existing model dumps into a wrapper:

```python
import json

output = {
    "version": __version__,
    "timestamp": datetime.utcnow().isoformat(),
    "audio": audio_data.model_dump(exclude={"peaks"} if not verbose else set()),
    "clips": [c.model_dump(exclude={"thumbnail_data"}) for c in clips],
    "segment_plan": plan.model_dump() if plan else None,
    "output": {"path": str(output_path), ...},
    "config": pacing.model_dump(),
}

if args.output_json == "-":
    print(json.dumps(output, indent=2, default=str))
else:
    Path(args.output_json).write_text(json.dumps(output, indent=2, default=str))
```

#### Thumbnail Exclusion
`thumbnail_data` (bytes) must be excluded from JSON serialization — it's binary data that doesn't belong in a JSON stream. The `exclude={"thumbnail_data"}` on `model_dump()` handles this.

#### CLI Integration
```bash
# JSON to stdout
python main.py --audio song.wav --video-dir ./clips/ --output-json -

# JSON to file
python main.py --audio song.wav --video-dir ./clips/ --output-json analysis.json

# Combine with dry-run for analysis-only JSON
python main.py --audio song.wav --video-dir ./clips/ --dry-run --output-json -

# Pipe into jq
python main.py ... --output-json - | jq '.clips | sort_by(.intensity_score) | reverse'
```

### Performance Considerations

| Concern | Impact |
|---------|--------|
| JSON serialisation via Pydantic | **< 10ms** — models are small |
| File write / stdout print | **< 1ms** |
| Excluding thumbnail_data | **Saves ~50KB per clip** from JSON output |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JSON schema changes break downstream scripts | Medium | User scripts fail | Include `version` field; document schema stability commitment |
| Peaks array is very large (thousands of entries) | Low | JSON file size bloat | Default to excluding `peaks`; include with `--verbose-json` |
| Combining `--output-json` with normal stdout logging | High | Interleaved text and JSON | Route all logs to stderr when `--output-json -` is used |

### Files Changed

| File | Change |
|------|--------|
| `main.py` | Add `--output-json` flag; assemble and emit JSON at end of pipeline |
| `src/pipeline.py` | Add `--output-json` flag; per-track JSON objects |
| `src/shorts_maker.py` | Add `--output-json` flag |
| `src/core/models.py` | No changes needed (Pydantic already provides `model_dump()`) |
| `docs/configuration.md` | Document `--output-json`, output schema, `jq` examples |
| `tests/unit/test_json_output.py` | **[NEW]** Validate JSON structure, thumbnail exclusion, version field |

### Scope
- **In scope:** JSON output to stdout/file, all analysis + plan + config data, thumbnail exclusion, version field, `--output-json` on all entry points.
- **Out of scope:** GraphQL/REST API, streaming JSON during pipeline, binary data (thumbnails) in JSON, backwards-compatible schema versioning system.

---

## FEAT-029: File Watcher with Incremental Re-render (`--watch`)

| Field        | Value                                                |
|--------------|------------------------------------------------------|
| **Status**   | `PROPOSED`                                           |
| **Priority** | 🟢 Low                                                |
| **Effort**   | High                                                 |
| **Impact**   | Medium — fast iteration loop for power users         |
| **Depends**  | FEAT-026 (Dry-Run Mode — reuses `build_plan()` / `render()` split) |

### Why this matters
GUI editors let users tweak and see results in near-real-time. The CLI equivalent is a **file watcher** that detects changes to clips, config, or audio and automatically re-runs the pipeline. Without it, every iteration requires manually re-invoking the command — friction that pushes users back toward GUIs.

This is the biggest gap for converting "interface-fatigued" users: they left GUIs for speed and control, but they don't want to sacrifice the tight feedback loop.

### Description
Add a `--watch` flag that monitors the input directories and config file for changes, then automatically re-runs the pipeline when changes are detected. Combined with `--test-mode` (or `--dry-run`), this creates a near-instant iteration loop.

### Watched File Types

| Source | Events Watched | Action |
|--------|----------------|--------|
| `--video-dir` contents | File added/removed/modified | Re-scan video library + re-render |
| `--broll-dir` contents | File added/removed/modified | Re-scan B-roll + re-render |
| `--audio` file | File modified | Re-analyse audio + re-render |
| `montage_config.yaml` | File modified | Reload config + re-render |

### Implementation Details

#### Watcher Library
Use Python's `watchdog` library (lightweight, cross-platform):

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PipelineWatcher(FileSystemEventHandler):
    def __init__(self, pipeline_fn, debounce_seconds=2.0):
        self.pipeline_fn = pipeline_fn
        self.debounce_seconds = debounce_seconds
        self._last_trigger = 0.0

    def on_any_event(self, event):
        now = time.time()
        if now - self._last_trigger < self.debounce_seconds:
            return  # Debounce rapid filesystem events
        self._last_trigger = now
        self.pipeline_fn()
```

#### Debouncing
File saves often trigger multiple filesystem events (write, rename, metadata update). A 2-second debounce window ensures the pipeline only re-runs once per logical save.

#### Incremental Re-scan (Optimisation)
On file change, only re-analyse the changed clip (not the entire library). Cache `VideoAnalysisResult` objects by `(file_path, mtime)` and only recompute when `mtime` changes.

```python
class ScanCache:
    _cache: dict[tuple[str, float], VideoAnalysisResult] = {}

    def get_or_analyse(self, path: str, analyzer: VideoAnalyzer) -> VideoAnalysisResult:
        mtime = os.path.getmtime(path)
        key = (path, mtime)
        if key not in self._cache:
            self._cache[key] = analyzer.analyze(VideoAnalysisInput(file_path=path))
        return self._cache[key]
```

#### CLI Integration
```bash
# Watch mode with test-mode for fast iteration
python main.py --audio song.wav --video-dir ./clips/ --watch --test-mode

# Watch mode with dry-run for instant plan feedback
python main.py --audio song.wav --video-dir ./clips/ --watch --dry-run

# Watch with full render (slower, but automatic)
python main.py --audio song.wav --video-dir ./clips/ --watch
```

### Performance Considerations

| Concern | Impact |
|---------|--------|
| `watchdog` Observer thread | **Negligible** — single background thread, event-driven |
| Debounce window | **2s delay** between save and re-run (configurable) |
| Full re-render on each change | **5-30 minutes** — mitigated by `--test-mode` or `--dry-run` |
| Incremental scan cache | **Saves 1-3s per unchanged clip** on re-scan |
| Memory: holding scan cache | **~10KB per clip** (VideoAnalysisResult without thumbnails) |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `watchdog` dependency adds weight | Low | New pip dependency | `watchdog` is lightweight, well-maintained, widely used |
| Rapid saves cause multiple renders | Medium | Wasted CPU | Debounce window; cancel in-progress render on new trigger |
| Watch mode on large directories (1000+ files) | Low | High CPU from inotify | Set `recursive=False` by default; document limitations |
| FFmpeg process left running after Ctrl+C | Medium | Zombie process | Register signal handler to terminate subprocess on exit |
| Stale cache entry if file is replaced with same mtime | Very Low | Wrong analysis results | Include file size in cache key alongside mtime |

### Files Changed

| File | Change |
|------|--------|
| `requirements.txt` | Add `watchdog>=4.0.0` |
| `src/core/watch.py` | **[NEW]** `PipelineWatcher`, `ScanCache`, debounce logic |
| `main.py` | Add `--watch` flag; wrap pipeline in watch loop |
| `src/pipeline.py` | Add `--watch` flag |
| `src/shorts_maker.py` | Add `--watch` flag |
| `docs/configuration.md` | Document watch mode, debounce, cache behavior |
| `tests/unit/test_watch.py` | **[NEW]** Test debounce, cache invalidation, signal handling |

### Scope
- **In scope:** File watching for video/audio/config changes, debounce, incremental scan cache, `--watch` on all entry points, Ctrl+C cleanup.
- **Out of scope:** Live preview (video player integration), hot-reload of Python code, network file system watching, multi-project watching, GUI file picker.

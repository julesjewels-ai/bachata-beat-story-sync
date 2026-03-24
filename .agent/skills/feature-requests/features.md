# Feature Backlog — Bachata Beat-Story Sync

> **🧹 Reset (2026-02-14):** Codebase stripped back to a clean, minimal foundation. All features reset to `PROPOSED` for re-implementation on solid ground. The core analysis engine (audio + video) remains stable and fully tested.
>
> **📋 Review (2026-02-23):** Backlog critically reviewed for end-user value. FEAT-010 (Structural Segmentation) removed — marginal visual impact vs. high complexity/dependency cost. Remaining features re-ordered by dependency and value.
>
> **📦 Archive (2026-03-23):** Completed features (FEAT-001 through FEAT-019, FEAT-022, FEAT-025, FEAT-026, FEAT-027) moved to [`archive/completed.md`](archive/completed.md) to reduce agent context usage. Only active/proposed features remain below.
>
> **📦 Archive (2026-03-24):** Completed features FEAT-020, FEAT-028, and FEAT-029 moved to archive. FEAT-028 was incorrectly marked PROPOSED despite being fully implemented. FEAT-029 was missing from the reference table.

---

## Completed Features (Reference)

The following features are fully implemented and archived. See [`archive/completed.md`](archive/completed.md) for summaries.

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
| FEAT-020 | Visual Scene-Change Detection for Smart Start | `IMPLEMENTED` |
| FEAT-022 | Intro Visual Effects | `IMPLEMENTED` |
| FEAT-025 | Decision Explainability Log (`--explain`) | `DONE` |
| FEAT-026 | Dry-Run Plan Mode (`--dry-run`) | `DONE` |
| FEAT-027 | Genre Preset System (`--genre`) | `DONE` |
| FEAT-028 | Structured JSON Output (`--output-json`) | `IMPLEMENTED` |
| FEAT-029 | File Watcher with Incremental Re-render (`--watch`) | `DONE` |

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



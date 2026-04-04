# Feature Backlog — Bachata Beat-Story Sync

**Status:** All 35 core features complete. See [`archive/completed.md`](archive/completed.md) for reference.

---

## FEAT-036: Energy-Driven Speed Ramps

**Status:** `PROPOSED`

**Summary:** Vary playback speed dynamically within clips based on section intensity, rather than applying a static speed multiplier.

**Motivation:** Static speed changes (e.g., always 1.2x) feel mechanical. Organic pacing should accelerate *into* high-energy peaks and decelerate *out of* them, following the natural breath of the music. This creates a more cinematic, energetic feel.

**Current Behavior:**
- Each clip gets a fixed speed adjustment (e.g., `speed_multiplier=1.1` during intense sections)
- Entire clip plays at that constant speed

**Proposed Behavior:**
- Divide clip into temporal windows aligned to beat grid or section boundaries
- For each window, calculate target speed based on section intensity (0.8x for calm, 1.3x+ for peaks)
- Apply ramping curve (linear, ease-in, ease-out, or quadratic) to smoothly transition speeds between windows
- Render via FFmpeg's `setpts` filter to achieve sub-frame-accurate speed changes

**Examples:**
- Intro (low energy): start at 0.9x, ramp to 1.0x by beat 4
- Build (rising energy): 1.0x → 1.2x over 8 beats  
- Peak (high energy): hold 1.3x for 4 beats
- Breakdown (falling energy): 1.3x → 0.95x over 8 beats

**Scope:** 
- `src/core/montage.py` — extend `SegmentPlan` with speed ramp keyframes
- `src/core/ffmpeg_utils.py` — add ramp rendering helper (smooth `setpts` generation)
- `src/core/models.py` — add `SpeedRampConfig` with curve type + sensitivity knobs
- `montage_config.yaml` — add `pacing.speed_ramp_enabled`, `speed_ramp_curve` (linear/ease_in/ease_out), `speed_ramp_sensitivity` (how aggressively to respond to intensity)

**Questions to clarify:**
- Should ramp timing align to beats, or to onset of intensity changes in the intensity curve?
- What curve types feel best? (Suggest: ease_in, ease_out, and linear as fallback)
- Should ramping be per-clip, per-segment, or both?

---

_Add new features below this line._


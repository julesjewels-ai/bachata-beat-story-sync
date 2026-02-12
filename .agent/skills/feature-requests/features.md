# Feature Backlog — Bachata Beat-Story Sync

> Dynamic video editing features to make the montage feel more alive and in time with the music.

---

## FEAT-001: Variable Clip Duration Based on Intensity

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🔴 High                              |
| **Effort**  | Medium                               |
| **Impact**  | High — biggest single improvement    |

### Description
Currently every clip segment is a fixed 4-beat bar (`bar_duration = beat_duration * 4`). This makes the edit feel metronomic.

**Proposed behavior:**
- **High intensity** → 2-beat cuts (fast, energetic)
- **Medium intensity** → 4-beat bars (standard)
- **Low intensity** → 8-beat holds (breathing room)

### Files Affected
- `src/core/montage.py` — `generate()` method, segment duration logic

### Acceptance Criteria
- [ ] Clips during high-intensity sections are ~2 beats long
- [ ] Clips during low-intensity sections are ~8 beats long
- [ ] Medium-intensity sections retain 4-beat cuts
- [ ] Output video timing still sums to full audio duration
- [ ] Existing tests still pass

---

## FEAT-002: Speed Ramping (Slow-Mo / Fast-Forward)

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `PROPOSED`                           |
| **Priority**| 🟡 Medium                            |
| **Effort**  | Medium                               |
| **Impact**  | High — cinematic and professional    |

### Description
Apply MoviePy speed effects to clips based on their matched audio intensity.

**Proposed behavior:**
- **Emotional peaks / breakdowns** → slow-motion (0.6x–0.8x)
- **High energy (derecho)** → slight speed-up (1.15x–1.3x)
- **Optional**: brief freeze-frame on major onset hits

### Files Affected
- `src/core/montage.py` — `_create_video_segment()`, add speed effects
- `src/core/models.py` — potentially add speed metadata

### Acceptance Criteria
- [ ] Slow-mo applied during low-intensity / breakdown segments
- [ ] Speed-up applied during high-intensity segments
- [ ] Speed-adjusted clip durations still match segment timing
- [ ] No audio pitch artifacts (clip audio is replaced by the master audio)
- [ ] Existing tests still pass

---

## FEAT-003: Musical Section Awareness

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `PROPOSED`                           |
| **Priority**| 🟡 Medium                            |
| **Effort**  | High                                 |
| **Impact**  | Medium — improves narrative structure|

### Description
Currently `AudioAnalyzer.analyze()` returns `sections = ["full_track"]` (placeholder). Enhance it to detect actual musical sections (intro, verse, chorus, breakdown, outro) using `librosa.segment`.

**Proposed behavior:**
- Detect section boundaries using spectral clustering
- Label sections based on energy profile
- Pass section labels to `MontageGenerator` so editing style can vary per section (e.g., longer holds in intro, rapid cuts in chorus)

### Files Affected
- `src/core/audio_analyzer.py` — section detection logic
- `src/core/models.py` — `AudioAnalysisResult.sections` schema
- `src/core/montage.py` — consume section labels in `generate()`

### Acceptance Criteria
- [ ] At least 3 distinct sections detected for typical bachata tracks
- [ ] Section labels available in `AudioAnalysisResult`
- [ ] Montage adjusts editing style per section
- [ ] Existing tests still pass

---

## FEAT-004: Beat-Snap Transitions

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `PROPOSED`                           |
| **Priority**| 🟢 Low                               |
| **Effort**  | Low–Medium                           |
| **Impact**  | Medium — polish and professionalism  |

### Description
Align transition effects precisely to beat timestamps instead of hard-cutting.

**Proposed behavior:**
- Cross-dissolve transitions snapped to beat boundaries
- Optional flash-cut on strong beats (beat 1 of a bar)
- Transitions duration proportional to BPM (faster BPM = shorter transition)

### Files Affected
- `src/core/montage.py` — transition logic in `generate()` / concatenation

### Acceptance Criteria
- [ ] Transitions occur aligned to detected beat timestamps
- [ ] Cross-dissolve duration scales with BPM
- [ ] No visual glitches at transition boundaries
- [ ] Existing tests still pass

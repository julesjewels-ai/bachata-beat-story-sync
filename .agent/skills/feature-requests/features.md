# Feature Backlog — Bachata Beat-Story Sync

> **⚠️ Note (2026-02-14):** All montage-dependent features have been reverted due to persistent memory leaks in the montage pipeline. The core analysis engine (audio + video) remains stable. These features can be re-proposed once a memory-safe montage architecture is designed.

---

## FEAT-001: Variable Clip Duration Based on Intensity

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `IMPLEMENTED`                        |
| **Priority**| 🔴 High                              |
| **Effort**  | Medium                               |
| **Impact**  | High — biggest single improvement    |

### Description
Vary clip segment duration based on audio intensity instead of fixed 4-beat bars.

- **High intensity** (≥0.65) → 2-beat cuts (fast, energetic)
- **Medium intensity** (0.35–0.65) → 4-beat bars (standard)
- **Low intensity** (<0.35) → 8-beat holds (breathing room)

### Architecture
Memory-safe open-close-per-clip pattern: only 1 `VideoFileClip` open at a time. Each segment rendered to temp file, clip closed immediately. Final concatenation via FFmpeg concat demuxer.

---

## FEAT-002: Speed Ramping (Slow-Mo / Fast-Forward)

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `REVERTED`                           |
| **Priority**| 🟡 Medium                            |
| **Effort**  | Medium                               |
| **Impact**  | High — cinematic and professional    |

### Description
Apply MoviePy speed effects to clips based on their matched audio intensity.

### Revert Reason
Depended on `MontageGenerator` which caused memory leaks via unmanaged FFmpeg processes.

---

## FEAT-003: Musical Section Awareness

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `REVERTED`                           |
| **Priority**| 🟡 Medium                            |
| **Effort**  | High                                 |
| **Impact**  | Medium — improves narrative structure|

### Description
Detect musical sections (intro, verse, chorus, breakdown, outro) from audio analysis.

### Revert Reason
Section detection via `librosa.segment` caused heavy memory allocations. Removed along with montage.

---

## FEAT-004: Beat-Snap Transitions

| Field       | Value                                |
|-------------|--------------------------------------|
| **Status**  | `REVERTED`                           |
| **Priority**| 🟢 Low                               |
| **Effort**  | Low–Medium                           |
| **Impact**  | Medium — polish and professionalism  |

### Description
Align transition effects precisely to beat timestamps instead of hard-cutting.

### Revert Reason
Depended on `MontageGenerator` which has been removed.

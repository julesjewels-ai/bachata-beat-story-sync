# Feature Backlog — Bachata Beat-Story Sync

> **📦 Archive (2026-04-01):** All implemented features (FEAT-001 through FEAT-029) moved to [`archive/completed.md`](archive/completed.md). Backlog is clean — no active feature requests.

---

## Completed Features (Reference)

All 29 features are fully implemented and archived. See [`archive/completed.md`](archive/completed.md) for summaries.

---

_No active feature requests. Add new `PROPOSED` features below this line._

---

## FEAT-030 — Per-Track Video Clip Pools in Full Pipeline

**Status:** `PROPOSED`

**Summary:** When running the full pipeline, allow users to optionally assign a dedicated folder of video clips (and B-roll) to each individual song, rather than sharing a single global pool across all tracks and the mix.

**Motivation:** Currently `pipeline.py` uses one `--video-dir` for every output — the mix video, every per-track video, and every Short. When a DJ set contains stylistically different songs, reusing the same clip pool makes all outputs look visually identical. Song-specific clip pools give each per-track video its own identity.

**Proposed Behaviour:**
- The existing `--video-dir` global pool remains the default and fallback — no breaking change.
- Users may optionally place per-track clip folders alongside their audio files, following a naming convention, e.g.:
  - `audio_folder/track1.wav` → `audio_folder/track1_clips/` (or a config key)
  - Alternatively, a YAML mapping in `montage_config.yaml` under `pipeline.track_clips`:
    ```yaml
    pipeline:
      track_clips:
        track1.wav: clips/track1/
        track2.wav: clips/track2/
    ```
- If a per-track folder is found/configured, it is used for that track's per-track video and Shorts; the global pool is used for the mix video and any track without a dedicated folder.
- B-roll discovery follows the same scoping: per-track folder first, then global fallback.

**Scope:** `src/pipeline.py`, `src/core/app.py`, `src/core/models.py` (`PacingConfig` or new `PipelineConfig`), `montage_config.yaml` schema, CLI docs.

---

## FEAT-031 — Per-Track Video Style Filter in Full Pipeline

**Status:** `PROPOSED`

**Summary:** When running the full pipeline, allow each song's per-track video to use a different `video_style` filter (e.g. `bw`, `vintage`, `warm`, `cool`, `golden`) so outputs are visually distinct within a mix.

**Motivation:** FEAT-012 added global `--video-style` but it applies uniformly to every output. When producing a multi-song mix for YouTube, giving each song a unique look helps viewers identify tracks and makes the overall mix more engaging.

**Proposed Behaviour:**
- The existing `--video-style` global flag remains the default and fallback.
- Users may configure per-track styles via `montage_config.yaml`:
  ```yaml
  pipeline:
    track_styles:
      track1.wav: vintage
      track2.wav: bw
      track3.wav: warm
  ```
  Or via a future `--track-styles` CLI flag (JSON/CSV form).
- If a per-track style is set, it overrides the global `video_style` for that track's `PacingConfig` at pipeline build time.
- The mix video continues to use the global style (or `none` by default).
- Shorts inherit the style of their source track.

**Scope:** `src/pipeline.py`, `src/core/models.py` (`PacingConfig`), `montage_config.yaml` schema, CLI docs.

---

## FEAT-032 — Native Folder Picker in Streamlit UI

**Status:** `IMPLEMENTED`

**Summary:** Update the Streamlit UI to include a native file/folder picker allowing users to select input and output directories via a graphical file browser rather than manually typing paths.

**Motivation:** Manually typing or pasting system paths for audio, video, and output directories is error-prone and tedious. A graphical folder picker provides a more intuitive, familiar, and desktop-like experience, significantly reducing friction for users.

**Proposed Behaviour:**
- Add "Select Folder" buttons next to the directory input fields in the Streamlit UI.
- When clicked, the button launches a system-native folder selection dialog (using `tkinter.filedialog` or similar since this runs locally).
- The selected path automatically populates the corresponding input field so the user can review it before executing the pipeline.

**Scope:** `app_ui.py`, potential integration of tkinter or a dedicated streamlit-file-browser extension.

---

## FEAT-033 — Smart B-Roll Insertion with Clip Boundary Respect

**Status:** `PROPOSED`

**Summary:** Improve B-roll clip insertion timing by respecting clip boundaries — wait for the current main clip to finish before switching to a B-roll clip, even if the time threshold has been reached.

**Motivation:** Currently, B-roll clips are inserted at predefined moments (e.g., every 20 seconds), which can cause jarring visual jumps if a main clip hasn't finished playing. By waiting for the current clip to finish naturally, transitions feel smoother and more intentional.

**Proposed Behaviour:**
- Set a B-roll insertion threshold (e.g., `b_roll_interval: 20` seconds in config or CLI flag).
- The system checks if the threshold has been reached, BUT only switches to B-roll once the currently playing main clip finishes.
- This prevents mid-clip switches and ensures smooth, boundary-respecting transitions.
- Example: If threshold is 20 seconds and the current clip ends at 23 seconds, wait until 23 seconds to insert B-roll rather than forcing a switch at the 20-second mark.

**Scope:** `src/core/montage.py` (`MontageGenerator` segment planning logic), `src/core/models.py` (add `b_roll_interval` to `PacingConfig`), `montage_config.yaml` schema.

---

## FEAT-034 — Persistent Status Bar with ETA in Streamlit UI

**Status:** `IMPLEMENTED`

**Summary:** Add a persistent top-level status bar in the Streamlit UI showing real-time progress, stage name, elapsed time, and estimated time remaining (ETA). Replace disappearing logs with a structured status display.

**Motivation:** Currently, log output disappears during long pipeline runs, leaving users uncertain about progress. A persistent status bar provides immediate, at-a-glance visibility into the current operation and how much longer to expect, reducing anxiety during long video renders.

**Proposed Behaviour:**
- Display a sticky header or sidebar status card showing:
  - Current stage (e.g., "Analyzing audio...", "Generating montage...", "Rendering video...")
  - Progress bar (0–100%) for current stage
  - Elapsed time (HH:MM:SS)
  - Estimated time remaining (ETA, HH:MM:SS)
  - Overall progress (e.g., "Step 2 of 4")
- Update in real-time as `ProgressObserver` callbacks fire from the pipeline.
- Use Streamlit's `st.status()` container for collapsible detail logs beneath the status bar.
- Log lines appear in the status container; they do not disappear — history is retained for the session.

**Implementation Notes:**
- Timing model: Use stage heuristics (audio analysis ~10%, montage building ~10%, rendering ~70%, export ~10%) as baseline.
- For more accurate ETAs, optionally track run history (per-clip render time, per-stage averages) in a lightweight cache.
- Hook into existing `ProgressObserver` interface; emit stage name and progress % from `BachataSyncEngine.generate()` and sub-stages.

**Scope:** `app_ui.py` (status bar layout, ETA calculation), `src/ui/console.py` (optional: factor out timing/stage logic into a shared `ProgressTracker` class), `src/core/app.py` (emit finer-grained progress with stage names).


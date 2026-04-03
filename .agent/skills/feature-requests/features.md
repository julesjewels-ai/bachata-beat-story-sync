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

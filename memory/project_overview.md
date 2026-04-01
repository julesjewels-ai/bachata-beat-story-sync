---
name: Project Overview — Bachata Beat-Story Sync
description: Core purpose, architecture, entry points, and pipeline structure of this Python video-editing automation tool
type: project
---

Automated video editor that synchronises bachata/Latin dance footage to music using beat detection (librosa) and FFmpeg rendering.

**Why:** YouTube content creation tool for dance videography — generates full-length music videos and YouTube Shorts from a folder of raw clips + audio tracks.

**How to apply:** When working on features, understand the three entry points and their shared `BachataSyncEngine` core:
- `main.py` → single audio + clips → one output video
- `src/pipeline.py` → folder of audio tracks → mix video + per-track videos + shorts batch
- `src/shorts_maker.py` → single/folder audio → batch of vertical 9:16 Shorts

**Architecture layers:**
1. `src/core/audio_analyzer.py` — librosa BPM/beat/intensity extraction + section detection
2. `src/core/video_analyzer.py` — OpenCV clip analysis (intensity score, scene changes, opening intensity)
3. `src/core/montage.py` (MontageGenerator) — pure Python segment planner (beat → clip matching)
4. `src/core/ffmpeg_renderer.py` — FFmpeg subprocess orchestration (extract, concat, transitions, audio overlay)
5. `src/core/audio_mixer.py` — multi-track WAV mixing with BPM tempo sync (atempo filter)
6. `src/services/` — reporting (Excel, plan markdown, JSON output)
7. `src/ui/console.py` — Rich-based progress observer + PipelineLogger

**Config:** `montage_config.yaml` at project root; `PacingConfig` Pydantic model; genre presets in `src/core/genre_presets.py` (bachata, salsa, reggaeton, kizomba, merengue, pop).

**Key models:** `AudioAnalysisResult`, `VideoAnalysisResult`, `SegmentPlan`, `PacingConfig`, `AudioMixConfig` — all in `src/core/models.py`.

**Tooling:** Python 3.13, uv, ruff, mypy, pytest. `make install / run / full-pipeline / test / lint`.

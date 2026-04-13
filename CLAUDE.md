# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Guidelines

- When the user asks to check or verify something simple, answer directly first before doing broad searches or exploration.

# Project Overview

This is a Python video production automation tool that syncs dance video clips to musical beats and intensity. It uses MoviePy v2 — ensure all code changes are compatible with the MoviePy v2 API (not v1). When in doubt, check the installed version before making assumptions about method signatures or class interfaces.

FFmpeg is used directly (via `src/core/ffmpeg_renderer.py` and `src/core/ffmpeg_utils.py`) for all actual rendering — MoviePy is used for clip manipulation only.

This project uses Streamlit for the UI. Always check for existing code before suggesting new frameworks or building from scratch.

# Commands

```bash
# Install (uses uv with Python 3.13 venv)
make install

# Run main story video generator
make run AUDIO=path/to/track.wav VIDEO_DIR=path/to/clips/

# Run the web UI (Streamlit)
make ui

# Run full pipeline (mix + per-track videos + shorts)
make full-pipeline AUDIO=path/to/audio_folder/ VIDEO_DIR=path/to/clips/

# Generate YouTube Shorts only
make run-shorts AUDIO=path/to/track.wav VIDEO_DIR=path/to/clips/

# Start MCP server (stdio transport for Claude Desktop / AI agents)
make mcp-serve

# Test, lint, type-check
make test
make lint
make format
make check-types

# Single test file
venv/bin/pytest tests/unit/test_montage.py -v

# Quick iteration with limits
make run AUDIO=track.wav VIDEO_DIR=clips/ TEST_MODE=1
make run AUDIO=track.wav VIDEO_DIR=clips/ MAX_CLIPS=5 MAX_DURATION=30

# Dry-run (plan without rendering)
make run AUDIO=track.wav VIDEO_DIR=clips/ DRY_RUN=1
```

# Architecture

## Entry Points

- **`main.py`** — single track → one story video. Accepts `--audio` (WAV) and `--video-dir`.
- **`src/pipeline.py`** — full batch pipeline: mixes a folder of audio tracks, generates a mix video, per-track videos, and YouTube Shorts.
- **`src/shorts_maker.py`** — standalone Shorts generator.
- **`mcp_server.py`** — MCP server exposing the pipeline as tools/resources for AI agents.

## Core Data Flow

```
AudioAnalyzer → AudioAnalysisResult (BPM, peaks, beat_times, sections, intensity_curve)
VideoAnalyzer → VideoAnalysisResult (intensity_score, scene_changes, opening_intensity)
         ↓
MontageGenerator.build_segment_plan() → [SegmentPlan]   # dry-run / planning
MontageGenerator.generate()           → output.mp4       # full render via FFmpeg
```

## Module Map (`src/`)

| Module | Responsibility |
|---|---|
| `core/app.py` | `BachataSyncEngine` — top-level facade; scan library, plan, generate |
| `core/montage.py` | `MontageGenerator` — clip selection, pacing, B-roll scheduling, segment plan |
| `core/audio_analyzer.py` | `AudioAnalyzer` — BPM, beat tracking, peaks, sections via librosa |
| `core/video_analyzer.py` | `VideoAnalyzer` — intensity score, scene changes via OpenCV |
| `core/ffmpeg_renderer.py` | FFmpeg wrappers: extract segments, concatenate, transitions, audio overlay |
| `core/ffmpeg_utils.py` | Low-level FFmpeg filter helpers (color grades, effects, interpolation) |
| `core/audio_mixer.py` | Mixes multiple audio files with crossfade and optional BPM tempo sync |
| `core/models.py` | Pydantic DTOs: `AudioAnalysisResult`, `VideoAnalysisResult`, `SegmentPlan`, `PacingConfig`, `AudioMixConfig` |
| `core/genre_presets.py` | Genre-specific `PacingConfig` overrides (bachata, salsa, reggaeton, etc.) |
| `core/validation.py` | Input validation helpers |
| `core/interfaces.py` | `ProgressObserver` ABC |
| `services/reporting/` | Excel report generation |
| `services/plan_report.py` | Dry-run Markdown plan report |
| `services/json_output.py` | Structured JSON output (FEAT-028) |
| `ui/console.py` | `RichProgressObserver`, `PipelineLogger` — Rich-based terminal UI |
| `cli_utils.py` | Shared CLI argument builders and helpers used by all three entry points |

## Configuration

`montage_config.yaml` at the project root is the primary configuration file. It maps to `PacingConfig` and `AudioMixConfig` (both in `src/core/models.py`). CLI flags always override YAML values. Key knobs:

- `pacing.genre` — applies a genre preset before other values
- `pacing.video_style` — color grade: `none`, `bw`, `vintage`, `warm`, `cool`, `golden`
- `pacing.transition_type` — FFmpeg xfade: `none`, `fade`, `wipeleft`, etc.
- `pacing.intro_effect` — `none`, `bloom`, `vignette_breathe` (first segment only)
- `pacing.dry_run` — plan without rendering

## Dependencies

Always add new dependencies to the project's build system (`pyproject.toml`/`setup.cfg`/`requirements.txt`) when introducing them, not just pip installing locally. This ensures the dependency is tracked for reproducibility and future installations.

## Debugging

For bug reports, investigate the actual error first: check logs, examine tracebacks, identify thread crashes, and gather concrete evidence before assuming UI-level or environmental issues.

## Workflow Conventions

When implementing features, complete the full implementation before moving on. If a session may be interrupted, prioritize getting working code committed over extensive planning.

## Workflow

After any refactoring or bug fix, always run the existing test suite before considering the task complete:

```bash
make test
```

## Refactoring Guidelines

When refactoring, prefer incremental decomposition:

1. Extract one module, class, or function at a time
2. Run tests after each extraction
3. Only proceed to the next extraction if tests pass
4. Summarise architectural changes made at the end

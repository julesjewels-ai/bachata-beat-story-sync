# Feature Archive — Bachata Beat-Story Sync

> Completed features. Full specs removed to reduce context. See git history for original details.

| Feature | Name | Status | Summary |
|---------|------|--------|---------|
| FEAT-001 | Variable Clip Duration Based on Intensity | `IMPLEMENTED` | Time-based clip durations tied to audio intensity (high→2.5s, med→4s, low→6s) |
| FEAT-002 | Speed Ramping (Slow-Mo / Fast-Forward) | `IMPLEMENTED` | Speed effects on clips based on audio intensity |
| FEAT-003 | Musical Section Awareness | `IMPLEMENTED` | Detect intro/verse/chorus/breakdown/outro from audio |
| FEAT-004 | Beat-Snap Transitions | `IMPLEMENTED` | Align transitions to beat timestamps |
| FEAT-005 | Test Mode (Quick Iteration) | `IMPLEMENTED` | `--test-mode` caps to 4 clips / 10s |
| FEAT-006 | Clip Variety & Start Offset | `IMPLEMENTED` | Randomised start offsets for reused clips |
| FEAT-007 | Multi-Track Folder Input | `IMPLEMENTED` | Folder of audio tracks → concatenated mix |
| FEAT-008 | Specific Clip Prefix Ordering | `VERIFIED` | `1_intro.mp4` prefix forces clip order |
| FEAT-009 | Visual Intensity Matching | `VERIFIED` | Pool-based clip selection matching audio energy |
| FEAT-010 | Smooth Slow Motion Interpolation | `IMPLEMENTED` | Frame interpolation via `minterpolate` for slowed clips |
| FEAT-011 | Intermittent B-Roll Insertion | `VERIFIED` | Auto-interleave B-roll every 12–15s |
| FEAT-012 | Video Style Filters | `IMPLEMENTED` | `--video-style` (bw, vintage, warm, cool) |
| FEAT-013 | Music-Synced Waveform Overlay | `IMPLEMENTED` | `--audio-overlay` (waveform, bars) |
| FEAT-014 | Full Pipeline Orchestrator | `IMPLEMENTED` | `pipeline.py` — mix + per-track videos |
| FEAT-015 | Pipeline Shorts Integration | `IMPLEMENTED` | `--shorts-count` in pipeline |
| FEAT-016 | Shared Scan Optimization | `IMPLEMENTED` | `--shared-scan` skips re-scanning per track |
| FEAT-017 | Per-Track Intro Variety | `DONE` | Rotates prefix clips across pipeline tracks |
| FEAT-018 | CLI Logging & UX System | `IMPLEMENTED` | Rich-based `PipelineLogger` with spinners/panels |
| FEAT-019 | Audio Hook Detection | `IMPLEMENTED` | `--smart-start` scores candidate start positions for shorts |
| FEAT-020 | Visual Scene-Change Detection | `IMPLEMENTED` | `scene_changes` + `opening_intensity` on clips; scene-aware start offsets |
| FEAT-021 | Waveform Overlay Padding / Margins | `VERIFIED` | `--audio-overlay-padding` (px from screen edge, default 10); flows through `PacingConfig` → `ffmpeg_renderer` |
| FEAT-022 | Intro Visual Effects | `IMPLEMENTED` | `--intro-effect` (bloom, vignette_breathe) |
| FEAT-023 | Pacing Visual Effects | `IMPLEMENTED` | `--pacing-drift-zoom`, `--pacing-crop-tighten`, `--pacing-saturation-pulse`; sustained cinematic motion effects applied per-segment via `_build_pacing_filters()` |
| FEAT-024 | Advanced Beat-Synced Effects | `IMPLEMENTED` | `--pacing-micro-jitters`, `--pacing-light-leaks`, `--pacing-warm-wash`, `--pacing-alternating-bokeh`; beat-synced visual effects using `_beats_to_expression()` helper |
| FEAT-025 | Decision Explainability Log | `DONE` | `--explain` outputs timestamped decision log |
| FEAT-026 | Dry-Run Plan Mode | `DONE` | `--dry-run` previews segment plan without rendering |
| FEAT-027 | Genre Preset System | `DONE` | `--genre` (bachata, salsa, reggaeton, kizomba, merengue, pop) |
| FEAT-028 | Structured JSON Output | `IMPLEMENTED` | `--output-json` emits analysis + plan as JSON |
| FEAT-029 | File Watcher | `DONE` | `--watch` monitors inputs and auto-re-renders |
| FEAT-030 | Per-Track Video Clip Pools | `IMPLEMENTED` | `pipeline.track_clips` YAML config allows per-song clip folders + fallback to global |
| FEAT-031 | Per-Track Video Style Filter | `IMPLEMENTED` | `pipeline.track_styles` YAML config per-song `video_style` overrides |
| FEAT-032 | Native Folder Picker in Streamlit UI | `IMPLEMENTED` | `tkinter.filedialog` integration for audio/video dir selection |
| FEAT-033 | Smart B-Roll Insertion with Clip Boundary Respect | `IMPLEMENTED` | `b_roll_interval` config respects clip boundaries; seamless insertion logic |
| FEAT-034 | Persistent Status Bar with ETA in Streamlit UI | `IMPLEMENTED` | Real-time progress bar, elapsed time, ETA, stage names in sticky header |
| FEAT-035 | Streamlit UI Folder Picker & Status Bar Polish | `IMPLEMENTED` | Native picker buttons (📁) for audio/video/output paths; improved visual hierarchy with emojis; collapsible log details; reorganized sidebar sections |
| FEAT-036 | Organic Per-Beat Speed Ramping | `IMPLEMENTED` | Dynamic per-beat speed variation driven by intensity curve; `speed_ramp_organic`, `speed_ramp_curve`, `speed_ramp_sensitivity` config; via FFmpeg `setpts` filter |
| FEAT-037 | Streamlit File Upload (Audio & Video) | `IMPLEMENTED` | `st.file_uploader()` for audio (WAV/MP3) and video clips; temp file storage; drag-and-drop UX; enables cloud deployment without local paths |
| FEAT-041 | Demo Mode | `IMPLEMENTED` | One-click demo using bundled sample assets (`demo/audio/`, `demo/clips/`); "Run Full Demo" and "Quick Preview" buttons; auto-wires paths, limits to 6 clips/20s, renders to temp file; `make download-demo` fetches assets; `demo_assets_available()` gating in `src/ui/inputs.py`; `SessionState.demo_mode` flag; Streamlit-cached clip scanning via `src/ui/video_cache.py` |

"""
Bachata Beat-Story Sync — Streamlit UI wrapper.

A simple web interface for non-technical users to run the CLI tool
without touching the terminal.

Usage:
    streamlit run app_ui.py
"""

from __future__ import annotations

import logging
import os
import queue
import tempfile
import threading
import time

import streamlit as st
from src.adapters.backend import get_genres, get_intro_effects
from src.state.session import SessionState
from src.ui.inputs import (
    DEMO_AUDIO,
    DEMO_CLIPS,
    audio_input_component,
    broll_input_component,
    demo_assets_available,
    output_input_component,
    video_input_component,
)
from src.ui.theme import apply_theme
from src.workers.progress import (
    ProgressTracker,
    QueueLogHandler,
    QueueProgressObserver,
)

# ---------------------------------------------------------------------------
# Page config must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Bachata Beat-Story Sync",
    page_icon="🎵",
    layout="wide",
)

# Apply Precision Gate design system
apply_theme()

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
state = SessionState()

# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def _is_deployed() -> bool:
    """Check if running on Streamlit Cloud or hosted environment."""
    return bool(os.getenv("STREAMLIT_RUNTIME_ENV", ""))


# ---------------------------------------------------------------------------
# Page state helpers
# ---------------------------------------------------------------------------

_show_welcome = (
    not state.demo_mode
    and not state.is_running
    and not state.result_path
    and not state.plan_report
    and not state.error
)

_controls_disabled = state.is_running

# ---------------------------------------------------------------------------
# UI — Header (conditional: hero vs compact bar)
# ---------------------------------------------------------------------------

if _show_welcome:
    # ── HERO BLOCK ────────────────────────────────────────────
    st.markdown(
        """
        <div style="
            background: #2A2A2A;
            border-radius: 28px;
            padding: 3.5rem 3rem 3rem 3rem;
            text-align: center;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(253,184,51,0.2);
            box-shadow: 0 16px 64px rgba(0,0,0,0.18);
        ">
            <p style="
                font-family:'IBM Plex Mono',monospace;
                font-size:0.72rem;
                letter-spacing:3.5px;
                color:#FDB833;
                text-transform:uppercase;
                margin:0 0 1rem 0;
            ">BEAT-SYNCED VIDEO AUTOMATION</p>
            <h1 style="
                font-family:'Space Grotesk',sans-serif;
                font-size:2.8rem;
                font-weight:700;
                color:#F5F5F5;
                margin:0 0 0.65rem 0;
                letter-spacing:-1.5px;
                line-height:1.1;
            ">Bachata Beat-Story Sync</h1>
            <p style="
                font-family:'DM Serif Display',serif;
                font-style:italic;
                font-size:1.25rem;
                color:rgba(245,245,245,0.65);
                margin:0 0 2.5rem 0;
                line-height:1.4;
            ">Beat-Synced in Seconds. Professional Montages in Minutes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Hero CTA buttons ───────────────────────────────────────
    _, col_cta, _ = st.columns([1, 2, 1])
    with col_cta:
        demo_full_clicked = st.button(
            "▶  Try the Demo — Free",
            type="primary",
            use_container_width=True,
            key="hero_demo_btn",
            help="Run the tool with built-in sample clips and audio (~2 min).",
        )
        demo_preview_clicked = st.button(
            "Quick Dry-Run Preview (10s)",
            type="secondary",
            use_container_width=True,
            key="hero_preview_btn",
            help="See the beat-sync plan instantly — no video rendering.",
        )

    if demo_full_clicked or demo_preview_clicked:
        if not demo_assets_available():
            st.error(
                "Demo assets not found. Run `make download-demo` and add "
                "sample files to `demo/audio/` and `demo/clips/`. "
                "See `demo/README.md` for details."
            )
            st.stop()
        state.demo_mode = True
        st.session_state["_demo_dry_run"] = demo_preview_clicked
        st.rerun()

else:
    demo_full_clicked = False
    demo_preview_clicked = False

    # ── Compact header bar ─────────────────────────────────────
    col_brand, col_badge, col_exit_hdr = st.columns([2, 4, 1])
    with col_brand:
        st.markdown(
            '<span style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;'
            'font-size:1.1rem;color:#2A2A2A;letter-spacing:-0.5px;">BBS</span>',
            unsafe_allow_html=True,
        )
    with col_badge:
        if state.is_running and state.demo_mode:
            badge_label = "● DEMO — PROCESSING"
        elif state.is_running:
            badge_label = "● PROCESSING"
        elif state.demo_mode:
            badge_label = "● DEMO MODE"
        elif state.result_path:
            badge_label = "● RESULT READY"
        elif state.plan_report:
            badge_label = "● PLAN READY"
        elif state.error:
            badge_label = "● ERROR"
        else:
            badge_label = ""
        if badge_label:
            st.markdown(
                f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.72rem;'
                f'letter-spacing:2.5px;color:#FDB833;text-transform:uppercase;">'
                f"{badge_label}</span>",
                unsafe_allow_html=True,
            )
    with col_exit_hdr:
        if state.demo_mode and not state.is_running:
            if st.button("Exit Demo", key="hdr_exit_demo", type="secondary"):
                state.demo_mode = False
                st.session_state.pop("_demo_dry_run", None)
                state.clear_results()
                st.rerun()

    st.markdown("<hr style='margin:0.5rem 0 1rem 0;border-color:rgba(253,184,51,0.2);'>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Progress & Status
# ---------------------------------------------------------------------------

@st.fragment(run_every=1.0)
def _progress_fragment() -> None:
    """Poll the log queue and render progress — reruns independently of the page."""
    _state = SessionState()
    if not _state.is_running:
        return

    log_queue: queue.Queue = _state.log_queue
    tracker: ProgressTracker = _state.progress_tracker

    if tracker.start_time is None:
        tracker.start()

    done = False
    while True:
        try:
            line = log_queue.get_nowait()
        except queue.Empty:
            break

        if line.startswith("__DONE__"):
            done = True
        elif line.startswith("__RESULT__"):
            _state.result_path = line[len("__RESULT__"):]
        elif line.startswith("__ERROR__"):
            _state.error = line[len("__ERROR__"):]
        elif line.startswith("__PLAN_REPORT__"):
            _state.plan_report = line[len("__PLAN_REPORT__"):]
        else:
            _state.log_lines.append(line)
            tracker.update(line)

    if done:
        _state.is_running = False
        st.rerun()

    # Derive approximate progress %
    stage_keys = list(tracker.STAGE_HEURISTICS.keys())
    current_idx = stage_keys.index(tracker.current_stage) if tracker.current_stage in stage_keys else 0
    cumulative = sum(tracker.STAGE_HEURISTICS[k] for k in stage_keys[:current_idx])
    current_weight = tracker.STAGE_HEURISTICS.get(tracker.current_stage, 10)
    progress_value = min((cumulative + current_weight * 0.5) / 100.0, 0.97)

    stage_text = (tracker.current_stage or "INITIALIZING").upper()
    status_container = st.status(
        f"PROCESSING  ·  {stage_text}",
        expanded=True,
        state="running",
    )
    with status_container:
        st.progress(progress_value)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Elapsed", tracker.elapsed_str())
        with col2:
            st.metric("ETA", tracker.estimate_eta_str())
        with col3:
            st.metric("Stage", tracker.current_stage or "initializing")

        st.divider()

        with st.expander("SYSTEM LOG", expanded=False):
            recent = _state.log_lines[-25:] if len(_state.log_lines) > 25 else _state.log_lines
            st.text_area(
                "log",
                value="\n".join(recent),
                height=180,
                disabled=True,
                label_visibility="collapsed",
            )


_progress_fragment()

# ---------------------------------------------------------------------------
# Result & errors
# ---------------------------------------------------------------------------

if state.error and not state.is_running:
    st.markdown(
        '<div style="border-left:4px solid #FDB833;padding:0.9rem 1.2rem;'
        'background:rgba(253,184,51,0.07);border-radius:0 12px 12px 0;margin-bottom:1rem;">'
        '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;'
        'letter-spacing:2px;color:#FDB833;text-transform:uppercase;">GENERATION FAILED</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Error details", expanded=True):
        st.code(state.error, language="python")

if state.result_path and not state.is_running:
    result = state.result_path
    # Result label
    result_label = "RESULT — BEAT-SYNCED DEMO" if state.demo_mode else "RESULT — MONTAGE READY"
    st.markdown(
        f'<p style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;'
        f'letter-spacing:3px;color:#FDB833;text-transform:uppercase;margin-bottom:0.75rem;">'
        f"{result_label}</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        if os.path.exists(result):
            st.video(result)
        else:
            st.warning("Output file not found at the reported path.")

        if state.demo_mode:
            col_again, col_try = st.columns(2)
            with col_again:
                if st.button("Run Demo Again", type="secondary", use_container_width=True, key="demo_again_btn"):
                    state.clear_results()
                    st.session_state["_demo_dry_run"] = False
                    st.rerun()
            with col_try:
                if st.button("▶  Try Your Own Clips", type="primary", use_container_width=True, key="try_own_btn"):
                    state.demo_mode = False
                    st.session_state.pop("_demo_dry_run", None)
                    state.clear_results()
                    st.rerun()
        else:
            st.caption(f"Saved to: {result}")

# ---------------------------------------------------------------------------
# Plan report (dry-run)
# ---------------------------------------------------------------------------

if state.plan_report and not state.is_running:
    st.markdown(
        '<p style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;'
        'letter-spacing:3px;color:#FDB833;text-transform:uppercase;margin-bottom:0.75rem;">'
        "SEGMENT PLAN — DRY RUN COMPLETE</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.code(st.session_state.get("plan_report", state.plan_report), language="")

    if state.demo_mode:
        col_again2, col_try2 = st.columns(2)
        with col_again2:
            if st.button("Run Full Demo", type="secondary", use_container_width=True, key="plan_demo_again"):
                state.clear_results()
                st.session_state["_demo_dry_run"] = False
                st.rerun()
        with col_try2:
            if st.button("▶  Try Your Own Clips", type="primary", use_container_width=True, key="plan_try_own"):
                state.demo_mode = False
                st.session_state.pop("_demo_dry_run", None)
                state.clear_results()
                st.rerun()

# ---------------------------------------------------------------------------
# "How It Works" — three callout cards (welcome state only)
# ---------------------------------------------------------------------------

if _show_welcome:
    st.markdown(
        '<p style="font-family:\'IBM Plex Mono\',monospace;font-size:0.68rem;'
        'letter-spacing:3px;color:#888888;text-transform:uppercase;margin:2rem 0 0.75rem 0;">'
        "HOW IT WORKS</p>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="pg-callout">'
            '<strong style="font-family:\'IBM Plex Mono\',monospace;font-size:0.75rem;'
            'letter-spacing:1.5px;color:#FDB833;">01 — UPLOAD</strong><br>'
            '<span style="font-family:\'Space Grotesk\',sans-serif;font-size:0.9rem;">'
            "Drop your dance clips and a bachata track.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="pg-callout">'
            '<strong style="font-family:\'IBM Plex Mono\',monospace;font-size:0.75rem;'
            'letter-spacing:1.5px;color:#FDB833;">02 — ANALYSE</strong><br>'
            '<span style="font-family:\'Space Grotesk\',sans-serif;font-size:0.9rem;">'
            "We detect every beat, swell and intensity peak.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="pg-callout">'
            '<strong style="font-family:\'IBM Plex Mono\',monospace;font-size:0.75rem;'
            'letter-spacing:1.5px;color:#FDB833;">03 — EXPORT</strong><br>'
            '<span style="font-family:\'Space Grotesk\',sans-serif;font-size:0.9rem;">'
            "Download a frame-accurate synced montage video.</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<p style="font-family:\'IBM Plex Mono\',monospace;font-size:0.68rem;'
        'letter-spacing:3px;color:#888888;text-transform:uppercase;margin:2rem 0 0.75rem 0;">'
        "OR UPLOAD YOUR OWN FOOTAGE</p>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Input components
# ---------------------------------------------------------------------------

is_deployed = _is_deployed()

if not state.demo_mode:
    col_audio, col_video = st.columns(2)
    with col_audio:
        audio_path_text = audio_input_component(state, is_deployed, disabled=_controls_disabled)
    with col_video:
        video_dir = video_input_component(state, is_deployed, disabled=_controls_disabled)
else:
    # Demo mode — show demo asset info (broll/output not needed)
    audio_path_text = audio_input_component(state, is_deployed, disabled=_controls_disabled)
    video_dir = video_input_component(state, is_deployed, disabled=_controls_disabled)
    broll_dir_input = ""
    output_path = ""

# ---------------------------------------------------------------------------
# Advanced Settings expander (normal mode only)
# ---------------------------------------------------------------------------

if not state.demo_mode:
    with st.expander("Advanced Settings — Visual Style, Effects & Limits", expanded=False):
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown(
                '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.68rem;'
                'letter-spacing:2px;color:#FDB833;text-transform:uppercase;">Visual Style</span>',
                unsafe_allow_html=True,
            )
            genre_options = get_genres()
            genre_choice = st.selectbox(
                "Genre preset",
                options=genre_options,
                help="Applies tuned clip pacing, colour grade and transitions for a genre.",
                disabled=_controls_disabled,
            )
            video_style = st.selectbox(
                "Colour grade",
                options=["none", "bw", "vintage", "warm", "cool", "golden"],
                help="Colour grading applied to every segment.",
                disabled=_controls_disabled,
            )
            transition_type = st.text_input(
                "Transition type",
                value="none",
                help="FFmpeg xfade: none, fade, wipeleft, wiperight, slideup, …",
                disabled=_controls_disabled,
            )
            intro_effects_options = get_intro_effects()
            intro_effect = st.selectbox(
                "Intro effect",
                options=intro_effects_options,
                help="Visual effect applied to the very first clip.",
                disabled=_controls_disabled,
            )

        with col_s2:
            st.markdown(
                '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.68rem;'
                'letter-spacing:2px;color:#FDB833;text-transform:uppercase;">Limits & Output</span>',
                unsafe_allow_html=True,
            )
            test_mode = st.checkbox(
                "Test mode (4 clips, 10s)",
                value=False,
                help="Restrict to 4 clips and 10s — good for quick checks.",
                disabled=_controls_disabled,
            )
            max_clips_input = st.number_input(
                "Max clips (0 = unlimited)",
                min_value=0,
                value=0,
                step=1,
                disabled=_controls_disabled,
            )
            max_duration_input = st.number_input(
                "Max duration in seconds (0 = unlimited)",
                min_value=0,
                value=0,
                step=5,
                disabled=_controls_disabled,
            )
            dry_run = st.checkbox(
                "Dry run (plan only, no render)",
                value=False,
                help="Analyse and plan without rendering.",
                disabled=_controls_disabled,
            )
            export_report = st.checkbox(
                "Export Excel report",
                value=False,
                help="Generate analysis.xlsx alongside video.",
                disabled=_controls_disabled,
            )

        st.markdown(
            '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.68rem;'
            'letter-spacing:2px;color:#FDB833;text-transform:uppercase;">B-roll & Output</span>',
            unsafe_allow_html=True,
        )
        broll_dir_input = broll_input_component(state, is_deployed, disabled=_controls_disabled)
        output_path = output_input_component(state, is_deployed, disabled=_controls_disabled)

        st.markdown(
            '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.68rem;'
            'letter-spacing:2px;color:#FDB833;text-transform:uppercase;">Advanced Effects</span>',
            unsafe_allow_html=True,
        )
        st.markdown("**Speed Ramping**")
        speed_ramp_organic = st.checkbox(
            "Organic per-beat speed",
            value=False,
            help="Variable speed within clips driven by beat-by-beat intensity.",
            disabled=_controls_disabled,
        )
        if speed_ramp_organic:
            speed_ramp_sensitivity = st.slider(
                "Sensitivity",
                min_value=0.3,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="0.5=gentle, 1.0=standard, 2.0=aggressive",
                disabled=_controls_disabled,
            )
            speed_ramp_curve = st.selectbox(
                "Curve type",
                options=["linear", "ease_in", "ease_out", "ease_in_out"],
                help="Smoothing function for speed transitions",
                disabled=_controls_disabled,
            )
            col_speed_min, col_speed_max = st.columns(2)
            with col_speed_min:
                speed_ramp_min = st.number_input(
                    "Min speed",
                    min_value=0.3,
                    max_value=1.0,
                    value=0.8,
                    step=0.1,
                    help="Slowest multiplier (low-energy beats)",
                    disabled=_controls_disabled,
                )
            with col_speed_max:
                speed_ramp_max = st.number_input(
                    "Max speed",
                    min_value=1.0,
                    max_value=2.0,
                    value=1.3,
                    step=0.1,
                    help="Fastest multiplier (high-energy beats)",
                    disabled=_controls_disabled,
                )
        else:
            speed_ramp_sensitivity = 1.0
            speed_ramp_curve = "ease_in_out"
            speed_ramp_min = 0.8
            speed_ramp_max = 1.3

        st.markdown("**Beat-Synced Effects**")
        pacing_drift_zoom = st.checkbox("Drift zoom (Ken Burns)", value=False, disabled=_controls_disabled)
        pacing_crop_tighten = st.checkbox("Crop tighten", value=False, disabled=_controls_disabled)
        pacing_saturation_pulse = st.checkbox("Saturation pulse on beats", value=False, disabled=_controls_disabled)
        pacing_micro_jitters = st.checkbox("Micro-jitters on beats", value=False, disabled=_controls_disabled)
        pacing_light_leaks = st.checkbox("Light leaks on beats", value=False, disabled=_controls_disabled)
        pacing_warm_wash = st.checkbox("Warm wash at transitions", value=False, disabled=_controls_disabled)
        pacing_alternating_bokeh = st.checkbox("Alternating bokeh blur", value=False, disabled=_controls_disabled)

else:
    # Demo mode — all settings at their defaults (not exposed in UI)
    genre_options = []
    genre_choice = "(none)"
    video_style = "none"
    transition_type = "none"
    intro_effects_options = []
    intro_effect = "none"
    test_mode = False
    max_clips_input = 0
    max_duration_input = 0
    dry_run = False
    export_report = False
    speed_ramp_organic = False
    speed_ramp_sensitivity = 1.0
    speed_ramp_curve = "ease_in_out"
    speed_ramp_min = 0.8
    speed_ramp_max = 1.3
    pacing_drift_zoom = False
    pacing_crop_tighten = False
    pacing_saturation_pulse = False
    pacing_micro_jitters = False
    pacing_light_leaks = False
    pacing_warm_wash = False
    pacing_alternating_bokeh = False

# ---------------------------------------------------------------------------
# Run / Cancel button
# ---------------------------------------------------------------------------

if not state.demo_mode and not state.result_path and not state.plan_report:
    st.markdown("---")
    col_spacer1, col_run, col_spacer2 = st.columns([1.5, 2, 1.5])
    with col_run:
        if state.is_running:
            run_button = False
            if st.button(
                "Cancel",
                type="secondary",
                use_container_width=True,
                help="Stop the current processing run.",
            ):
                state.is_running = False
                state.error = "Run cancelled by user."
                st.rerun()
        else:
            run_button = st.button(
                "▶  Generate Montage",
                type="primary",
                use_container_width=True,
                help=(
                    "Process audio and video clips. This may take several minutes "
                    "depending on video length."
                ),
            )
else:
    run_button = False


# ---------------------------------------------------------------------------
# Background generation thread
# ---------------------------------------------------------------------------

def _run_generation(
    audio_resolved: str,
    video_dir_path: str,
    broll_path: str | None,
    output_video: str,
    pacing_kwargs: dict,
    export_report_path: str | None,
    log_queue: queue.Queue,
) -> None:
    """Run the full engine pipeline in a background thread."""
    import sys
    import traceback as tb_module

    # Attach our queue handler to the root logger for this thread
    handler = QueueLogHandler(log_queue)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    # Also log to stderr for debugging
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    try:
        log_queue.put("DEBUG: Background thread started")
        log_queue.put(f"DEBUG: Audio: {audio_resolved}")
        log_queue.put(f"DEBUG: Video dir: {video_dir_path}")

        log_queue.put("DEBUG: Importing modules…")
        from src.cli_utils import (  # noqa: WPS433
            analyze_audio,
            detect_broll_dir,
            strip_thumbnails,
        )
        from src.core.app import BachataSyncEngine  # noqa: WPS433
        from src.core.models import PacingConfig  # noqa: WPS433
        from src.core.montage import load_pacing_config  # noqa: WPS433
        log_queue.put("DEBUG: Modules imported successfully")

        log_queue.put("DEBUG: Initializing engine…")
        engine = BachataSyncEngine()
        log_queue.put("DEBUG: Engine initialized")

        # 1. Analyse audio
        log_queue.put("[1/4] Analysing audio…")
        resolved_audio, audio_meta = analyze_audio(audio_resolved)

        # 2. Scan video library
        log_queue.put(f"[2/4] Scanning video clips in {video_dir_path}")
        broll_dir_resolved = detect_broll_dir(video_dir_path, broll_path)
        exclude_dirs = [broll_dir_resolved] if broll_dir_resolved else None

        obs = QueueProgressObserver(log_queue)
        video_clips = engine.scan_video_library(
            video_dir_path, exclude_dirs=exclude_dirs, observer=obs
        )
        log_queue.put(f"   → Found {len(video_clips)} clip(s)")

        broll_clips = None
        if broll_dir_resolved and os.path.exists(broll_dir_resolved):
            log_queue.put(f"   → Scanning B-roll in {broll_dir_resolved}")
            broll_clips = engine.scan_video_library(
                broll_dir_resolved, observer=obs
            )
            log_queue.put(f"   → Found {len(broll_clips)} B-roll clip(s)")

        # 3. Build pacing config
        log_queue.put("[3/4] Configuring pacing and effects…")
        base_config = load_pacing_config()
        merged = {**base_config.model_dump(), **pacing_kwargs}
        pacing = PacingConfig(**merged)

        montage_clips = strip_thumbnails(video_clips)

        # 4a. Dry-run path
        if pacing.dry_run:
            log_queue.put("[3/4] Planning segment timeline…")
            from src.services.plan_report import format_plan_report  # noqa: WPS433
            segments = engine.plan_story(audio_meta, montage_clips, pacing=pacing)
            report = format_plan_report(audio_meta, segments, montage_clips, pacing)
            log_queue.put("__PLAN_REPORT__" + report)
            log_queue.put("✓ Dry-run complete — plan ready (no video rendered)")
            log_queue.put("__DONE__")
            return

        # 4b. Full render
        log_queue.put("[4/4] Rendering montage with FFmpeg…")
        log_queue.put("   → This may take several minutes depending on video length…")
        result_path = engine.generate_story(
            audio_meta,
            montage_clips,
            output_video,
            broll_clips=broll_clips,
            audio_path=resolved_audio,
            observer=obs,
            pacing=pacing,
        )
        del montage_clips

        log_queue.put("✓ Video rendered successfully!")
        log_queue.put(f"   → Saved to: {result_path}")

        # 5. Optional Excel report
        if export_report_path:
            from src.services.reporting import ExcelReportGenerator  # noqa: WPS433
            log_queue.put("   → Generating Excel report…")
            ExcelReportGenerator().generate_report(
                audio_meta, video_clips, export_report_path
            )
            log_queue.put(f"   → Report saved to: {export_report_path}")

        log_queue.put("__RESULT__" + result_path)
        log_queue.put("__DONE__")

    except Exception:  # noqa: BLE001
        error_details = tb_module.format_exc()
        log_queue.put(f"__ERROR__{error_details}")
        sys.stderr.write(f"THREAD ERROR:\n{error_details}\n")
        log_queue.put("__DONE__")
    finally:
        root_logger.removeHandler(handler)
        root_logger.removeHandler(console_handler)


# ---------------------------------------------------------------------------
# Handle Run button press
# ---------------------------------------------------------------------------

# Also trigger run when demo mode was just activated
_demo_triggered = (
    state.demo_mode
    and state.result_path is None
    and state.plan_report is None
    and state.error is None
    and not state.is_running
    and st.session_state.get("_demo_dry_run") is not None
)

if run_button or _demo_triggered:
    # --- Resolve paths (demo mode bypasses uploads) ---
    errors: list[str] = []
    resolved_audio_path: str | None = None
    resolved_video_dir: str | None = None
    temp_audio_file: str | None = None
    temp_video_dir: str | None = None
    broll_dir_resolved: str | None = None

    if state.demo_mode:
        # Demo mode: use bundled assets, skip upload validation
        resolved_audio_path = str(DEMO_AUDIO)
        resolved_video_dir = str(DEMO_CLIPS)
        broll_dir_resolved = None
    else:
        # Normal mode: validate uploads / paths
        uploaded_audio = st.session_state.get("audio_upload")
        uploaded_videos = st.session_state.get("video_upload") or []

        # Resolve audio path (upload overrides text input)
        if uploaded_audio is not None:
            suffix = os.path.splitext(uploaded_audio.name)[1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(uploaded_audio.read())
            tmp.close()
            resolved_audio_path = tmp.name
            temp_audio_file = tmp.name
        elif audio_path_text.strip():
            resolved_audio_path = audio_path_text.strip()
            if not os.path.exists(resolved_audio_path):
                errors.append(f"Audio file not found: {resolved_audio_path}")
        else:
            errors.append("Please provide an audio file path or upload a file.")

        # Resolve video directory (uploads override text input)
        if uploaded_videos:
            temp_video_dir = tempfile.mkdtemp(prefix="bachata_videos_")
            for uploaded_file in uploaded_videos:
                file_path = os.path.join(temp_video_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.read())
            resolved_video_dir = temp_video_dir
        elif video_dir.strip():
            resolved_video_dir = video_dir.strip()
            if not os.path.isdir(resolved_video_dir):
                errors.append(f"Video clips folder not found: {resolved_video_dir}")
        else:
            errors.append(
                "Please upload video files or enter the path to your video "
                "clips folder."
            )

        broll_dir_resolved = broll_dir_input.strip() or None
        if broll_dir_resolved and not os.path.isdir(broll_dir_resolved):
            errors.append(f"B-roll folder not found: {broll_dir_resolved}")

    if errors:
        for err in errors:
            st.error(err)
        st.stop()

    # --- Build pacing kwargs ---
    pacing_kwargs: dict = {}

    if genre_choice != "(none)":
        pacing_kwargs["genre"] = genre_choice

    if video_style != "none":
        pacing_kwargs["video_style"] = video_style

    if transition_type.strip() and transition_type.strip() != "none":
        pacing_kwargs["transition_type"] = transition_type.strip()

    if intro_effect and intro_effect != "none":
        pacing_kwargs["intro_effect"] = intro_effect

    # Demo mode overrides
    if state.demo_mode:
        if st.session_state.get("_demo_dry_run", False):
            pacing_kwargs["dry_run"] = True
        pacing_kwargs["max_clips"] = 6
        pacing_kwargs["max_duration_seconds"] = 20.0
        pacing_kwargs["text_overlay_enabled"] = True
        pacing_kwargs["cold_open_enabled"] = True
        pacing_kwargs["track_artist"] = "Sample Artist"
        pacing_kwargs["track_title"] = "Sample Bachata"
    else:
        if dry_run:
            pacing_kwargs["dry_run"] = True

    # Speed ramping
    if speed_ramp_organic:
        pacing_kwargs["speed_ramp_organic"] = True
        pacing_kwargs["speed_ramp_sensitivity"] = speed_ramp_sensitivity
        pacing_kwargs["speed_ramp_curve"] = speed_ramp_curve
        pacing_kwargs["speed_ramp_min"] = speed_ramp_min
        pacing_kwargs["speed_ramp_max"] = speed_ramp_max

    if pacing_drift_zoom:
        pacing_kwargs["pacing_drift_zoom"] = True
    if pacing_crop_tighten:
        pacing_kwargs["pacing_crop_tighten"] = True
    if pacing_saturation_pulse:
        pacing_kwargs["pacing_saturation_pulse"] = True
    if pacing_micro_jitters:
        pacing_kwargs["pacing_micro_jitters"] = True
    if pacing_light_leaks:
        pacing_kwargs["pacing_light_leaks"] = True
    if pacing_warm_wash:
        pacing_kwargs["pacing_warm_wash"] = True
    if pacing_alternating_bokeh:
        pacing_kwargs["pacing_alternating_bokeh"] = True

    # Test mode / limits (normal mode only)
    if not state.demo_mode:
        effective_max_clips: int | None = None
        effective_max_duration: float | None = None

        if test_mode:
            effective_max_clips = 4
            effective_max_duration = 10.0

        if max_clips_input > 0:
            effective_max_clips = int(max_clips_input)
        if max_duration_input > 0:
            effective_max_duration = float(max_duration_input)

        if effective_max_clips is not None:
            pacing_kwargs["max_clips"] = effective_max_clips
        if effective_max_duration is not None:
            pacing_kwargs["max_duration_seconds"] = effective_max_duration

    # Demo mode: render to temp file
    if state.demo_mode and not pacing_kwargs.get("dry_run"):
        demo_tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix="_demo.mp4", prefix="bachata_"
        )
        demo_tmp.close()
        output_path_resolved = demo_tmp.name
    else:
        output_path_resolved = output_path.strip()

    # Excel report path
    report_path: str | None = None
    if export_report:
        base, _ = os.path.splitext(output_path_resolved)
        report_path = base + "_report.xlsx"

    # Clear the demo trigger flag
    st.session_state.pop("_demo_dry_run", None)

    # Reset session state for this run
    state.is_running = True
    state.log_lines = []
    state.result_path = None
    state.error = None
    state.plan_report = None
    state.log_queue = queue.Queue()
    state.progress_tracker = ProgressTracker()

    # Start background thread
    thread = threading.Thread(
        target=_run_generation,
        args=(
            resolved_audio_path,
            resolved_video_dir,
            broll_dir_resolved,
            output_path_resolved,
            pacing_kwargs,
            report_path,
            state.log_queue,
        ),
        daemon=True,
    )
    thread.start()

    time.sleep(0.1)
    st.rerun()

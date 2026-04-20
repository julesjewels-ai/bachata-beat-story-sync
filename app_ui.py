"""
Bachata Beat-Story Sync — Streamlit UI wrapper.

A simple web interface for non-technical users to run the CLI tool
without touching the terminal.

Usage:
    streamlit run app_ui.py
"""

from __future__ import annotations

import os
import threading
import time

import streamlit as st
from src.application.streamlit_requests import (
    prepare_run_request,
    should_trigger_demo_run,
)
from src.application.streamlit_runner import run_streamlit_generation
from src.state.session import SessionState
from src.ui.inputs import (
    audio_input_component,
    video_input_component,
)
from src.ui.page_sections import (
    render_error_panel,
    render_page_header,
    render_plan_report_panel,
    render_progress_fragment,
    render_result_panel,
    render_welcome_overview,
)
from src.ui.settings_form import render_advanced_settings, render_run_controls
from src.ui.theme import apply_theme

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

render_page_header(state, _show_welcome)
render_progress_fragment()
render_error_panel(state)
render_result_panel(state)
render_plan_report_panel(state)
render_welcome_overview(_show_welcome)

# ---------------------------------------------------------------------------
# Input components
# ---------------------------------------------------------------------------

is_deployed = _is_deployed()

if not state.demo_mode:
    col_audio, col_video = st.columns(2)
    with col_audio:
        audio_path_text = audio_input_component(
            state, is_deployed, disabled=_controls_disabled
        )
    with col_video:
        video_dir = video_input_component(
            state, is_deployed, disabled=_controls_disabled
        )
else:
    # Demo mode — show demo asset info (broll/output not needed)
    audio_path_text = audio_input_component(
        state, is_deployed, disabled=_controls_disabled
    )
    video_dir = video_input_component(state, is_deployed, disabled=_controls_disabled)
    broll_dir_input = ""
    output_path = ""

settings, broll_dir_input, output_path = render_advanced_settings(
    state,
    is_deployed,
    _controls_disabled,
)
run_button = render_run_controls(state)


# ---------------------------------------------------------------------------
# Handle Run button press
# ---------------------------------------------------------------------------

# Also trigger run when demo mode was just activated
_demo_triggered = should_trigger_demo_run(state)

if run_button or _demo_triggered:
    prepared_run, errors = prepare_run_request(
        state,
        settings,
        audio_path_text,
        video_dir,
        broll_dir_input,
        output_path,
    )
    if prepared_run is None:
        for err in errors:
            st.error(err)
        st.stop()

    # Clear the demo trigger flag
    st.session_state.pop("_demo_dry_run", None)

    state.reset_execution()

    # Start background thread
    thread = threading.Thread(
        target=run_streamlit_generation,
        args=(
            prepared_run.audio_path,
            prepared_run.video_dir,
            prepared_run.broll_dir,
            prepared_run.output_path,
            prepared_run.pacing_kwargs,
            prepared_run.report_path,
            state.log_queue,
        ),
        daemon=True,
    )
    thread.start()

    time.sleep(0.1)
    st.rerun()

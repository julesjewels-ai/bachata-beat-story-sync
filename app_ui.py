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


# Apply Terra Design System theme
apply_theme()



# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

# Initialize session state with typed wrapper
state = SessionState()



# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def _is_deployed() -> bool:
    """Check if running on Streamlit Cloud or hosted environment."""
    return bool(os.getenv("STREAMLIT_RUNTIME_ENV", ""))


# ---------------------------------------------------------------------------
# UI — Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Project Settings")
st.sidebar.caption("Bachata Beat-Story")

st.sidebar.markdown("---")

st.sidebar.subheader("🎨 Visual Style")

_sidebar_disabled = state.is_running

genre_options = get_genres()
genre_choice = st.sidebar.selectbox(
    "Genre preset",
    options=genre_options,
    help="Applies tuned clip pacing, colour grade and transitions for a genre.",
    disabled=_sidebar_disabled,
)

video_style = st.sidebar.selectbox(
    "Colour grade",
    options=["none", "bw", "vintage", "warm", "cool", "golden"],
    help="Colour grading applied to every segment.",
    disabled=_sidebar_disabled,
)

transition_type = st.sidebar.text_input(
    "Transition type",
    value="none",
    help="FFmpeg xfade: none, fade, wipeleft, wiperight, slideup, …",
    disabled=_sidebar_disabled,
)

intro_effects_options = get_intro_effects()
intro_effect = st.sidebar.selectbox(
    "Intro effect",
    options=intro_effects_options,
    help="Visual effect applied to the very first clip.",
    disabled=_sidebar_disabled,
)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Limits & Output")

test_mode = st.sidebar.checkbox(
    "🧪 Test mode",
    value=False,
    help="Restrict to 4 clips and 10s — good for quick checks.",
    disabled=_sidebar_disabled,
)

max_clips_input = st.sidebar.number_input(
    "Max clips (0 = unlimited)",
    min_value=0,
    value=0,
    step=1,
    disabled=_sidebar_disabled,
)

max_duration_input = st.sidebar.number_input(
    "Max duration in seconds (0 = unlimited)",
    min_value=0,
    value=0,
    step=5,
    disabled=_sidebar_disabled,
)

dry_run = st.sidebar.checkbox(
    "📋 Dry run (plan only)",
    value=False,
    help="Analyse and plan without rendering.",
    disabled=_sidebar_disabled,
)

export_report = st.sidebar.checkbox(
    "📊 Export Excel report",
    value=False,
    help="Generate analysis.xlsx alongside video.",
    disabled=_sidebar_disabled,
)

st.sidebar.markdown("---")
st.sidebar.subheader("✨ Advanced Effects")

# Speed ramping
st.sidebar.markdown("**Speed Ramping (FEAT-036)**")
speed_ramp_organic = st.sidebar.checkbox(
    "Organic per-beat speed",
    value=False,
    help="Variable speed within clips driven by beat-by-beat intensity "
    "(breathing effect).",
    disabled=_sidebar_disabled,
)
if speed_ramp_organic:
    speed_ramp_sensitivity = st.sidebar.slider(
        "Sensitivity",
        min_value=0.3,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="0.5=gentle, 1.0=standard, 2.0=aggressive",
        disabled=_sidebar_disabled,
    )
    speed_ramp_curve = st.sidebar.selectbox(
        "Curve type",
        options=["linear", "ease_in", "ease_out", "ease_in_out"],
        help="Smoothing function for speed transitions",
        disabled=_sidebar_disabled,
    )
    col_speed_min, col_speed_max = st.sidebar.columns(2)
    with col_speed_min:
        speed_ramp_min = st.number_input(
            "Min speed",
            min_value=0.3,
            max_value=1.0,
            value=0.8,
            step=0.1,
            help="Slowest multiplier (low-energy beats)",
            disabled=_sidebar_disabled,
        )
    with col_speed_max:
        speed_ramp_max = st.number_input(
            "Max speed",
            min_value=1.0,
            max_value=2.0,
            value=1.3,
            step=0.1,
            help="Fastest multiplier (high-energy beats)",
            disabled=_sidebar_disabled,
        )
else:
    speed_ramp_sensitivity = 1.0
    speed_ramp_curve = "ease_in_out"
    speed_ramp_min = 0.8
    speed_ramp_max = 1.3

# Other pacing effects
st.sidebar.markdown("**Beat-Synced Effects**")
pacing_drift_zoom = st.sidebar.checkbox("Drift zoom (Ken Burns)", value=False, disabled=_sidebar_disabled)
pacing_crop_tighten = st.sidebar.checkbox("Crop tighten", value=False, disabled=_sidebar_disabled)
pacing_saturation_pulse = st.sidebar.checkbox("Saturation pulse on beats", value=False, disabled=_sidebar_disabled)
pacing_micro_jitters = st.sidebar.checkbox("Micro-jitters on beats", value=False, disabled=_sidebar_disabled)
pacing_light_leaks = st.sidebar.checkbox("Light leaks on beats", value=False, disabled=_sidebar_disabled)
pacing_warm_wash = st.sidebar.checkbox("Warm wash at transitions", value=False, disabled=_sidebar_disabled)
pacing_alternating_bokeh = st.sidebar.checkbox("Alternating bokeh blur", value=False, disabled=_sidebar_disabled)


# ---------------------------------------------------------------------------
# UI — Main area
# ---------------------------------------------------------------------------

# Header with better branding
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.write("🎵")  # Logo placeholder
with col_title:
    st.markdown("## Beat-Story Sync")
    st.caption(
        "Automatically sync your dance video clips to musical beats and intensity. "
        "Terra uses neural waveform analysis to create organic transitions that "
        "breathe with the music."
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Progress & Status (Prominent Top Placement)
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
        # Trigger a full-page rerun so results section renders
        st.rerun()

    status_container = st.status(
        f"⏳ {tracker.current_stage or 'Initializing…'} — {tracker.stage_label()}",
        expanded=True,
        state="running",
    )
    with status_container:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ Elapsed", tracker.elapsed_str())
        with col2:
            st.metric("⏲️ ETA", tracker.estimate_eta_str())
        with col3:
            st.metric("📍 Stage", tracker.current_stage or "initializing…")

        st.divider()

        with st.expander("📋 Log Details", expanded=False):
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
# Result & errors — shown prominently at top as soon as run completes
# ---------------------------------------------------------------------------

if state.error and not state.is_running:
    st.error("❌ Generation failed")
    with st.expander("Error details", expanded=True):
        st.code(state.error, language="python")

if state.result_path and not state.is_running:
    result = state.result_path
    if state.demo_mode:
        st.success(
            "🎬 Demo complete! Your beat-synced video is ready below. "
            "Upload your own footage to create your own version."
        )
        with st.container(border=True):
            if os.path.exists(result):
                st.video(result)
            else:
                st.warning("⚠️ Output file not found at the reported path.")
            col_exit, col_try = st.columns(2)
            with col_exit:
                if st.button("✕ Exit Demo", use_container_width=True):
                    state.demo_mode = False
                    st.session_state.pop("_demo_dry_run", None)
                    state.clear_results()
                    st.rerun()
            with col_try:
                st.info("↓ Upload your clips below to create your own video")
    else:
        st.success("✅ Montage successfully generated")
        with st.container(border=True):
            st.caption(f"📹 Saved to: `{result}`")
            if os.path.exists(result):
                st.video(result)
            else:
                st.warning("⚠️ Output file not found at the reported path.")

# ---------------------------------------------------------------------------
# Quick Preview plan report — shown immediately after dry-run completes
# ---------------------------------------------------------------------------

if state.plan_report and not state.is_running:
    st.markdown("---")
    st.success("✓ Dry-run complete — segment plan ready.")
    with st.container(border=True):
        st.subheader("📋 Segment Plan Report")
        st.code(st.session_state["plan_report"], language="")

# ---------------------------------------------------------------------------
# Demo mode banner
# ---------------------------------------------------------------------------

if not state.demo_mode and not state.is_running:
    with st.container(border=True):
        st.markdown("**New here? See it in action before you upload anything.**")
        st.caption("No uploads needed — we'll use sample bachata footage and music.")

        col_demo, col_preview = st.columns(2)
        with col_demo:
            demo_full_clicked = st.button(
                "▶ Run Full Demo",
                type="secondary",
                use_container_width=True,
                help="Run the tool with built-in sample clips and audio (~2 min).",
            )
        with col_preview:
            demo_preview_clicked = st.button(
                "📋 Quick Preview (10s)",
                type="secondary",
                use_container_width=True,
                help="See the beat-sync plan instantly — no video rendering.",
            )

        if demo_full_clicked or demo_preview_clicked:
            if not demo_assets_available():
                st.error(
                    "Demo assets not found. Run `make download-demo` and add "
                    "sample files to `demo/audio/` and `demo/clips/`.  "
                    "See `demo/README.md` for details."
                )
                st.stop()
            
            state.demo_mode = True
            # Store which demo variant was requested
            st.session_state["_demo_dry_run"] = demo_preview_clicked
            st.rerun()
else:
    # These variables are not used when demo banner is hidden, but we need
    # them defined so later references don't error.
    demo_full_clicked = False
    demo_preview_clicked = False

# Exit-demo banner (shown while demo is active but result hasn't loaded yet)
if state.demo_mode and not state.is_running and not state.result_path:
    with st.container(border=True):
        col_msg, col_exit = st.columns([3, 1])
        with col_msg:
            st.info(
                "🎬 Running with demo files. "
                "Upload your own below to create your video."
            )
        with col_exit:
            if st.button("✕ Exit Demo", use_container_width=True):
                state.demo_mode = False
                st.session_state.pop("_demo_dry_run", None)
                state.clear_results()
                st.rerun()

st.markdown("### 🎵 Inputs")

# Check deployment environment once
is_deployed = _is_deployed()

# Audio inputs card
audio_path_text = audio_input_component(state, is_deployed, disabled=state.is_running)

# Video clips card
video_dir = video_input_component(state, is_deployed, disabled=state.is_running)

# B-roll and Output cards are not needed in demo mode
if not state.demo_mode:
    broll_dir_input = broll_input_component(state, is_deployed, disabled=state.is_running)
    output_path = output_input_component(state, is_deployed, disabled=state.is_running)
else:
    broll_dir_input = ""
    output_path = ""

# ---------------------------------------------------------------------------
# Run button with improved layout
# ---------------------------------------------------------------------------

st.markdown("---")
col_spacer1, col_run, col_spacer2 = st.columns([1.5, 2, 1.5])
with col_run:
    if state.is_running:
        run_button = False
        if st.button(
            "🛑 Cancel",
            type="secondary",
            use_container_width=True,
            help="Stop the current processing run.",
        ):
            state.is_running = False
            state.error = "Run cancelled by user."
            st.rerun()
    else:
        run_button = st.button(
            "▶️  Generate Montage",
            type="primary",
            use_container_width=True,
            help=(
                "Process audio and video clips. This may take several minutes "
                "depending on video length."
            ),
        )


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
        # Retrieve uploaded files from session state (set by file_uploader
        # widgets in components)
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
            # Create a temporary directory and save uploaded videos
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

    # --- Build pacing kwargs (mirrors main.py logic) ---
    pacing_kwargs: dict = {}

    if genre_choice != "(none)":
        pacing_kwargs["genre"] = genre_choice

    if video_style != "none":
        pacing_kwargs["video_style"] = video_style

    if transition_type.strip() and transition_type.strip() != "none":
        pacing_kwargs["transition_type"] = transition_type.strip()

    if intro_effect and intro_effect != "none":
        pacing_kwargs["intro_effect"] = intro_effect

    # Demo mode overrides: force dry_run for preview, set limits
    if state.demo_mode:
        if st.session_state.get("_demo_dry_run", False):
            pacing_kwargs["dry_run"] = True
        pacing_kwargs["max_clips"] = 6
        pacing_kwargs["max_duration_seconds"] = 20.0
    else:
        if dry_run:
            pacing_kwargs["dry_run"] = True

    # Speed ramping (FEAT-036)
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

    # Test mode / limits (only in normal mode — demo sets its own limits above)
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

    # Demo mode: render to temp file to avoid polluting workspace
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

    # Clear the demo trigger flag so we don't re-trigger on rerun
    st.session_state.pop("_demo_dry_run", None)

    # Reset session state for this run
    state.is_running = True
    state.log_lines = []
    state.result_path = None
    state.error = None
    state.plan_report = None
    state.log_queue = queue.Queue()
    state.progress_tracker = ProgressTracker()  # Fresh tracker

    # Create and start the background thread
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

    # Give the thread a moment to initialize
    import time
    time.sleep(0.1)

    st.rerun()



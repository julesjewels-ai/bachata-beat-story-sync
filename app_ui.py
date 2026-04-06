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

from src.io.file_picker import pick_audio_file, pick_folder, pick_output_file
from src.ui.theme import apply_theme
from src.workers.progress import (
    ProgressTracker,
    QueueLogHandler,
    QueueProgressObserver,
    StageInfo,
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

def _init_state() -> None:
    defaults = {
        "running": False,
        "log_lines": [],
        "result_path": None,
        "error": None,
        "plan_report": None,
        "log_queue": queue.Queue(),
        "audio_path": "",
        "video_dir": "",
        "broll_dir": "",
        "output_path": "output_story.mp4",
        "progress_tracker": ProgressTracker(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_state()


# ---------------------------------------------------------------------------
# Lazy imports (avoid slow startup for users who haven't clicked Run yet)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading engine…")
def _load_engine():
    """Import and return BachataSyncEngine (cached across reruns)."""
    from src.core.app import BachataSyncEngine  # noqa: WPS433
    return BachataSyncEngine()


def _get_genres() -> list[str]:
    from src.core.genre_presets import list_genres  # noqa: WPS433
    return ["(none)", *list_genres()]


def _get_intro_effects() -> list[str]:
    from src.core.ffmpeg_renderer import INTRO_EFFECTS  # noqa: WPS433
    return ["none", *sorted(INTRO_EFFECTS.keys())]


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

genre_options = _get_genres()
genre_choice = st.sidebar.selectbox(
    "Genre preset",
    options=genre_options,
    help="Applies tuned clip pacing, colour grade and transitions for a genre.",
)

video_style = st.sidebar.selectbox(
    "Colour grade",
    options=["none", "bw", "vintage", "warm", "cool", "golden"],
    help="Colour grading applied to every segment.",
)

transition_type = st.sidebar.text_input(
    "Transition type",
    value="none",
    help="FFmpeg xfade: none, fade, wipeleft, wiperight, slideup, …",
)

intro_effects_options = _get_intro_effects()
intro_effect = st.sidebar.selectbox(
    "Intro effect",
    options=intro_effects_options,
    help="Visual effect applied to the very first clip.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Limits & Output")

test_mode = st.sidebar.checkbox(
    "🧪 Test mode",
    value=False,
    help="Restrict to 4 clips and 10s — good for quick checks.",
)

max_clips_input = st.sidebar.number_input(
    "Max clips (0 = unlimited)",
    min_value=0,
    value=0,
    step=1,
)

max_duration_input = st.sidebar.number_input(
    "Max duration in seconds (0 = unlimited)",
    min_value=0,
    value=0,
    step=5,
)

dry_run = st.sidebar.checkbox(
    "📋 Dry run (plan only)",
    value=False,
    help="Analyse and plan without rendering.",
)

export_report = st.sidebar.checkbox(
    "📊 Export Excel report",
    value=False,
    help="Generate analysis.xlsx alongside video.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("✨ Advanced Effects")

# Speed ramping
st.sidebar.markdown("**Speed Ramping (FEAT-036)**")
speed_ramp_organic = st.sidebar.checkbox(
    "Organic per-beat speed",
    value=False,
    help="Variable speed within clips driven by beat-by-beat intensity (breathing effect)."
)
if speed_ramp_organic:
    speed_ramp_sensitivity = st.sidebar.slider(
        "Sensitivity",
        min_value=0.3,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="0.5=gentle, 1.0=standard, 2.0=aggressive"
    )
    speed_ramp_curve = st.sidebar.selectbox(
        "Curve type",
        options=["linear", "ease_in", "ease_out", "ease_in_out"],
        help="Smoothing function for speed transitions"
    )
    col_speed_min, col_speed_max = st.sidebar.columns(2)
    with col_speed_min:
        speed_ramp_min = st.number_input(
            "Min speed",
            min_value=0.3,
            max_value=1.0,
            value=0.8,
            step=0.1,
            help="Slowest multiplier (low-energy beats)"
        )
    with col_speed_max:
        speed_ramp_max = st.number_input(
            "Max speed",
            min_value=1.0,
            max_value=2.0,
            value=1.3,
            step=0.1,
            help="Fastest multiplier (high-energy beats)"
        )
else:
    speed_ramp_sensitivity = 1.0
    speed_ramp_curve = "ease_in_out"
    speed_ramp_min = 0.8
    speed_ramp_max = 1.3

# Other pacing effects
st.sidebar.markdown("**Beat-Synced Effects**")
pacing_drift_zoom = st.sidebar.checkbox("Drift zoom (Ken Burns)", value=False)
pacing_crop_tighten = st.sidebar.checkbox("Crop tighten", value=False)
pacing_saturation_pulse = st.sidebar.checkbox("Saturation pulse on beats", value=False)
pacing_micro_jitters = st.sidebar.checkbox("Micro-jitters on beats", value=False)
pacing_light_leaks = st.sidebar.checkbox("Light leaks on beats", value=False)
pacing_warm_wash = st.sidebar.checkbox("Warm wash at transitions", value=False)
pacing_alternating_bokeh = st.sidebar.checkbox("Alternating bokeh blur", value=False)


# ---------------------------------------------------------------------------
# UI — Main area
# ---------------------------------------------------------------------------

# Header with better branding
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.write("🎵")  # Logo placeholder
with col_title:
    st.markdown("## Beat-Story Sync")
    st.caption("Automatically sync your dance video clips to musical beats and intensity. Terra uses neural waveform analysis to create organic transitions that breathe with the music.")

st.markdown("---")
st.markdown("### 🎵 Inputs")

# Check deployment environment once
is_deployed = _is_deployed()

# Audio inputs card
with st.container(border=True):
    st.subheader("Audio", anchor=None)

    if is_deployed:
        # Deployed version: file upload only
        st.markdown("**Upload audio file**")
        uploaded_audio = st.file_uploader(
            "Drag and drop or click to upload",
            type=["wav", "mp3"],
            key="audio_upload",
            label_visibility="collapsed",
            help="Maximum 200MB • WAV / MP3",
        )
        audio_path_text = ""  # No local path option when deployed
    else:
        # Local version: offer both upload and local path
        col_audio_upload, col_audio_path = st.columns([1.5, 2.5])

        with col_audio_upload:
            st.markdown("**Upload audio file**")
            uploaded_audio = st.file_uploader(
                "Drag and drop or click",
                type=["wav", "mp3"],
                key="audio_upload",
                label_visibility="collapsed",
                help="Maximum 200MB • WAV / MP3",
            )

        with col_audio_path:
            st.markdown("**Or paste path**")
            col_text, col_btn = st.columns([4, 1])
            with col_btn:
                if st.button("📁", key="pick_audio", help="Browse for audio file", use_container_width=True):
                    picked = pick_audio_file()
                    if picked:
                        st.session_state["audio_path"] = picked
                        st.rerun()
            with col_text:
                audio_path_text = st.text_input(
                    "Audio path",
                    placeholder="/Volumes/Drives/Music...",
                    key="audio_path",
                    label_visibility="collapsed",
                    help="Absolute path on your machine.",
                )

# Video clips card
with st.container(border=True):
    st.subheader("Video Clips", anchor=None)

    if is_deployed:
        # Deployed version: file upload only
        st.markdown("**Upload video files**")
        uploaded_videos = st.file_uploader(
            "Drag and drop or click to upload",
            type=["mp4", "mov", "avi", "mkv"],
            key="video_upload",
            accept_multiple_files=True,
            label_visibility="collapsed",
            help="Maximum 200MB per file • MP4 / MOV / AVI / MKV",
        )
        video_dir = ""  # No local path option when deployed
        st.caption("Upload your video clips to get started.")
    else:
        # Local version: offer both upload and local path
        col_video_upload, col_video_path = st.columns([1.5, 2.5])

        with col_video_upload:
            st.markdown("**Upload video files**")
            uploaded_videos = st.file_uploader(
                "Drag and drop or click",
                type=["mp4", "mov", "avi", "mkv"],
                key="video_upload",
                accept_multiple_files=True,
                label_visibility="collapsed",
                help="Maximum 200MB per file • MP4 / MOV / AVI / MKV",
            )

        with col_video_path:
            st.markdown("**Or paste path**")
            col_text, col_btn = st.columns([4, 1])
            with col_btn:
                if st.button("📁", key="pick_video", help="Browse for video clips folder", use_container_width=True):
                    picked = pick_folder("Select folder containing video clips")
                    if picked:
                        st.session_state["video_dir"] = picked
                        st.rerun()
            with col_text:
                video_dir = st.text_input(
                    "Footage folder",
                    placeholder="/Users/Artist/Documents/Project_01/Raw",
                    key="video_dir",
                    label_visibility="collapsed",
                    help="Terra will auto-index and categorize by motion intensity.",
                )
        st.caption("Upload individual video files or select the root directory containing your dance footage.")

# B-roll card (optional)
with st.container(border=True):
    st.subheader("B-roll", anchor=None)
    st.caption("OPTIONAL — Add texture clips, atmospheric shots, or environment b-roll to be used as transitions and overlays during musical swells.")

    if not is_deployed:
        col_broll_path, col_broll_btn = st.columns([4, 1])
        with col_broll_btn:
            if st.button("📁", key="pick_broll", help="Browse for B-roll folder", use_container_width=True):
                picked = pick_folder("Select B-roll folder")
                if picked:
                    st.session_state["broll_dir"] = picked
                    st.rerun()
        with col_broll_path:
            broll_dir_input = st.text_input(
                "Overlays folder",
                placeholder="/Users/Artist/Documents/Stock/Atmosph",
                key="broll_dir",
                help="Auto-detected as a 'broll/' subfolder inside the clips folder if it exists.",
            )
    else:
        st.info("💡 B-roll support is available when running locally. Include B-roll files with your video uploads for now.")
        broll_dir_input = ""  # No B-roll when deployed

# Output card
with st.container(border=True):
    st.subheader("Output", anchor=None)

    if is_deployed:
        # Deployed version: simple filename input
        output_path = st.text_input(
            "Output filename",
            key="output_path",
            help="Your finished video will be available to download.",
            placeholder="output_story.mp4",
            value="output_story.mp4",
        )
    else:
        # Local version: full path picker
        col_output_path, col_output_btn = st.columns([4, 1])
        with col_output_btn:
            if st.button("📁", key="pick_output", help="Browse and save output video", use_container_width=True):
                picked = pick_output_file()
                if picked:
                    st.session_state["output_path"] = picked
                    st.rerun()
        with col_output_path:
            output_path = st.text_input(
                "Save as",
                key="output_path",
                help="Where to save the finished video.",
                placeholder="output_story.mp4",
            )

# ---------------------------------------------------------------------------
# Run button with improved layout
# ---------------------------------------------------------------------------

st.markdown("---")
col_spacer1, col_run, col_spacer2 = st.columns([1.5, 2, 1.5])
with col_run:
    run_button = st.button(
        "▶️  Generate Montage",
        type="primary",
        disabled=st.session_state["running"],
        use_container_width=True,
        help="Process audio and video clips. This may take several minutes depending on video length.",
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

if run_button:
    # --- Validate inputs ---
    errors: list[str] = []

    # Resolve audio path (upload overrides text input)
    resolved_audio_path: str | None = None
    temp_audio_file: str | None = None

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
    resolved_video_dir: str | None = None
    temp_video_dir: str | None = None

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
        errors.append("Please upload video files or enter the path to your video clips folder.")

    broll_dir_resolved: str | None = broll_dir_input.strip() or None
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

    # Test mode / limits
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

    # Excel report path
    report_path: str | None = None
    if export_report:
        base, _ = os.path.splitext(output_path.strip())
        report_path = base + "_report.xlsx"

    # Reset session state for this run
    st.session_state["running"] = True
    st.session_state["log_lines"] = []
    st.session_state["result_path"] = None
    st.session_state["error"] = None
    st.session_state["plan_report"] = None
    st.session_state["log_queue"] = queue.Queue()
    st.session_state["progress_tracker"] = ProgressTracker()  # Fresh tracker

    # Create and start the background thread
    thread = threading.Thread(
        target=_run_generation,
        args=(
            resolved_audio_path,
            resolved_video_dir,
            broll_dir_resolved,
            output_path.strip(),
            pacing_kwargs,
            report_path,
            st.session_state["log_queue"],
        ),
        daemon=True,
    )
    thread.start()

    # Give the thread a moment to initialize
    import time
    time.sleep(0.1)

    st.rerun()


# ---------------------------------------------------------------------------
# Drain the log queue and update session state on each rerun
# ---------------------------------------------------------------------------

if st.session_state["running"]:
    log_queue: queue.Queue = st.session_state["log_queue"]
    tracker: ProgressTracker = st.session_state["progress_tracker"]

    # Drain everything currently in the queue
    done = False
    while True:
        try:
            line = log_queue.get_nowait()
        except queue.Empty:
            break

        if line.startswith("__DONE__"):
            done = True
        elif line.startswith("__RESULT__"):
            st.session_state["result_path"] = line[len("__RESULT__"):]
        elif line.startswith("__ERROR__"):
            st.session_state["error"] = line[len("__ERROR__"):]
        elif line.startswith("__PLAN_REPORT__"):
            st.session_state["plan_report"] = line[len("__PLAN_REPORT__"):]
        else:
            st.session_state["log_lines"].append(line)
            tracker.update(line)

    if done:
        st.session_state["running"] = False


# ---------------------------------------------------------------------------
# Display progress status (replaces meta-refresh)
# ---------------------------------------------------------------------------

if st.session_state["running"]:
    tracker: ProgressTracker = st.session_state["progress_tracker"]

    # Initialize tracker timing on first run
    if tracker.start_time is None:
        tracker.start()

    # Create persistent status container with metrics always visible
    status_container = st.status(
        f"⏳ {tracker.current_stage or 'Initializing…'} — {tracker.stage_label()}",
        state="running",
    )

    with status_container:
        # Show progress metrics in a prominent row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ Elapsed", tracker.elapsed_str())
        with col2:
            st.metric("⏲️ ETA", tracker.estimate_eta_str())
        with col3:
            st.metric("📍 Stage", tracker.current_stage or "initializing…")

        st.divider()

        # Show logs in collapsible detail container
        with st.expander("📋 Log Details", expanded=False):
            log_text = "\n".join(st.session_state["log_lines"])
            st.code(log_text, language="")

        st.caption("Status updates every 2 seconds")

    # Auto-rerun every 2 seconds for live updates
    time.sleep(0.1)
    st.rerun()


# ---------------------------------------------------------------------------
# Display results and messages
# ---------------------------------------------------------------------------

if st.session_state["error"]:
    st.error("❌ Generation failed")
    with st.expander("Error details", expanded=True):
        st.code(st.session_state["error"], language="python")

if st.session_state["plan_report"]:
    st.markdown("---")
    st.success("✓ Dry-run complete — segment plan ready.")
    with st.container(border=True):
        st.subheader("📋 Segment Plan Report")
        st.code(st.session_state['plan_report'], language="")

if st.session_state["result_path"]:
    result = st.session_state["result_path"]
    st.markdown("---")
    st.success(f"✅ Montage successfully generated")
    with st.container(border=True):
        st.caption(f"📹 Saved to: `{result}`")
        if os.path.exists(result):
            st.video(result)
        else:
            st.warning("⚠️ Output file not found at the reported path.")

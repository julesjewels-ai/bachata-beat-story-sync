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

import streamlit as st

# ---------------------------------------------------------------------------
# Page config must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Bachata Beat-Story Sync",
    page_icon="🎵",
    layout="wide",
)


# ---------------------------------------------------------------------------
# In-memory logging handler that feeds a thread-safe queue
# ---------------------------------------------------------------------------

class QueueLogHandler(logging.Handler):
    """Logging handler that pushes formatted records onto a queue."""

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self._queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait(self.format(record))
        except Exception:  # noqa: BLE001
            pass


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
# UI — Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Settings")

genre_options = _get_genres()
genre_choice = st.sidebar.selectbox(
    "Genre preset",
    options=genre_options,
    help="Applies tuned clip pacing, colour grade and transitions for a genre.",
)

video_style = st.sidebar.selectbox(
    "Video style / colour grade",
    options=["none", "bw", "vintage", "warm", "cool", "golden"],
    help="Colour grading applied to every segment.",
)

transition_type = st.sidebar.text_input(
    "Transition type",
    value="none",
    help="FFmpeg xfade transition: none, fade, wipeleft, wiperight, slideup, …",
)

intro_effects_options = _get_intro_effects()
intro_effect = st.sidebar.selectbox(
    "Intro effect",
    options=intro_effects_options,
    help="Visual effect applied to the very first clip.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("Limits")

test_mode = st.sidebar.checkbox(
    "Test mode",
    value=False,
    help="Restrict to 4 clips and 10 s of music — good for quick checks.",
)

max_clips_input = st.sidebar.number_input(
    "Max clips (0 = unlimited)",
    min_value=0,
    value=0,
    step=1,
    help="Hard cap on clip segments. 0 means no limit.",
)

max_duration_input = st.sidebar.number_input(
    "Max duration in seconds (0 = unlimited)",
    min_value=0,
    value=0,
    step=5,
    help="Hard cap on total montage length. 0 means no limit.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("Output options")

dry_run = st.sidebar.checkbox(
    "Dry run (plan only, no rendering)",
    value=False,
    help="Analyse and plan without running FFmpeg. Shows a segment plan report.",
)

export_report = st.sidebar.checkbox(
    "Export Excel analysis report",
    value=False,
    help="Generate a report.xlsx alongside the output video.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("Pacing effects")

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

st.title("Bachata Beat-Story Sync")
st.caption("Automatically sync your dance video clips to musical beats and intensity.")

st.markdown("### Inputs")

col1, col2 = st.columns([2, 1])

with col1:
    audio_path_text = st.text_input(
        "Path to audio file (.wav or .mp3)",
        placeholder="/path/to/track.wav",
        help="Absolute path to your audio track on this machine.",
    )

with col2:
    uploaded_audio = st.file_uploader(
        "…or upload an audio file",
        type=["wav", "mp3"],
        help="Uploads are saved to a temp folder for the duration of the session.",
    )

video_dir = st.text_input(
    "Path to folder containing video clips",
    placeholder="/path/to/clips/",
    help="Folder of .mp4 clips to use in the montage.",
)

broll_dir_input = st.text_input(
    "B-roll folder (optional — leave blank to auto-detect)",
    placeholder="/path/to/clips/broll/",
    help="Auto-detected as a 'broll/' subfolder inside the clips folder if it exists.",
)

output_path = st.text_input(
    "Output video path",
    value="output_story.mp4",
    help="Where to save the finished video.",
)

# ---------------------------------------------------------------------------
# Run button
# ---------------------------------------------------------------------------

run_button = st.button(
    "Generate Montage",
    type="primary",
    disabled=st.session_state["running"],
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
    # Attach our queue handler to the root logger for this thread
    handler = QueueLogHandler(log_queue)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    try:
        from src.cli_utils import analyze_audio, detect_broll_dir, strip_thumbnails  # noqa: WPS433
        from src.core.app import BachataSyncEngine  # noqa: WPS433
        from src.core.models import PacingConfig  # noqa: WPS433
        from src.core.montage import load_pacing_config  # noqa: WPS433
        from src.ui.console import RichProgressObserver  # noqa: WPS433

        engine = BachataSyncEngine()

        # 1. Analyse audio
        log_queue.put("INFO: Analysing audio…")
        resolved_audio, audio_meta = analyze_audio(audio_resolved)

        # 2. Scan video library
        log_queue.put(f"INFO: Scanning video clips in {video_dir_path}")
        broll_dir_resolved = detect_broll_dir(video_dir_path, broll_path)
        exclude_dirs = [broll_dir_resolved] if broll_dir_resolved else None

        with RichProgressObserver() as obs:
            video_clips = engine.scan_video_library(
                video_dir_path, exclude_dirs=exclude_dirs, observer=obs
            )
        log_queue.put(f"INFO: Found {len(video_clips)} suitable clip(s).")

        broll_clips = None
        if broll_dir_resolved and os.path.exists(broll_dir_resolved):
            log_queue.put(f"INFO: Scanning B-roll in {broll_dir_resolved}")
            with RichProgressObserver() as obs:
                broll_clips = engine.scan_video_library(
                    broll_dir_resolved, observer=obs
                )
            log_queue.put(f"INFO: Found {len(broll_clips)} B-roll clip(s).")

        # 3. Build pacing config
        base_config = load_pacing_config()
        merged = {**base_config.model_dump(), **pacing_kwargs}
        pacing = PacingConfig(**merged)

        montage_clips = strip_thumbnails(video_clips)

        # 4a. Dry-run path
        if pacing.dry_run:
            from src.services.plan_report import format_plan_report  # noqa: WPS433
            segments = engine.plan_story(audio_meta, montage_clips, pacing=pacing)
            report = format_plan_report(audio_meta, segments, montage_clips, pacing)
            log_queue.put("__PLAN_REPORT__" + report)
            log_queue.put("INFO: Dry-run complete — no video rendered.")
            log_queue.put("__DONE__")
            return

        # 4b. Full render
        log_queue.put("INFO: Syncing visual narrative to musical dynamics…")
        with RichProgressObserver() as obs:
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

        log_queue.put(f"INFO: Done! Output saved to: {result_path}")

        # 5. Optional Excel report
        if export_report_path:
            from src.services.reporting import ExcelReportGenerator  # noqa: WPS433
            log_queue.put(f"INFO: Generating Excel report → {export_report_path}")
            ExcelReportGenerator().generate_report(
                audio_meta, video_clips, export_report_path
            )

        log_queue.put("__RESULT__" + result_path)
        log_queue.put("__DONE__")

    except Exception as exc:  # noqa: BLE001
        log_queue.put(f"__ERROR__{exc}")
        log_queue.put("__DONE__")
    finally:
        root_logger.removeHandler(handler)


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

    if not video_dir.strip():
        errors.append("Please enter the path to your video clips folder.")
    elif not os.path.isdir(video_dir.strip()):
        errors.append(f"Video clips folder not found: {video_dir.strip()}")

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

    thread = threading.Thread(
        target=_run_generation,
        args=(
            resolved_audio_path,
            video_dir.strip(),
            broll_dir_resolved,
            output_path.strip(),
            pacing_kwargs,
            report_path,
            st.session_state["log_queue"],
        ),
        daemon=True,
    )
    thread.start()
    st.rerun()


# ---------------------------------------------------------------------------
# Drain the log queue and update session state on each rerun
# ---------------------------------------------------------------------------

if st.session_state["running"]:
    log_queue: queue.Queue = st.session_state["log_queue"]

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

    if done:
        st.session_state["running"] = False


# ---------------------------------------------------------------------------
# Progress feedback while running
# ---------------------------------------------------------------------------

if st.session_state["running"]:
    st.info("Generating montage… this may take a few minutes. Refresh to see log updates.")
    st.spinner("Working…")
    # Auto-refresh every 3 seconds while running
    st.markdown(
        "<meta http-equiv='refresh' content='3'>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------

if st.session_state["error"]:
    st.error(f"Generation failed: {st.session_state['error']}")

if st.session_state["plan_report"]:
    st.success("Dry-run complete — segment plan ready.")
    with st.expander("Segment Plan Report", expanded=True):
        st.markdown(
            f"```\n{st.session_state['plan_report']}\n```"
        )

if st.session_state["result_path"]:
    result = st.session_state["result_path"]
    st.success(f"Montage saved to: `{result}`")
    if os.path.exists(result):
        st.video(result)
    else:
        st.warning("Output file not found at the reported path.")

if st.session_state["log_lines"]:
    with st.expander("Processing Log", expanded=st.session_state["running"]):
        st.text("\n".join(st.session_state["log_lines"]))

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
from dataclasses import dataclass

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
# Terra Design System — Custom CSS Styling
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* Root colors from design system */
    :root {
        --primary: #4a7c59;
        --bg-cream: #faf6f0;
        --secondary-bg: #f0ede5;
        --tertiary: #705c30;
        --accent-amber: #c99a6e;
        --text-dark: #1a1a1a;
        --text-light: #6b6b6b;
        --border-soft: #e0dcd4;
    }

    /* Page background - warm cream with subtle texture feeling */
    body, .main {
        background-color: var(--bg-cream);
        color: var(--text-dark);
    }

    /* Typography - with warmth and personality */
    h1, h2, h3 {
        color: var(--text-dark);
        font-family: 'Literata', serif;
        letter-spacing: -0.5px;
        font-weight: 700;
    }

    h1 {
        font-size: 2.2rem;
        color: var(--primary);
    }

    h2 {
        font-size: 1.6rem;
        margin-bottom: 1.2rem;
        position: relative;
        padding-left: 0.8rem;
    }

    h2::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 4px;
        height: 1.2em;
        background: linear-gradient(to bottom, var(--primary), var(--tertiary));
        border-radius: 2px;
    }

    h3 {
        font-size: 1.1rem;
    }

    p, label, .stMarkdown {
        font-family: 'Nunito Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        line-height: 1.6;
        color: var(--text-dark);
    }

    /* Primary buttons - prominent and inviting */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary), #3d6849);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 28px;
        font-weight: 600;
        font-family: 'Nunito Sans', sans-serif;
        font-size: 0.95rem;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        min-height: 48px;
        box-shadow: 0 4px 20px rgba(74, 124, 89, 0.15);
        letter-spacing: 0.3px;
    }

    .stButton > button:hover:not(:disabled) {
        box-shadow: 0 8px 30px rgba(74, 124, 89, 0.25);
        transform: translateY(-3px);
    }

    .stButton > button:active {
        transform: translateY(-1px) scale(0.98);
    }

    .stButton > button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    /* Secondary buttons - soft and minimal */
    .stButton[data-baseweb="button"]:has(button) > button {
        padding: 10px 18px;
        font-size: 0.9rem;
        background-color: var(--secondary-bg);
        color: var(--primary);
        border: 2px solid var(--primary);
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stButton[data-baseweb="button"]:has(button) > button:hover:not(:disabled) {
        background-color: var(--primary);
        color: white;
        box-shadow: 0 4px 16px rgba(74, 124, 89, 0.2);
    }

    /* Input fields - soft focus states */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: white;
        border: 2px solid var(--border-soft);
        border-radius: 10px;
        color: var(--text-dark);
        font-family: 'Nunito Sans', sans-serif;
        padding: 12px 14px;
        transition: all 0.2s ease;
        font-size: 0.95rem;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 4px rgba(74, 124, 89, 0.12);
        background-color: #fefdfb;
    }

    /* Checkboxes - custom styling */
    .stCheckbox > label {
        color: var(--text-dark);
        font-weight: 500;
        font-family: 'Nunito Sans', sans-serif;
        font-size: 0.95rem;
    }

    /* Sliders - gradient and refined */
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, var(--primary) 0%, var(--accent-amber) 50%, var(--tertiary) 100%);
        border-radius: 8px;
        height: 6px;
    }

    /* Cards/Containers - enhanced with borders and shadows */
    [data-testid="element-container"] {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.85) 100%);
        border-radius: 14px;
        padding: 1.8rem;
        box-shadow: 0 4px 20px rgba(46, 50, 48, 0.08);
        border: 1.5px solid var(--border-soft);
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }

    [data-testid="element-container"]:hover {
        box-shadow: 0 6px 28px rgba(46, 50, 48, 0.12);
        border-color: rgba(74, 124, 89, 0.2);
    }

    /* Better subheader styling - with accent */
    .stSubheader {
        color: var(--primary);
        font-weight: 700;
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.05rem;
    }

    /* Sidebar - warmer and more defined */
    .css-1544g2n {
        background: linear-gradient(180deg, var(--secondary-bg) 0%, rgba(240, 237, 229, 0.7) 100%);
        border-right: 2px solid var(--border-soft);
        padding-top: 1.5rem;
    }

    .css-1544g2n h2 {
        color: var(--primary);
        margin-top: 2rem;
        margin-bottom: 1.2rem;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        font-weight: 700;
        padding-left: 0.5rem;
        border-left: 3px solid var(--primary);
    }

    .css-1544g2n h3 {
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--tertiary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 1.8rem;
        margin-bottom: 1rem;
        padding-left: 0.5rem;
        border-left: 3px solid var(--tertiary);
    }

    .css-1544g2n [data-testid="element-container"] {
        background-color: rgba(255, 255, 255, 0.6);
        border-color: rgba(224, 220, 212, 0.8);
    }

    /* Dividers - warmer styling */
    hr, .css-bm2z3a {
        border-color: var(--border-soft);
        opacity: 0.4;
        margin: 1.5rem 0;
    }

    /* Status indicators */
    .stStatus {
        background-color: white;
        border-radius: 12px;
        border: 2px solid var(--primary);
    }

    /* Expander - soft and inviting */
    .streamlit-expanderHeader {
        background: linear-gradient(90deg, var(--secondary-bg) 0%, rgba(240, 237, 229, 0.5) 100%);
        border-radius: 10px;
        border: 1px solid var(--border-soft);
        transition: all 0.2s ease;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--primary);
        background: linear-gradient(90deg, rgba(240, 237, 229, 0.8) 0%, rgba(240, 237, 229, 0.6) 100%);
    }

    /* Metrics - cards with accent top border */
    .stMetric {
        background-color: white;
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid var(--border-soft);
        border-top: 4px solid var(--primary);
        box-shadow: 0 2px 12px rgba(46, 50, 48, 0.06);
        transition: all 0.2s ease;
    }

    .stMetric:hover {
        box-shadow: 0 4px 18px rgba(46, 50, 48, 0.1);
    }

    .stMetric > div:first-child {
        color: var(--text-light);
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }

    .stMetric > div:last-child {
        color: var(--primary);
        font-size: 2rem;
        font-weight: 700;
    }

    /* Warnings, errors, success */
    .stAlert {
        border-radius: 10px;
        border-left: 5px solid var(--primary);
        background-color: rgba(74, 124, 89, 0.05);
        border-color: var(--primary);
        padding: 1rem;
    }

    /* Video player */
    .stVideo {
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 6px 28px rgba(46, 50, 48, 0.15);
    }

    /* Code blocks - warm theme */
    code {
        background-color: var(--secondary-bg);
        border-radius: 6px;
        padding: 3px 7px;
        color: var(--tertiary);
        font-family: 'Fira Code', monospace;
        font-size: 0.9em;
    }

    pre {
        background-color: #2e3230;
        color: #f0ede5;
        border-radius: 10px;
        padding: 1.2rem;
        overflow-x: auto;
        font-size: 0.85rem;
        line-height: 1.6;
        border: 1px solid rgba(240, 237, 229, 0.1);
    }

    /* Headings - more spacing and style */
    h1 { margin-top: 2.5rem; margin-bottom: 1.5rem; }
    h2 { margin-top: 2rem; margin-bottom: 1.2rem; }
    h3 { margin-top: 1.5rem; margin-bottom: 0.75rem; }

    /* Captions and help text - secondary color */
    .stCaption, [data-testid="stCaption"] {
        color: var(--text-light);
        font-size: 0.8rem;
        font-weight: 500;
        margin: 0.5rem 0 1rem 0;
        font-family: 'Nunito Sans', sans-serif;
    }

    /* File uploader - inviting drop zone */
    [data-testid="stFileUploadDropzone"] {
        border: 3px dashed var(--primary);
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(74, 124, 89, 0.04) 0%, rgba(74, 124, 89, 0.02) 100%);
        padding: 2rem;
        transition: all 0.2s ease;
    }

    [data-testid="stFileUploadDropzone"]:hover {
        background: linear-gradient(135deg, rgba(74, 124, 89, 0.08) 0%, rgba(74, 124, 89, 0.05) 100%);
        border-color: var(--tertiary);
        box-shadow: 0 4px 20px rgba(74, 124, 89, 0.12);
    }

    /* Main content padding - generous spacing */
    .main {
        padding: 2.5rem;
    }

    /* Accent divider lines */
    .stMarkdown hr {
        border-top: 2px solid var(--border-soft);
        margin: 2rem 0;
    }

    /* Better spacing for tabs */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 2px solid var(--border-soft);
    }

    .stTabs [data-baseweb="tab"] {
        border-bottom: 3px solid transparent;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        border-bottom-color: var(--primary);
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Progress tracking for ETA calculation
# ---------------------------------------------------------------------------

@dataclass
class StageInfo:
    """Stage progress information."""
    name: str
    current: int
    total: int
    estimated_percent: float

    @property
    def pct(self) -> float:
        """Return percentage for this stage."""
        return (self.current / self.total * 100) if self.total > 0 else 0


class ProgressTracker:
    """Tracks pipeline progress, stage, elapsed time, and estimates ETA."""

    # Stage duration heuristics (as % of total runtime)
    STAGE_HEURISTICS = {
        "Analysing audio": 10,
        "Scanning video": 10,
        "Configuring pacing": 5,
        "Planning segment": 5,
        "Rendering montage": 65,
        "Generating Excel": 5,
    }

    def __init__(self) -> None:
        self.start_time: float | None = None
        self.current_stage: str = ""
        # stage -> (current, total)
        self.stage_progress: dict[str, tuple[int, int]] = {}
        self.log_count: int = 0

    def start(self) -> None:
        """Mark the start of processing."""
        self.start_time = time.time()

    def update(self, message: str) -> None:
        """Update progress based on log message."""
        self.log_count += 1

        # Extract stage name from log message (e.g., "[1/4] Analysing audio…")
        for stage_key in self.STAGE_HEURISTICS:
            if stage_key in message:
                self.current_stage = stage_key
                break

        # Parse "[N/M]" progress
        if "[" in message and "/" in message:
            try:
                bracket = message[message.index("[") : message.index("]") + 1]
                parts = bracket.strip("[]").split("/")
                current, total = int(parts[0]), int(parts[1])
                self.stage_progress[self.current_stage] = (current, total)
            except (ValueError, IndexError):
                pass

    def elapsed_seconds(self) -> float:
        """Return elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def elapsed_str(self) -> str:
        """Return elapsed time as HH:MM:SS."""
        seconds = int(self.elapsed_seconds())
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def estimate_eta_seconds(self) -> float | None:
        """Estimate remaining time based on elapsed time and stage heuristics."""
        if self.start_time is None or not self.current_stage:
            return None

        elapsed = self.elapsed_seconds()
        if elapsed < 1:
            return None

        # Find estimated total based on current stage
        current_heuristic = self.STAGE_HEURISTICS.get(self.current_stage, 50)
        estimated_total = elapsed / (current_heuristic / 100.0)
        estimated_remaining = estimated_total - elapsed
        return max(0, estimated_remaining)

    def estimate_eta_str(self) -> str:
        """Return estimated remaining time as HH:MM:SS or '?'."""
        eta = self.estimate_eta_seconds()
        if eta is None:
            return "—"
        seconds = int(eta)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def stage_label(self) -> str:
        """Return a readable stage label (e.g., '2 of 4')."""
        if not self.stage_progress:
            return "starting…"
        # Get the highest stage number seen
        max_current = max((c for c, _ in self.stage_progress.values()), default=0)
        max_total = max((t for _, t in self.stage_progress.values()), default=0)
        return f"{max_current} of {max_total}"


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


class QueueProgressObserver:
    """Progress observer that pushes status updates to a log queue."""

    def __init__(self, log_queue: queue.Queue) -> None:
        self._queue = log_queue

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """Pushes a progress message to the queue."""
        percent = (current / total * 100) if total > 0 else 0
        formatted = f"PROGRESS: {message} ({percent:.0f}%)"
        self._queue.put(formatted)


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
# File/folder picker helpers using tkinter
# ---------------------------------------------------------------------------


def _run_safe_tk_dialog(script: str) -> str | None:
    """Execute tkinter script in separate process to avoid macOS main-thread issues."""
    import subprocess
    import sys

    # Use the same python executable as the current process
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001
        return None
    return None


def _pick_folder(title: str = "Select folder") -> str | None:
    """Open a native folder picker. Returns selected path or None."""
    script = f"""
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes("-topmost", True)
path = filedialog.askdirectory(title='{title}')
root.destroy()
if path:
    print(path)
"""
    return _run_safe_tk_dialog(script)


def _pick_audio_file() -> str | None:
    """Open a native file picker for audio files."""
    script = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes("-topmost", True)
path = filedialog.askopenfilename(
    title='Select audio file',
    filetypes=[('Audio files', '*.wav *.mp3'), ('All files', '*.*')],
)
root.destroy()
if path:
    print(path)
"""
    return _run_safe_tk_dialog(script)


def _pick_output_file() -> str | None:
    """Open a native save-as dialog for the output MP4."""
    script = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes("-topmost", True)
path = filedialog.asksaveasfilename(
    title='Save output video as',
    defaultextension='.mp4',
    filetypes=[('MP4 video', '*.mp4'), ('All files', '*.*')],
)
root.destroy()
if path:
    print(path)
"""
    return _run_safe_tk_dialog(script)


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

# Audio inputs card
with st.container(border=True):
    st.subheader("Audio", anchor=None)
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
                picked = _pick_audio_file()
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
    col_video_path, col_video_btn = st.columns([4, 1])
    with col_video_btn:
        if st.button("📁", key="pick_video", help="Browse for video clips folder", use_container_width=True):
            picked = _pick_folder("Select folder containing video clips")
            if picked:
                st.session_state["video_dir"] = picked
                st.rerun()
    with col_video_path:
        video_dir = st.text_input(
            "Footage folder",
            placeholder="/Users/Artist/Documents/Project_01/Raw",
            key="video_dir",
            help="Terra will auto-index and categorize by motion intensity.",
        )
    st.caption("Select the root directory containing your dance footage.")

# B-roll card (optional)
with st.container(border=True):
    st.subheader("B-roll", anchor=None)
    st.caption("OPTIONAL — Add texture clips, atmospheric shots, or environment b-roll to be used as transitions and overlays during musical swells.")

    col_broll_path, col_broll_btn = st.columns([4, 1])
    with col_broll_btn:
        if st.button("📁", key="pick_broll", help="Browse for B-roll folder", use_container_width=True):
            picked = _pick_folder("Select B-roll folder")
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

# Output card
with st.container(border=True):
    st.subheader("Output", anchor=None)
    col_output_path, col_output_btn = st.columns([4, 1])
    with col_output_btn:
        if st.button("📁", key="pick_output", help="Browse and save output video", use_container_width=True):
            picked = _pick_output_file()
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

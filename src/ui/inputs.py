"""Reusable input components for the Streamlit UI.

Consolidates repeated deployed/local conditional logic for file inputs.
"""

from __future__ import annotations

import streamlit as st

from src.io.file_picker import pick_audio_file, pick_folder, pick_output_file
from src.state.session import SessionState
from src.ui.video_cache import get_cached_clips
from pathlib import Path

DEMO_AUDIO = Path(__file__).parent.parent.parent / "demo" / "audio" / "sample_bachata.mp3"
DEMO_CLIPS = Path(__file__).parent.parent.parent / "demo" / "clips"


def demo_assets_available() -> bool:
    """Return True if demo audio and at least one clip exist on disk."""
    if not DEMO_AUDIO.exists():
        return False
    if not DEMO_CLIPS.exists():
        return False
    return bool(list(DEMO_CLIPS.glob("*.mp4")))


def audio_input_component(state: SessionState, is_deployed: bool, disabled: bool = False) -> str:
    """Audio file input with deploy-aware fallback.

    Args:
        state: Session state wrapper
        is_deployed: Whether running on Streamlit Cloud
        disabled: Whether all controls should be disabled (e.g. during processing)

    Returns:
        Resolved audio file path (uploaded or local)
    """
    with st.container(border=True):
        st.subheader("Audio", anchor=None)

        if state.demo_mode:
            st.info(f"🎬 **Demo Mode:** Using `{DEMO_AUDIO.name}`")
            if DEMO_AUDIO.exists():
                st.audio(str(DEMO_AUDIO))
            else:
                st.error("Demo audio not found. Run `make download-demo`.")

            if st.button("✕ Switch to Manual Upload", key="exit_demo_audio", use_container_width=True, disabled=disabled):
                state.demo_mode = False
                state.clear_results()
                st.rerun()
            return str(DEMO_AUDIO)

        if is_deployed:
            # Deployed: file upload only
            st.markdown("**Upload audio file**")
            uploaded_audio = st.file_uploader(
                "Drag and drop or click to upload",
                type=["wav", "mp3"],
                key="audio_upload",
                label_visibility="collapsed",
                help="Maximum 200MB • WAV / MP3",
                disabled=disabled,
            )
            if uploaded_audio:
                return uploaded_audio.name
            return ""
        else:
            # Local: upload + file picker
            col_upload, col_path = st.columns([1.5, 2.5])

            with col_upload:
                st.markdown("**Upload audio file**")
                uploaded_audio = st.file_uploader(
                    "Drag and drop or click",
                    type=["wav", "mp3"],
                    key="audio_upload",
                    label_visibility="collapsed",
                    help="Maximum 200MB • WAV / MP3",
                    disabled=disabled,
                )

            with col_path:
                st.markdown("**Or paste path**")
                col_text, col_btn = st.columns([4, 1])
                with col_btn:
                    if st.button("📁", key="pick_audio", help="Browse for audio file", use_container_width=True, disabled=disabled):
                        picked = pick_audio_file()
                        if picked:
                            state.audio_path = picked
                            st.rerun()
                with col_text:
                    audio_path = st.text_input(
                        "Audio path",
                        placeholder="/Volumes/Drives/Music...",
                        key="audio_path",
                        label_visibility="collapsed",
                        help="Absolute path on your machine.",
                        disabled=disabled,
                    )

            if uploaded_audio:
                return uploaded_audio.name
            return audio_path


def video_input_component(state: SessionState, is_deployed: bool, disabled: bool = False) -> str:
    """Video clips input with deploy-aware fallback.

    Args:
        state: Session state wrapper
        is_deployed: Whether running on Streamlit Cloud
        disabled: Whether all controls should be disabled (e.g. during processing)

    Returns:
        Resolved video directory path
    """
    with st.container(border=True):
        st.subheader("Video Clips", anchor=None)

        if state.demo_mode:
            st.info("🎬 **Demo Mode:** Using sample footage gallery")

            if DEMO_CLIPS.exists():
                clips = get_cached_clips(str(DEMO_CLIPS))
                if clips:
                    # Show a gallery of thumbnails
                    cols = st.columns(min(len(clips), 4))
                    for idx, clip in enumerate(clips):
                        with cols[idx % 4]:
                            if clip.thumbnail_data:
                                st.image(clip.thumbnail_data, use_container_width=True)
                            st.caption(f"Clip {idx+1}")
                    st.caption(f"Total: {len(clips)} demo clips loaded.")
                else:
                    st.warning("No demo clips found in demo/clips/")
            else:
                st.error("Demo directory not found.")

            if st.button("✕ Switch to Manual Upload", key="exit_demo_video", use_container_width=True, disabled=disabled):
                state.demo_mode = False
                state.clear_results()
                st.rerun()
            return str(DEMO_CLIPS)

        if is_deployed:
            # Deployed: file upload only
            st.markdown("**Upload video files**")
            st.file_uploader(
                "Drag and drop or click to upload",
                type=["mp4", "mov", "avi", "mkv"],
                key="video_upload",
                accept_multiple_files=True,
                label_visibility="collapsed",
                help="Maximum 200MB per file • MP4 / MOV / AVI / MKV",
                disabled=disabled,
            )
            st.caption("Upload your video clips to get started.")
            return ""
        else:
            # Local: upload + folder picker
            col_upload, col_path = st.columns([1.5, 2.5])

            with col_upload:
                st.markdown("**Upload video files**")
                st.file_uploader(
                    "Drag and drop or click",
                    type=["mp4", "mov", "avi", "mkv"],
                    key="video_upload",
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                    help="Maximum 200MB per file • MP4 / MOV / AVI / MKV",
                    disabled=disabled,
                )

            with col_path:
                st.markdown("**Or paste path**")
                col_text, col_btn = st.columns([4, 1])
                with col_btn:
                    if st.button("📁", key="pick_video", help="Browse for video clips folder", use_container_width=True, disabled=disabled):
                        picked = pick_folder("Select folder containing video clips")
                        if picked:
                            state.video_dir = picked
                            st.rerun()
                with col_text:
                    video_path = st.text_input(
                        "Footage folder",
                        placeholder="/Users/Artist/Documents/Project_01/Raw",
                        key="video_dir",
                        label_visibility="collapsed",
                        help="Terra will auto-index and categorize by motion intensity.",
                        disabled=disabled,
                    )

            st.caption("Upload individual video files or select the root directory containing your dance footage.")
            return video_path


def broll_input_component(state: SessionState, is_deployed: bool, disabled: bool = False) -> str:
    """B-roll folder input with deploy-aware fallback.

    Args:
        state: Session state wrapper
        is_deployed: Whether running on Streamlit Cloud
        disabled: Whether all controls should be disabled (e.g. during processing)

    Returns:
        Resolved B-roll directory path (empty if not available or not set)
    """
    with st.container(border=True):
        st.subheader("B-roll", anchor=None)
        st.caption("OPTIONAL — Add texture clips, atmospheric shots, or environment b-roll to be used as transitions and overlays during musical swells.")

        if not is_deployed:
            col_path, col_btn = st.columns([4, 1])
            with col_btn:
                if st.button("📁", key="pick_broll", help="Browse for B-roll folder", use_container_width=True, disabled=disabled):
                    picked = pick_folder("Select B-roll folder")
                    if picked:
                        state.broll_dir = picked
                        st.rerun()
            with col_path:
                broll_path = st.text_input(
                    "Overlays folder",
                    placeholder="/Users/Artist/Documents/Stock/Atmosph",
                    key="broll_dir",
                    help="Auto-detected as a 'broll/' subfolder inside the clips folder if it exists.",
                    disabled=disabled,
                )
            return broll_path
        else:
            st.info("💡 B-roll support is available when running locally. Include B-roll files with your video uploads for now.")
            return ""


def output_input_component(state: SessionState, is_deployed: bool, disabled: bool = False) -> str:
    """Output file input with deploy-aware fallback.

    Args:
        state: Session state wrapper
        is_deployed: Whether running on Streamlit Cloud
        disabled: Whether all controls should be disabled (e.g. during processing)

    Returns:
        Resolved output file path
    """
    with st.container(border=True):
        st.subheader("Output", anchor=None)

        if is_deployed:
            # Deployed: simple filename only
            output_path = st.text_input(
                "Output filename",
                key="output_path",
                help="Your finished video will be available to download.",
                placeholder="output_story.mp4",
                value="output_story.mp4",
                disabled=disabled,
            )
            return output_path
        else:
            # Local: full path picker
            col_path, col_btn = st.columns([4, 1])
            with col_btn:
                if st.button("📁", key="pick_output", help="Browse and save output video", use_container_width=True, disabled=disabled):
                    picked = pick_output_file()
                    if picked:
                        state.output_path = picked
                        st.rerun()
            with col_path:
                output_path = st.text_input(
                    "Save as",
                    key="output_path",
                    help="Where to save the finished video.",
                    placeholder="output_story.mp4",
                    disabled=disabled,
                )
            return output_path

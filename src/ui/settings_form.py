"""Advanced settings and run controls for the Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from src.adapters.backend import get_genres, get_intro_effects, get_transitions
from src.state.session import SessionState
from src.ui.inputs import broll_input_component, output_input_component


@dataclass(slots=True)
class GenerationSettings:
    """Collected advanced settings from the Streamlit form."""

    genre_choice: str = "(none)"
    video_style: str = "none"
    transition_type: str = "none"
    intro_effect: str = "none"
    test_mode: bool = False
    max_clips_input: int = 0
    max_duration_input: int = 0
    dry_run: bool = False
    export_report: bool = False
    speed_ramp_organic: bool = False
    speed_ramp_sensitivity: float = 1.0
    speed_ramp_curve: str = "ease_in_out"
    speed_ramp_min: float = 0.8
    speed_ramp_max: float = 1.3
    pacing_drift_zoom: bool = False
    pacing_crop_tighten: bool = False
    pacing_saturation_pulse: bool = False
    pacing_micro_jitters: bool = False
    pacing_light_leaks: bool = False
    pacing_warm_wash: bool = False
    pacing_alternating_bokeh: bool = False
    text_overlay_enabled: bool = False
    track_artist: str = ""
    track_title: str = ""
    cold_open_enabled: bool = True
    lyrics_overlay_enabled: bool = True


def _render_section_label(label: str) -> None:
    st.markdown(
        "<span style=\"font-family:'IBM Plex Mono',monospace;"
        "font-size:0.68rem;letter-spacing:2px;color:#FDB833;"
        f'text-transform:uppercase;">{label}</span>',
        unsafe_allow_html=True,
    )


def render_advanced_settings(
    state: SessionState,
    is_deployed: bool,
    controls_disabled: bool,
) -> tuple[GenerationSettings, str, str]:
    """Render advanced settings and return captured values."""
    if state.demo_mode:
        return GenerationSettings(), "", ""

    with st.expander(
        "Advanced Settings — Visual Style, Effects & Limits", expanded=False
    ):
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            _render_section_label("Visual Style")
            genre_choice = st.selectbox(
                "Genre preset",
                options=get_genres(),
                help=(
                    "Applies tuned clip pacing, colour grade and transitions "
                    "for a genre."
                ),
                disabled=controls_disabled,
            )
            video_style = st.selectbox(
                "Colour grade",
                options=["none", "bw", "vintage", "warm", "cool", "golden"],
                help="Colour grading applied to every segment.",
                disabled=controls_disabled,
            )
            transition_type = st.selectbox(
                "Transition type",
                options=get_transitions(),
                help="FFmpeg xfade: none, fade, wipeleft, wiperight, slideup, …",
                disabled=controls_disabled,
            )
            intro_effect = st.selectbox(
                "Intro effect",
                options=get_intro_effects(),
                help="Visual effect applied to the very first clip.",
                disabled=controls_disabled,
            )

        with col_s2:
            _render_section_label("Limits & Output")
            test_mode = st.checkbox(
                "Test mode (4 clips, 10s)",
                value=False,
                help="Restrict to 4 clips and 10s — good for quick checks.",
                disabled=controls_disabled,
            )
            max_clips_input = st.number_input(
                "Max clips (0 = unlimited)",
                min_value=0,
                value=0,
                step=1,
                disabled=controls_disabled,
            )
            max_duration_input = st.number_input(
                "Max duration in seconds (0 = unlimited)",
                min_value=0,
                value=0,
                step=5,
                disabled=controls_disabled,
            )
            dry_run = st.checkbox(
                "Dry run (plan only, no render)",
                value=False,
                help="Analyse and plan without rendering.",
                disabled=controls_disabled,
            )
            export_report = st.checkbox(
                "Export Excel report",
                value=False,
                help="Generate analysis.xlsx alongside video.",
                disabled=controls_disabled,
            )

        _render_section_label("B-roll & Output")
        broll_dir_input = broll_input_component(
            state,
            is_deployed,
            disabled=controls_disabled,
        )
        output_path = output_input_component(
            state,
            is_deployed,
            disabled=controls_disabled,
        )

        _render_section_label("Advanced Effects")
        speed_settings = _render_speed_ramping(controls_disabled)
        beat_effects = _render_beat_effects(controls_disabled)
        text_overlay = _render_text_overlay_settings(controls_disabled)

    settings = GenerationSettings(
        genre_choice=genre_choice,
        video_style=video_style,
        transition_type=transition_type,
        intro_effect=intro_effect,
        test_mode=test_mode,
        max_clips_input=int(max_clips_input),
        max_duration_input=int(max_duration_input),
        dry_run=dry_run,
        export_report=export_report,
        **speed_settings,
        **beat_effects,
        **text_overlay,
    )
    return settings, broll_dir_input, output_path


def _render_speed_ramping(controls_disabled: bool) -> dict[str, object]:
    st.markdown("**Speed Ramping**")
    speed_ramp_organic = st.checkbox(
        "Organic per-beat speed",
        value=False,
        help="Variable speed within clips driven by beat-by-beat intensity.",
        disabled=controls_disabled,
    )
    if not speed_ramp_organic:
        return {
            "speed_ramp_organic": False,
            "speed_ramp_sensitivity": 1.0,
            "speed_ramp_curve": "ease_in_out",
            "speed_ramp_min": 0.8,
            "speed_ramp_max": 1.3,
        }

    speed_ramp_sensitivity = st.slider(
        "Sensitivity",
        min_value=0.3,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="0.5=gentle, 1.0=standard, 2.0=aggressive",
        disabled=controls_disabled,
    )
    speed_ramp_curve = st.selectbox(
        "Curve type",
        options=["linear", "ease_in", "ease_out", "ease_in_out"],
        help="Smoothing function for speed transitions",
        disabled=controls_disabled,
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
            disabled=controls_disabled,
        )
    with col_speed_max:
        speed_ramp_max = st.number_input(
            "Max speed",
            min_value=1.0,
            max_value=2.0,
            value=1.3,
            step=0.1,
            help="Fastest multiplier (high-energy beats)",
            disabled=controls_disabled,
        )

    return {
        "speed_ramp_organic": True,
        "speed_ramp_sensitivity": float(speed_ramp_sensitivity),
        "speed_ramp_curve": speed_ramp_curve,
        "speed_ramp_min": float(speed_ramp_min),
        "speed_ramp_max": float(speed_ramp_max),
    }


def _render_beat_effects(controls_disabled: bool) -> dict[str, bool]:
    st.markdown("**Beat-Synced Effects**")
    return {
        "pacing_drift_zoom": st.checkbox(
            "Drift zoom (Ken Burns)",
            value=False,
            disabled=controls_disabled,
        ),
        "pacing_crop_tighten": st.checkbox(
            "Crop tighten",
            value=False,
            disabled=controls_disabled,
        ),
        "pacing_saturation_pulse": st.checkbox(
            "Saturation pulse on beats",
            value=False,
            disabled=controls_disabled,
        ),
        "pacing_micro_jitters": st.checkbox(
            "Micro-jitters on beats",
            value=False,
            disabled=controls_disabled,
        ),
        "pacing_light_leaks": st.checkbox(
            "Light leaks on beats",
            value=False,
            disabled=controls_disabled,
        ),
        "pacing_warm_wash": st.checkbox(
            "Warm wash at transitions",
            value=False,
            disabled=controls_disabled,
        ),
        "pacing_alternating_bokeh": st.checkbox(
            "Alternating bokeh blur",
            value=False,
            disabled=controls_disabled,
        ),
    }


def _render_text_overlay_settings(controls_disabled: bool) -> dict[str, object]:
    _render_section_label("Text Overlays")
    text_overlay_enabled = st.checkbox(
        "Enable text overlays",
        value=False,
        help="Burn timed text into the video: cinematic cold open and/or LRC lyrics.",
        disabled=controls_disabled,
    )
    if not text_overlay_enabled:
        return {
            "text_overlay_enabled": False,
            "track_artist": "",
            "track_title": "",
            "cold_open_enabled": True,
            "lyrics_overlay_enabled": True,
        }

    col_to1, col_to2 = st.columns(2)
    with col_to1:
        track_artist = st.text_input(
            "Artist name",
            value="",
            help="Shown in the lower-third at the start of the video.",
            disabled=controls_disabled,
        )
        track_title = st.text_input(
            "Song title",
            value="",
            help="Shown alongside the artist name in the lower-third.",
            disabled=controls_disabled,
        )
    with col_to2:
        cold_open_enabled = st.checkbox(
            "Cinematic cold open",
            value=True,
            help="Scene-setter wash text (0–4s) and artist/title lower-third (4–7s).",
            disabled=controls_disabled,
        )
        lyrics_overlay_enabled = st.checkbox(
            "LRC lyrics",
            value=True,
            help=(
                "Show synced lyrics burned into the video. "
                "Auto-discovers {audio_stem}.lrc next to the audio file."
            ),
            disabled=controls_disabled,
        )

    return {
        "text_overlay_enabled": True,
        "track_artist": track_artist,
        "track_title": track_title,
        "cold_open_enabled": cold_open_enabled,
        "lyrics_overlay_enabled": lyrics_overlay_enabled,
    }


def render_run_controls(state: SessionState) -> bool:
    """Render the generate/cancel controls and return a run trigger."""
    if state.demo_mode:
        return False

    st.markdown("---")
    col_spacer1, col_run, col_spacer2 = st.columns([1.5, 2, 1.5])
    with col_run:
        if state.is_running:
            if st.button(
                "Cancel",
                type="secondary",
                use_container_width=True,
                help="Stop the current processing run.",
            ):
                state.is_running = False
                state.error = "Run cancelled by user."
                st.rerun()
            return False

        return st.button(
            "▶  Generate Montage",
            type="primary",
            use_container_width=True,
            help=(
                "Process audio and video clips. This may take several minutes "
                "depending on video length."
            ),
        )

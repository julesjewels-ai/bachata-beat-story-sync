"""Typed request-building helpers for the Streamlit UI."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.state.session import SessionState
from src.ui.inputs import DEMO_AUDIO, DEMO_CLIPS
from src.ui.settings_form import GenerationSettings


@dataclass(slots=True)
class PreparedRunRequest:
    """Resolved inputs for a Streamlit-triggered generation run."""

    audio_path: str
    video_dir: str
    broll_dir: str | None
    output_path: str
    pacing_kwargs: dict[str, Any]
    report_path: str | None


def should_trigger_demo_run(state: SessionState) -> bool:
    """Return True when demo mode should auto-start a run."""
    return (
        state.demo_mode
        and state.result_path is None
        and state.plan_report is None
        and state.error is None
        and not state.is_running
        and st.session_state.get("_demo_dry_run") is not None
    )


def prepare_run_request(
    state: SessionState,
    settings: GenerationSettings,
    audio_path_text: str,
    video_dir: str,
    broll_dir_input: str,
    output_path: str,
) -> tuple[PreparedRunRequest | None, list[str]]:
    """Resolve user inputs into a background-run request."""
    resolved_inputs, errors = _resolve_inputs(
        state,
        audio_path_text,
        video_dir,
        broll_dir_input,
    )
    if errors:
        return None, errors

    pacing_kwargs = build_pacing_kwargs(
        settings,
        demo_mode=state.demo_mode,
        demo_dry_run=bool(st.session_state.get("_demo_dry_run", False)),
    )
    output_path_resolved, report_path = resolve_output_targets(
        state,
        settings,
        output_path,
        pacing_kwargs,
    )
    return (
        PreparedRunRequest(
            audio_path=resolved_inputs.audio_path,
            video_dir=resolved_inputs.video_dir,
            broll_dir=resolved_inputs.broll_dir,
            output_path=output_path_resolved,
            pacing_kwargs=pacing_kwargs,
            report_path=report_path,
        ),
        [],
    )


@dataclass(slots=True)
class _ResolvedInputs:
    audio_path: str
    video_dir: str
    broll_dir: str | None


def _resolve_inputs(
    state: SessionState,
    audio_path_text: str,
    video_dir: str,
    broll_dir_input: str,
) -> tuple[_ResolvedInputs | None, list[str]]:
    errors: list[str] = []

    if state.demo_mode:
        return (
            _ResolvedInputs(
                audio_path=str(DEMO_AUDIO),
                video_dir=str(DEMO_CLIPS),
                broll_dir=None,
            ),
            [],
        )

    resolved_audio_path = _resolve_audio_path(audio_path_text, errors)
    resolved_video_dir = _resolve_video_dir(video_dir, errors)
    broll_dir_resolved = (broll_dir_input or "").strip() or None
    if broll_dir_resolved and not os.path.isdir(broll_dir_resolved):
        errors.append(f"B-roll folder not found: {broll_dir_resolved}")

    if errors or resolved_audio_path is None or resolved_video_dir is None:
        return None, errors

    return (
        _ResolvedInputs(
            audio_path=resolved_audio_path,
            video_dir=resolved_video_dir,
            broll_dir=broll_dir_resolved,
        ),
        [],
    )


def _resolve_audio_path(audio_path_text: str, errors: list[str]) -> str | None:
    uploaded_audio = st.session_state.get("audio_upload")
    if uploaded_audio is not None:
        suffix = os.path.splitext(uploaded_audio.name)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(uploaded_audio.read())
        tmp.close()
        return tmp.name

    audio_path = audio_path_text.strip()
    if not audio_path:
        errors.append("Please provide an audio file path or upload a file.")
        return None
    if not os.path.exists(audio_path):
        errors.append(f"Audio file not found: {audio_path}")
        return None
    return audio_path


def _resolve_video_dir(video_dir: str, errors: list[str]) -> str | None:
    uploaded_videos = st.session_state.get("video_upload") or []
    if uploaded_videos:
        temp_video_dir = tempfile.mkdtemp(prefix="bachata_videos_")
        for uploaded_file in uploaded_videos:
            file_path = os.path.join(temp_video_dir, uploaded_file.name)
            with open(file_path, "wb") as file_handle:
                file_handle.write(uploaded_file.read())
        return temp_video_dir

    resolved_video_dir = video_dir.strip()
    if not resolved_video_dir:
        errors.append(
            "Please upload video files or enter the path to your video clips folder."
        )
        return None
    if not os.path.isdir(resolved_video_dir):
        errors.append(f"Video clips folder not found: {resolved_video_dir}")
        return None
    return resolved_video_dir


def build_pacing_kwargs(
    settings: GenerationSettings,
    *,
    demo_mode: bool,
    demo_dry_run: bool,
) -> dict[str, Any]:
    """Translate UI settings into story workflow pacing overrides."""
    pacing_kwargs: dict[str, Any] = {}

    if settings.genre_choice != "(none)":
        pacing_kwargs["genre"] = settings.genre_choice
    if settings.video_style != "none":
        pacing_kwargs["video_style"] = settings.video_style
    if settings.transition_type.strip() and settings.transition_type.strip() != "none":
        pacing_kwargs["transition_type"] = settings.transition_type.strip()
    if settings.intro_effect != "none":
        pacing_kwargs["intro_effect"] = settings.intro_effect

    if demo_mode:
        if demo_dry_run:
            pacing_kwargs["dry_run"] = True
        pacing_kwargs["max_clips"] = 6
        pacing_kwargs["max_duration_seconds"] = 20.0
        pacing_kwargs["text_overlay_enabled"] = True
        pacing_kwargs["cold_open_enabled"] = True
        pacing_kwargs["track_artist"] = "Sample Artist"
        pacing_kwargs["track_title"] = "Sample Bachata"
    elif settings.dry_run:
        pacing_kwargs["dry_run"] = True

    if settings.speed_ramp_organic:
        pacing_kwargs["speed_ramp_organic"] = True
        pacing_kwargs["speed_ramp_sensitivity"] = settings.speed_ramp_sensitivity
        pacing_kwargs["speed_ramp_curve"] = settings.speed_ramp_curve
        pacing_kwargs["speed_ramp_min"] = settings.speed_ramp_min
        pacing_kwargs["speed_ramp_max"] = settings.speed_ramp_max

    for field_name in (
        "pacing_drift_zoom",
        "pacing_crop_tighten",
        "pacing_saturation_pulse",
        "pacing_micro_jitters",
        "pacing_light_leaks",
        "pacing_warm_wash",
        "pacing_alternating_bokeh",
    ):
        if getattr(settings, field_name):
            pacing_kwargs[field_name] = True

    if not demo_mode and settings.text_overlay_enabled:
        pacing_kwargs["text_overlay_enabled"] = True
        if not settings.cold_open_enabled:
            pacing_kwargs["cold_open_enabled"] = False
        if not settings.lyrics_overlay_enabled:
            pacing_kwargs["lyrics_overlay_enabled"] = False
        if settings.track_artist.strip():
            pacing_kwargs["track_artist"] = settings.track_artist.strip()
        if settings.track_title.strip():
            pacing_kwargs["track_title"] = settings.track_title.strip()

    if not demo_mode:
        effective_max_clips: int | None = None
        effective_max_duration: float | None = None
        if settings.test_mode:
            effective_max_clips = 4
            effective_max_duration = 10.0
        if settings.max_clips_input > 0:
            effective_max_clips = settings.max_clips_input
        if settings.max_duration_input > 0:
            effective_max_duration = float(settings.max_duration_input)
        if effective_max_clips is not None:
            pacing_kwargs["max_clips"] = effective_max_clips
        if effective_max_duration is not None:
            pacing_kwargs["max_duration_seconds"] = effective_max_duration

    return pacing_kwargs


def resolve_output_targets(
    state: SessionState,
    settings: GenerationSettings,
    output_path: str,
    pacing_kwargs: dict[str, Any],
) -> tuple[str, str | None]:
    """Resolve output video and optional report paths."""
    if state.demo_mode and not pacing_kwargs.get("dry_run"):
        demo_tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix="_demo.mp4",
            prefix="bachata_",
        )
        demo_tmp.close()
        output_path_resolved = demo_tmp.name
    else:
        output_path_resolved = output_path.strip()

    report_path: str | None = None
    if settings.export_report:
        base, _ = os.path.splitext(output_path_resolved)
        report_path = base + "_report.xlsx"
    return output_path_resolved, report_path

"""Rendering helpers for montage execution after planning completes."""

from __future__ import annotations

import logging
import os
import re
import shutil
from dataclasses import dataclass
from typing import Any

from src.core.interfaces import ProgressObserver
from src.core.models import AudioAnalysisResult, PacingConfig, SegmentPlan
from src.core.pacing_views import OverlayConfig, PlanningConfig, RenderConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MontageRenderOps:
    """Injected rendering operations used by the montage executor."""

    extract_segments: Any
    concatenate_segments: Any
    apply_transitions: Any
    get_video_duration: Any
    normalize_video_duration: Any
    fill_tail_gap: Any
    overlay_audio: Any
    apply_text_overlay: Any
    temp_dir_factory: Any
    cleanup_dir: Any
    path_exists: Any


def group_segments_by_section(
    segments: list[SegmentPlan],
) -> list[list[SegmentPlan]]:
    """Group consecutive segments that share the same section label."""
    if not segments:
        return []

    groups: list[list[SegmentPlan]] = []
    current_group: list[SegmentPlan] = [segments[0]]

    for segment in segments[1:]:
        if segment.section_label == current_group[-1].section_label:
            current_group.append(segment)
        else:
            groups.append(current_group)
            current_group = [segment]

    groups.append(current_group)
    return groups


def _assemble_video_segments(
    segments: list[SegmentPlan],
    segment_files: list[str],
    temp_dir: str,
    render_config: RenderConfig,
    ops: MontageRenderOps,
) -> str:
    """Concatenate extracted segments, applying transitions if enabled."""
    concat_path = os.path.join(temp_dir, "concat_output.mp4")
    transitions_enabled = (
        render_config.transition_type
        and render_config.transition_type.lower() != "none"
    )

    if not transitions_enabled:
        ops.concatenate_segments(segment_files, concat_path)
        return concat_path

    groups = group_segments_by_section(segments)
    if len(groups) <= 1:
        ops.concatenate_segments(segment_files, concat_path)
        return concat_path

    group_files = []
    file_idx = 0
    for group_idx, group in enumerate(groups):
        group_segment_files = segment_files[file_idx : file_idx + len(group)]
        file_idx += len(group)

        if len(group_segment_files) == 1:
            group_files.append(group_segment_files[0])
        else:
            group_out = os.path.join(temp_dir, f"group_{group_idx:04d}.mp4")
            ops.concatenate_segments(group_segment_files, group_out)
            group_files.append(group_out)

    ops.apply_transitions(
        group_files,
        concat_path,
        render_config.transition_type,
        render_config.transition_duration,
        warm_wash=render_config.pacing_warm_wash,
    )
    return concat_path


def _verify_and_correct_duration(
    concat_path: str,
    segment_files: list[str],
    output_target_duration: float,
    temp_dir: str,
    config: PacingConfig,
    ops: MontageRenderOps,
) -> tuple[str, float]:
    """Check assembled duration and fill gap or normalize if necessary."""
    video_dur = ops.get_video_duration(concat_path)
    if output_target_duration <= 0 or video_dur <= 0:
        return concat_path, video_dur

    delta = abs(video_dur - output_target_duration)
    signed_delta = output_target_duration - video_dur
    logger.info(
        "Pre-overlay duration check: rendered=%.3fs target=%.3fs "
        "delta=%+.3fs tolerance=%.3fs",
        video_dur,
        output_target_duration,
        signed_delta,
        config.duration_sync_tolerance_seconds,
    )

    if delta > config.duration_sync_tolerance_seconds:
        raise RuntimeError(
            "Assembled video duration mismatch before audio overlay: "
            f"rendered={video_dur:.3f}s target={output_target_duration:.3f}s "
            f"delta={delta:.3f}s"
        )

    if delta <= 1e-3:
        return concat_path, video_dur

    if signed_delta > 0:
        tail_filled = os.path.join(temp_dir, "concat_output.tail_filled.mp4")
        filled = ops.fill_tail_gap(
            concat_path,
            segment_files,
            signed_delta,
            temp_dir,
            tail_filled,
        )
        if filled:
            concat_path = tail_filled
            video_dur = ops.get_video_duration(concat_path)
            delta = abs(video_dur - output_target_duration)

    if delta > 1e-3:
        normalized_concat = os.path.join(temp_dir, "concat_output.normalized.mp4")
        ops.normalize_video_duration(
            concat_path,
            normalized_concat,
            output_target_duration,
            actual_duration=video_dur,
        )
        concat_path = normalized_concat
        video_dur = ops.get_video_duration(concat_path)
        normalized_delta = abs(video_dur - output_target_duration)
        if normalized_delta > config.duration_sync_tolerance_seconds:
            raise RuntimeError(
                "Normalized video duration mismatch before audio overlay: "
                f"rendered={video_dur:.3f}s "
                f"target={output_target_duration:.3f}s "
                f"delta={normalized_delta:.3f}s"
            )

    return concat_path, video_dur


def _apply_audio_overlay(
    concat_path: str,
    output_path: str,
    audio_path: str | None,
    segments: list[SegmentPlan],
    video_dur: float,
    output_target_duration: float,
    overlay_config: OverlayConfig,
    ops: MontageRenderOps,
) -> None:
    """Overlay audio if provided; otherwise, just move the video."""
    if not (audio_path and ops.path_exists(audio_path)):
        shutil.move(concat_path, output_path)
        return

    intro_duration = 0.0
    if segments:
        first_seg = segments[0]
        basename = os.path.basename(first_seg.video_path)
        if re.match(r"^(\d+)_", basename):
            intro_duration = first_seg.duration

    ops.overlay_audio(
        concat_path,
        audio_path,
        output_path,
        overlay_config,
        video_duration=video_dur,
        target_duration=output_target_duration,
        intro_duration=intro_duration,
    )


def _apply_text_and_post_process(
    output_path: str,
    audio_path: str | None,
    config: PacingConfig,
    render_config: RenderConfig,
    output_target_duration: float,
    ops: MontageRenderOps,
) -> None:
    """Apply text events (and mix fades) and verify final duration."""
    wants_mix_fades = render_config.mix_fade_transitions and bool(
        render_config.mix_track_segments
    )
    if render_config.text_overlay_enabled or wants_mix_fades:
        from src.core.text_overlay import build_text_events  # noqa: WPS433

        text_events = (
            build_text_events(config, audio_path)
            if render_config.text_overlay_enabled
            else []
        )
        if text_events or wants_mix_fades:
            if os.path.isfile(output_path):
                pre_text = output_path + ".pre_text.mp4"
                shutil.move(output_path, pre_text)
                try:
                    ops.apply_text_overlay(
                        pre_text,
                        output_path,
                        text_events,
                        render_config,
                    )
                finally:
                    if ops.path_exists(pre_text):
                        os.remove(pre_text)
            else:
                logger.warning(
                    "Skipping text overlay post-pass because %s was not created.",
                    output_path,
                )

    output_dur = ops.get_video_duration(output_path)
    if output_target_duration > 0 and output_dur > 0:
        delta = abs(output_dur - output_target_duration)
        if delta > config.duration_sync_tolerance_seconds:
            raise RuntimeError(
                "Output duration mismatch after post-processing: "
                f"rendered={output_dur:.3f}s target={output_target_duration:.3f}s "
                f"delta={delta:.3f}s"
            )
        logger.debug(
            "Duration check OK: rendered=%.2fs  target=%.2fs  delta=%.2fs",
            output_dur,
            output_target_duration,
            delta,
        )


def render_montage(
    *,
    segments: list[SegmentPlan],
    audio_data: AudioAnalysisResult,
    output_path: str,
    audio_path: str | None,
    observer: ProgressObserver | None,
    config: PacingConfig,
    planning_config: PlanningConfig,
    render_config: RenderConfig,
    overlay_config: OverlayConfig,
    output_target_duration: float,
    ops: MontageRenderOps,
) -> str:
    """Render a planned montage using the injected FFmpeg operations."""
    temp_dir = ops.temp_dir_factory(prefix="montage_")

    try:
        segment_files = ops.extract_segments(
            segments,
            temp_dir,
            render_config,
            observer,
            beat_times=audio_data.beat_times,
        )

        concat_path = _assemble_video_segments(
            segments,
            segment_files,
            temp_dir,
            render_config,
            ops,
        )

        concat_path, video_dur = _verify_and_correct_duration(
            concat_path,
            segment_files,
            output_target_duration,
            temp_dir,
            config,
            ops,
        )

        _apply_audio_overlay(
            concat_path,
            output_path,
            audio_path,
            segments,
            video_dur,
            output_target_duration,
            overlay_config,
            ops,
        )

        _apply_text_and_post_process(
            output_path,
            audio_path,
            config,
            render_config,
            output_target_duration,
            ops,
        )

        logger.info(
            "Montage render complete: %s (target_duration=%.3fs)",
            output_path,
            output_target_duration,
        )
        return output_path

    finally:
        ops.cleanup_dir(temp_dir, ignore_errors=True)

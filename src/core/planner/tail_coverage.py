"""Audio tail coverage helpers for segment planning."""

from __future__ import annotations

import logging
from collections.abc import Callable

from src.core.models import (
    AudioAnalysisResult,
    MusicalSection,
    SegmentDecision,
    SegmentPlan,
    VideoAnalysisResult,
)
from src.core.pacing_views import PlanningConfig


def append_tail_segment(
    *,
    segments: list[SegmentPlan],
    audio_data: AudioAnalysisResult,
    timeline_pos: float,
    config: PlanningConfig,
    pools: dict[str, list[VideoAnalysisResult]],
    pool_indices: dict[str, int],
    sorted_clips: list[VideoAnalysisResult],
    pick_from_pool: Callable[
        [dict[str, list[VideoAnalysisResult]], dict[str, int], str],
        VideoAnalysisResult,
    ],
    find_section_label: Callable[[list[MusicalSection], float], str | None],
    record_decision: Callable[[SegmentDecision], None] | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """Cover any audio tail that falls after the last detected beat."""
    log = logger or logging.getLogger(__name__)

    tail_uncovered = audio_data.duration - timeline_pos
    log.debug(
        "_append_tail_segment: tail_uncovered=%.2fs, max_dur=%s, "
        "max_clips=%s, sorted_clips=%d",
        tail_uncovered,
        config.max_duration_seconds,
        config.max_clips,
        len(sorted_clips) if sorted_clips else 0,
    )

    if not (
        tail_uncovered > 0.15  # ignore sub-frame gaps
        and config.max_duration_seconds is None
        and config.max_clips is None
        and sorted_clips
    ):
        log.debug(
            "SKIP tail: uncovered>0.15=%s, max_dur_none=%s, "
            "max_clips_none=%s, has_clips=%s",
            tail_uncovered > 0.15,
            config.max_duration_seconds is None,
            config.max_clips is None,
            bool(sorted_clips),
        )
        return

    tail_clip = pick_from_pool(pools, pool_indices, "low")
    # Always start from offset 0 for the tail to guarantee we have
    # enough source material regardless of clip length.
    tail_available = tail_clip.duration
    tail_duration = min(tail_uncovered, tail_available)

    log.debug(
        "Tail segment: duration=%.2fs, min_required=%.2f, will_append=%s",
        tail_duration,
        config.min_clip_seconds,
        tail_duration >= config.min_clip_seconds,
    )

    if tail_duration < config.min_clip_seconds:
        log.debug(
            "SKIP tail: duration (%.2fs) < min_clip_seconds (%.2f)",
            tail_duration,
            config.min_clip_seconds,
        )
        return

    tail_section = find_section_label(audio_data.sections or [], timeline_pos)
    tail_seg = SegmentPlan(
        video_path=tail_clip.path,
        start_time=0.0,
        duration=tail_duration,
        clip_duration=tail_clip.duration,
        timeline_position=timeline_pos,
        intensity_level="low",
        speed_factor=1.0,
        section_label=tail_section,
    )
    segments.append(tail_seg)
    log.debug(
        "APPENDED tail segment: %.2fs (was uncovered %.2fs), total_segments=%d",
        tail_duration,
        tail_uncovered,
        len(segments),
    )
    if config.explain and record_decision is not None:
        record_decision(
            SegmentDecision(
                timeline_start=timeline_pos,
                clip_path=tail_clip.path,
                intensity_score=tail_clip.intensity_score,
                section_label=tail_section,
                duration=tail_duration,
                speed=1.0,
                reason="Tail coverage: audio after last beat",
            )
        )
    log.debug(
        "Tail coverage: added %.2fs segment at %.2fs to reach audio end",
        tail_duration,
        timeline_pos,
    )

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
    target_duration: float,
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
    target_level: str = "low",
    speed_factor: float = 1.0,
    min_recovery_seconds: float = 0.25,
    sync_tolerance: float = 0.10,
    max_tail_segments: int = 512,
    logger: logging.Logger | None = None,
) -> float:
    """Cover any uncovered tail until timeline reaches ``target_duration``."""
    log = logger or logging.getLogger(__name__)
    level_target_seconds = {
        "high": config.high_intensity_seconds,
        "medium": config.medium_intensity_seconds,
        "low": config.low_intensity_seconds,
    }
    target_segment_seconds = level_target_seconds.get(
        target_level,
        config.low_intensity_seconds,
    )
    target_segment_seconds = max(target_segment_seconds, config.min_clip_seconds)

    current_timeline = timeline_pos
    tail_uncovered = target_duration - current_timeline
    log.debug(
        "_append_tail_segment: tail_uncovered=%.2fs, target=%.2fs, max_dur=%s, "
        "max_clips=%s, sorted_clips=%d",
        tail_uncovered,
        target_duration,
        config.max_duration_seconds,
        config.max_clips,
        len(sorted_clips) if sorted_clips else 0,
    )

    if not sorted_clips or target_duration <= 0:
        log.debug(
            "SKIP tail: target_duration=%.2fs has_clips=%s",
            target_duration,
            bool(sorted_clips),
        )
        return current_timeline

    for _ in range(max_tail_segments):
        remaining = target_duration - current_timeline
        if remaining <= sync_tolerance:
            break
        if config.max_clips is not None and len(segments) >= config.max_clips:
            log.debug(
                "STOP tail: segments (%d) >= max_clips (%d)",
                len(segments),
                config.max_clips,
            )
            break

        tail_clip = pick_from_pool(pools, pool_indices, target_level)
        if tail_clip.duration <= 0:
            log.debug("SKIP tail iteration: selected clip has invalid duration")
            break

        # Always start from offset 0 for deterministic tail fill.
        tail_duration = min(remaining, tail_clip.duration, target_segment_seconds)
        min_required = min(config.min_clip_seconds, remaining)
        allow_short_terminal = remaining <= (config.min_clip_seconds + sync_tolerance)

        if tail_duration + 1e-6 < min_required and not allow_short_terminal:
            # Retry with the longest available clip before giving up.
            longest_clip = max(sorted_clips, key=lambda c: c.duration)
            tail_clip = longest_clip
            tail_duration = min(remaining, tail_clip.duration, target_segment_seconds)

        leftover_after = remaining - tail_duration
        if (
            leftover_after > sync_tolerance
            and leftover_after < config.min_clip_seconds
            and tail_clip.duration >= remaining
        ):
            tail_duration = remaining

        if tail_duration + 1e-6 < min_required and not allow_short_terminal:
            log.debug(
                "STOP tail: cannot satisfy minimum (tail=%.2fs < required=%.2fs)",
                tail_duration,
                min_required,
            )
            break

        if tail_duration < min_recovery_seconds:
            log.debug(
                "STOP tail: duration %.3fs below recovery floor %.3fs",
                tail_duration,
                min_recovery_seconds,
            )
            break

        tail_section = find_section_label(audio_data.sections or [], current_timeline)
        tail_seg = SegmentPlan(
            video_path=tail_clip.path,
            start_time=0.0,
            duration=tail_duration,
            clip_duration=tail_clip.duration,
            timeline_position=current_timeline,
            intensity_level=target_level,
            speed_factor=speed_factor,
            section_label=tail_section,
        )
        segments.append(tail_seg)
        log.debug(
            "APPENDED tail segment: %.2fs at %.2fs "
            "(remaining was %.2fs), total_segments=%d",
            tail_duration,
            current_timeline,
            remaining,
            len(segments),
        )

        if config.explain and record_decision is not None:
            record_decision(
                SegmentDecision(
                    timeline_start=current_timeline,
                    clip_path=tail_clip.path,
                    intensity_score=tail_clip.intensity_score,
                    section_label=tail_section,
                    duration=tail_duration,
                    speed=speed_factor,
                    reason="Tail coverage: iterative fill",
                )
            )

        current_timeline += tail_duration

    return current_timeline

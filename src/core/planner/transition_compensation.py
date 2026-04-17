"""Transition-overlap compensation helpers for segment planning."""

from __future__ import annotations

import logging
from collections.abc import Callable

from src.core.models import SegmentPlan


def append_transition_compensation(
    *,
    segments: list[SegmentPlan],
    timeline_pos: float,
    target_timeline_duration: float,
    build_segment: Callable[[float, float], SegmentPlan | None],
    sync_tolerance: float = 0.10,
    min_compensation_seconds: float = 1 / 30,
    max_segments: int = 128,
    logger: logging.Logger | None = None,
) -> float:
    """Append compensation segments without creating a new transition group.

    The supplied ``build_segment`` callback is responsible for choosing the
    source clip and preserving the final existing section label.
    """
    log = logger or logging.getLogger(__name__)
    current_timeline = timeline_pos

    for _ in range(max_segments):
        remaining = target_timeline_duration - current_timeline
        if remaining <= sync_tolerance:
            break

        min_required = min(min_compensation_seconds, remaining)
        allow_short_terminal = remaining <= (
            min_compensation_seconds + sync_tolerance
        )
        segment = build_segment(current_timeline, remaining)
        if segment is None:
            log.debug(
                "STOP transition compensation: no segment available (remaining=%.3fs)",
                remaining,
            )
            break

        if segment.duration <= 0:
            log.debug(
                "STOP transition compensation: non-positive duration %.3fs",
                segment.duration,
            )
            break

        if segment.duration + 1e-6 < min_required and not allow_short_terminal:
            log.debug(
                "STOP transition compensation: %.3fs below minimum %.3fs",
                segment.duration,
                min_required,
            )
            break

        segments.append(segment)
        current_timeline += segment.duration
        log.debug(
            "APPENDED transition compensation: %.3fs at %.3fs (remaining was %.3fs)",
            segment.duration,
            segment.timeline_position,
            remaining,
        )

    return current_timeline

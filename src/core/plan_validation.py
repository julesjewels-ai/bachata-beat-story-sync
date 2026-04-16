"""Segment-plan validation helpers.

Pure validation utilities that can be reused by planners, tests, and
debug/reporting layers without coupling to FFmpeg rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.models import SegmentPlan


@dataclass(frozen=True)
class SegmentPlanValidationResult:
    """Validation outcome for a generated segment plan."""

    issues: list[str] = field(default_factory=list)
    expected_duration: float = 0.0
    actual_duration: float = 0.0
    duration_delta_seconds: float = 0.0
    absolute_delta_seconds: float = 0.0
    alignment_status: str = "ok"

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_segment_plan(
    segments: list[SegmentPlan],
    *,
    expected_duration: float,
    min_clip_seconds: float,
    tolerance: float = 0.10,
) -> SegmentPlanValidationResult:
    """Validate timeline continuity and basic safety invariants.

    Args:
        segments: Planned segments in timeline order.
        expected_duration: Target timeline duration in seconds.
        min_clip_seconds: Configured minimum clip duration.
        tolerance: Allowed floating-point tolerance for timing checks.
    """
    issues: list[str] = []

    previous_end = 0.0
    total_segments = len(segments)
    for idx, seg in enumerate(segments, start=1):
        if seg.duration <= 0:
            issues.append(
                f"Segment {idx} has non-positive duration ({seg.duration:.3f}s)."
            )
        # Allow a shorter terminal segment for exact tail coverage.
        if idx < total_segments and seg.duration + tolerance < min_clip_seconds:
            issues.append(
                f"Segment {idx} is below min_clip_seconds "
                f"({seg.duration:.3f}s < {min_clip_seconds:.3f}s)."
            )
        if seg.timeline_position < -tolerance:
            issues.append(
                f"Segment {idx} has negative timeline position "
                f"({seg.timeline_position:.3f}s)."
            )

        delta = seg.timeline_position - previous_end
        if delta > tolerance:
            issues.append(
                f"Gap before segment {idx}: {delta:.3f}s "
                f"(previous_end={previous_end:.3f}s)."
            )
        elif delta < -tolerance:
            issues.append(
                f"Overlap before segment {idx}: {-delta:.3f}s "
                f"(previous_end={previous_end:.3f}s)."
            )

        previous_end = seg.timeline_position + seg.duration

    actual_duration = previous_end if segments else 0.0
    duration_delta = actual_duration - expected_duration
    absolute_delta = abs(duration_delta)
    alignment_status = (
        "over"
        if duration_delta > tolerance
        else "under"
        if duration_delta < -tolerance
        else "ok"
    )
    if expected_duration > 0:
        if duration_delta < -tolerance:
            issues.append(
                f"Plan under-covers target duration by {abs(duration_delta):.3f}s "
                f"(planned={actual_duration:.3f}s, expected={expected_duration:.3f}s)."
            )
        elif duration_delta > tolerance:
            issues.append(
                f"Plan over-covers target duration by {duration_delta:.3f}s "
                f"(planned={actual_duration:.3f}s, expected={expected_duration:.3f}s)."
            )

    return SegmentPlanValidationResult(
        issues=issues,
        expected_duration=expected_duration,
        actual_duration=actual_duration,
        duration_delta_seconds=duration_delta,
        absolute_delta_seconds=absolute_delta,
        alignment_status=alignment_status,
    )

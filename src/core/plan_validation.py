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

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_segment_plan(
    segments: list[SegmentPlan],
    *,
    expected_duration: float,
    min_clip_seconds: float,
    tolerance: float = 0.05,
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
    for idx, seg in enumerate(segments, start=1):
        if seg.duration <= 0:
            issues.append(
                f"Segment {idx} has non-positive duration ({seg.duration:.3f}s)."
            )
        if seg.duration + tolerance < min_clip_seconds:
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
    if expected_duration > 0:
        coverage_delta = expected_duration - actual_duration
        if coverage_delta > 0.5:
            issues.append(
                f"Plan under-covers target duration by {coverage_delta:.3f}s "
                f"(planned={actual_duration:.3f}s, expected={expected_duration:.3f}s)."
            )

    return SegmentPlanValidationResult(
        issues=issues,
        expected_duration=expected_duration,
        actual_duration=actual_duration,
    )

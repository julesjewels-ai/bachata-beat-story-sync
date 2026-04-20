"""Explainability helpers for montage planning decisions."""

from __future__ import annotations

import logging
import os

from src.core.models import AudioAnalysisResult, PacingConfig, SegmentDecision

logger = logging.getLogger(__name__)


def write_explain_log(
    output_path: str,
    decisions: list[SegmentDecision],
    config: PacingConfig,
) -> None:
    """Write collected decisions to a Markdown file next to the output."""
    stem = os.path.splitext(output_path)[0]
    log_path = f"{stem}_explain.md"

    lines: list[str] = [
        "# Decision Explainability Log\n",
        "",
        "## Segment Decisions\n",
        "",
        "| # | Time | Clip | Intensity | Section | Duration | Speed | Reason |",
        "|---|------|------|-----------|---------|----------|-------|--------|",
    ]
    for i, decision in enumerate(decisions, 1):
        clip_name = os.path.basename(decision.clip_path)
        section = decision.section_label or "—"
        lines.append(
            f"| {i} | {decision.timeline_start:.2f}s "
            f"| {clip_name} "
            f"| {decision.intensity_score:.2f} "
            f"| {section} "
            f"| {decision.duration:.2f}s "
            f"| {decision.speed:.2f}x "
            f"| {decision.reason} |"
        )

    lines.append("")
    lines.append("## Config Applied\n")
    lines.append("")
    lines.append(f"- **Min clip duration**: {config.min_clip_seconds}s")
    lines.append(
        f"- **Intensity durations**: "
        f"high={config.high_intensity_seconds}s "
        f"mid={config.medium_intensity_seconds}s "
        f"low={config.low_intensity_seconds}s"
    )
    lines.append(f"- **Max clips**: {config.max_clips}")
    lines.append(f"- **Max duration**: {config.max_duration_seconds}")
    if config.video_style and config.video_style != "none":
        lines.append(f"- **Video style**: {config.video_style}")
    if config.audio_overlay and config.audio_overlay != "none":
        lines.append(f"- **Audio overlay**: {config.audio_overlay}")
    lines.append("")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Explain log written to: %s", log_path)


def write_explain_html(
    config: PacingConfig,
    audio_data: AudioAnalysisResult,
    decisions: list[SegmentDecision],
) -> None:
    """Write collected decisions to an HTML report file."""
    if not config.explain_html or not decisions:
        return

    from src.services.explain_html import generate_explain_html  # noqa: WPS433

    generate_explain_html(
        config.explain_html,
        audio_data,
        decisions,
        config,
    )
    logger.info("HTML explain report written to: %s", config.explain_html)

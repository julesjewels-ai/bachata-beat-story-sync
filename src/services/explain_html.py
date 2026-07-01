"""
HTML Decision Report Generator — FEAT-025.

Produces a beautiful, shareable HTML report showing why the tool made each
montage decision, including timeline visualization, decision table, and stats.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import AudioAnalysisResult, PacingConfig, SegmentDecision


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _intensity_to_color(intensity_score: float) -> str:
    """Map intensity score (0.0-1.0) to a color.

    Args:
        intensity_score: Normalized intensity value.

    Returns:
        Hex color code (red for high, yellow for medium, blue for low).
    """
    if intensity_score >= 0.65:
        return "#ef4444"  # Red for high intensity
    if intensity_score >= 0.35:
        return "#eab308"  # Yellow for medium intensity
    return "#3b82f6"  # Blue for low intensity


def _fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS.f (e.g. 03:42.5)."""
    mins = int(seconds) // 60
    secs = seconds - mins * 60
    return f"{mins:02d}:{secs:04.1f}"


def _fmt_duration(seconds: float) -> str:
    """Format duration as X.XXs."""
    return f"{seconds:.2f}s"


def _fmt_speed(speed: float) -> str:
    """Format speed as X.XXx."""
    return f"{speed:.2f}x"


def _build_timeline_svg(
    decisions: list[SegmentDecision],
    audio_duration: float,
    sections: list | None = None,
) -> str:
    """Build an SVG timeline visualization.

    Args:
        decisions: List of segment decisions.
        audio_duration: Total audio duration in seconds.
        sections: Optional list of MusicalSection objects for labeling.

    Returns:
        SVG element as a string.
    """
    if not decisions:
        return "<p>No segments to visualize.</p>"

    # SVG dimensions
    width = 1000
    height = 100
    margin = 40
    bar_height = 40
    section_label_height = 30

    total_height = section_label_height + bar_height + 20

    # Build timeline bar
    lines = [
        f'<svg width="{width}" height="{total_height}" '
        'style="border: 1px solid #ccc; background: #fafafa; margin: 20px 0;">',
    ]

    # Draw section labels if available
    if sections:
        section_y = 10
        for section in sections:
            start_pct = (section.start_time / audio_duration) * (width - 2 * margin)
            end_pct = (section.end_time / audio_duration) * (width - 2 * margin)
            x1 = margin + start_pct
            x2 = margin + end_pct
            label_text = _escape_html(section.label)

            # Section label with background
            lines.append(
                f'<rect x="{x1}" y="{section_y}" width="{max(30, x2 - x1)}" '
                f'height="20" fill="rgba(100,100,100,0.1)" stroke="none"/>'
            )
            lines.append(
                f'<text x="{x1 + 5}" y="{section_y + 15}" font-size="11" '
                f'fill="#666" font-family="Arial">{label_text}</text>'
            )

    # Draw segment bars
    bar_y = section_label_height
    for decision in decisions:
        start_pct = (decision.timeline_start / audio_duration) * (width - 2 * margin)
        duration_pct = (decision.duration / audio_duration) * (width - 2 * margin)

        x = margin + start_pct
        w = max(2, duration_pct)  # Minimum width for visibility
        color = _intensity_to_color(decision.intensity_score)

        # Draw segment rectangle
        lines.append(
            f'<rect x="{x}" y="{bar_y}" width="{w}" height="{bar_height}" '
            f'fill="{color}" stroke="#333" stroke-width="1" opacity="0.8"/>'
        )

    # Draw timeline axis
    axis_y = bar_y + bar_height + 5
    lines.append(
        f'<line x1="{margin}" y1="{axis_y}" x2="{width - margin}" '
        f'y2="{axis_y}" stroke="#999" stroke-width="1"/>'
    )

    # Add time markers
    num_markers = 5
    for i in range(num_markers + 1):
        time_val = (i / num_markers) * audio_duration
        x = margin + (i / num_markers) * (width - 2 * margin)
        time_str = _fmt_time(time_val)
        lines.append(
            f'<text x="{x}" y="{axis_y + 15}" font-size="11" '
            f'text-anchor="middle" fill="#666" '
            f'font-family="Arial">{time_str}</text>'
        )

    # Add legend
    legend_y = total_height - 10
    lines.append(
        '<g font-size="11" font-family="Arial" fill="#666">'
    )
    lines.append(
        f'<rect x="{margin}" y="{legend_y}" width="12" height="12" '
        f'fill="#ef4444" stroke="#333" stroke-width="1"/>'
    )
    lines.append(
        f'<text x="{margin + 16}" y="{legend_y + 10}">High Intensity</text>'
    )
    lines.append(
        f'<rect x="{margin + 150}" y="{legend_y}" width="12" height="12" '
        f'fill="#eab308" stroke="#333" stroke-width="1"/>'
    )
    lines.append(
        f'<text x="{margin + 166}" y="{legend_y + 10}">Medium Intensity</text>'
    )
    lines.append(
        f'<rect x="{margin + 330}" y="{legend_y}" width="12" height="12" '
        f'fill="#3b82f6" stroke="#333" stroke-width="1"/>'
    )
    lines.append(
        f'<text x="{margin + 346}" y="{legend_y + 10}">Low Intensity</text>'
    )
    lines.append("</g>")

    lines.append("</svg>")
    return "\n".join(lines)


def _build_decision_table(decisions: list[SegmentDecision]) -> str:
    """Build an HTML table of segment decisions.

    Args:
        decisions: List of segment decisions.

    Returns:
        HTML table as a string.
    """
    rows = []
    rows.append(
        "<table style='width: 100%; border-collapse: collapse; "
        "margin: 20px 0; font-size: 14px;'>"
    )
    rows.append(
        "<thead style='background: #f3f4f6; border-bottom: 2px solid #9ca3af;'>"
    )
    rows.append(
        "<tr style='height: 40px;'>"
        "<th style='padding: 10px; text-align: left; font-weight: 600;'>#</th>"
        "<th style='padding: 10px; text-align: left; font-weight: 600;'>Time</th>"
        "<th style='padding: 10px; text-align: left; font-weight: 600;'>Clip</th>"
        "<th style='padding: 10px; text-align: left; font-weight: 600;'>Intensity</th>"
        "<th style='padding: 10px; text-align: left; font-weight: 600;'>Section</th>"
        "<th style='padding: 10px; text-align: left; font-weight: 600;'>Duration</th>"
        "<th style='padding: 10px; text-align: left; font-weight: 600;'>Speed</th>"
        "<th style='padding: 10px; text-align: left; font-weight: 600;'>Reason</th>"
        "</tr>"
    )
    rows.append("</thead>")
    rows.append("<tbody>")

    for i, decision in enumerate(decisions, 1):
        clip_name = os.path.basename(decision.clip_path)
        section_label = decision.section_label or "—"
        intensity_color = _intensity_to_color(decision.intensity_score)

        bg_color = "#f9fafb" if i % 2 == 0 else "#ffffff"
        rows.append(
            f"<tr style='background: {bg_color}; "
            f"border-bottom: 1px solid #e5e7eb; height: 36px;'>"
            f"<td style='padding: 10px;'>{i}</td>"
            f"<td style='padding: 10px;'>{_fmt_time(decision.timeline_start)}</td>"
            f"<td style='padding: 10px; max-width: 200px; word-break: break-word;'>"
            f"{_escape_html(clip_name)}</td>"
            f"<td style='padding: 10px;'>"
            f"<span style='display: inline-block; width: 16px; height: 16px; "
            f"background: {intensity_color}; border-radius: 3px; "
            f"margin-right: 5px;'></span>"
            f"{decision.intensity_score:.2f}</td>"
            f"<td style='padding: 10px;'>{_escape_html(section_label)}</td>"
            f"<td style='padding: 10px;'>{_fmt_duration(decision.duration)}</td>"
            f"<td style='padding: 10px;'>{_fmt_speed(decision.speed)}</td>"
            f"<td style='padding: 10px;'>{_escape_html(decision.reason)}</td>"
            f"</tr>"
        )

    rows.append("</tbody>")
    rows.append("</table>")
    return "\n".join(rows)


def _build_stats_summary(
    decisions: list[SegmentDecision],
    audio_duration: float,
) -> str:
    """Build a statistics summary card.

    Args:
        decisions: List of segment decisions.
        audio_duration: Total audio duration.

    Returns:
        HTML card with stats.
    """
    if not decisions:
        return ""

    unique_clips = len({d.clip_path for d in decisions})
    avg_duration = sum(d.duration for d in decisions) / len(decisions)
    speeds = [d.speed for d in decisions]
    min_speed = min(speeds)
    max_speed = max(speeds)
    total_montage_duration = sum(d.duration for d in decisions)
    coverage_pct = (total_montage_duration / audio_duration * 100) if audio_duration > 0 else 0

    rows = [
        "<div style='display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; "
        "gap: 20px; margin: 30px 0;'>"
    ]

    stats = [
        ("Total Segments", str(len(decisions))),
        ("Unique Clips", str(unique_clips)),
        ("Avg Duration", _fmt_duration(avg_duration)),
        ("Speed Range", f"{_fmt_speed(min_speed)} → {_fmt_speed(max_speed)}"),
        ("Montage Duration", _fmt_time(total_montage_duration)),
        ("Timeline Coverage", f"{coverage_pct:.1f}%"),
    ]

    for label, value in stats:
        rows.append(
            f"<div style='background: #f3f4f6; padding: 20px; border-radius: 8px;'>"
            f"<div style='font-size: 12px; color: #6b7280; margin-bottom: 8px;'>"
            f"{_escape_html(label)}</div>"
            f"<div style='font-size: 24px; font-weight: bold; color: #1f2937;'>"
            f"{_escape_html(value)}</div>"
            f"</div>"
        )

    rows.append("</div>")
    return "\n".join(rows)


def _build_config_summary(config: PacingConfig) -> str:
    """Build a configuration summary card.

    Args:
        config: The PacingConfig used.

    Returns:
        HTML section with config details.
    """
    rows = [
        "<div style='background: #f3f4f6; padding: 20px; border-radius: 8px; "
        "margin: 20px 0;'>"
        "<h3 style='margin-top: 0;'>Configuration Applied</h3>"
        "<ul style='margin: 10px 0; padding-left: 20px;'>"
    ]

    rows.append(
        f"<li>Min clip duration: <strong>{config.min_clip_seconds}s</strong></li>"
    )
    rows.append(
        f"<li>Intensity durations: <strong>high={config.high_intensity_seconds}s, "
        f"medium={config.medium_intensity_seconds}s, "
        f"low={config.low_intensity_seconds}s</strong></li>"
    )
    rows.append(
        f"<li>Max clips: <strong>{config.max_clips or 'unlimited'}</strong></li>"
    )
    rows.append(
        f"<li>Max duration: <strong>{config.max_duration_seconds or 'unlimited'}s"
        f"</strong></li>"
    )

    if config.video_style and config.video_style != "none":
        rows.append(f"<li>Video style: <strong>{config.video_style}</strong></li>")

    if config.audio_overlay and config.audio_overlay != "none":
        rows.append(
            f"<li>Audio overlay: <strong>{config.audio_overlay}</strong></li>"
        )

    if config.genre:
        rows.append(f"<li>Genre: <strong>{config.genre}</strong></li>")

    if config.intro_effect and config.intro_effect != "none":
        rows.append(
            f"<li>Intro effect: <strong>{config.intro_effect} "
            f"({config.intro_effect_duration}s)</strong></li>"
        )

    if config.transition_type and config.transition_type != "none":
        rows.append(
            f"<li>Transitions: <strong>{config.transition_type} "
            f"({config.transition_duration}s)</strong></li>"
        )

    rows.append("</ul></div>")
    return "\n".join(rows)


def generate_explain_html(
    output_path: str,
    audio_meta: AudioAnalysisResult,
    decisions: list[SegmentDecision],
    config: PacingConfig,
) -> None:
    """Generate a beautiful HTML decision report.

    Creates a self-contained HTML file with inline CSS, including:
    - Project metadata (filename, BPM, duration, timestamp)
    - Timeline visualization (color-coded by intensity)
    - Interactive decision table
    - Configuration summary
    - Statistics summary

    Args:
        output_path: Path where to write the HTML file.
        audio_meta: AudioAnalysisResult with audio metadata.
        decisions: List of SegmentDecision objects from montage generation.
        config: PacingConfig that was applied.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    audio_filename = _escape_html(audio_meta.filename)
    duration_str = _fmt_time(audio_meta.duration)

    # Build sections
    timeline_svg = _build_timeline_svg(decisions, audio_meta.duration, audio_meta.sections)
    decision_table = _build_decision_table(decisions)
    stats_summary = _build_stats_summary(decisions, audio_meta.duration)
    config_summary = _build_config_summary(config)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Decision Report - {audio_filename}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            color: #1f2937;
            padding: 0;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        header {{
            background: white;
            padding: 40px 30px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }}

        h1 {{
            font-size: 32px;
            color: #1f2937;
            margin-bottom: 20px;
        }}

        .header-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .meta-item {{
            display: flex;
            flex-direction: column;
        }}

        .meta-label {{
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}

        .meta-value {{
            font-size: 16px;
            font-weight: 600;
            color: #1f2937;
        }}

        main {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            padding: 40px 30px;
        }}

        section {{
            margin-bottom: 50px;
        }}

        section:last-child {{
            margin-bottom: 0;
        }}

        h2 {{
            font-size: 24px;
            color: #1f2937;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }}

        .timeline {{
            overflow-x: auto;
            margin: 20px 0;
        }}

        footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #9ca3af;
            font-size: 12px;
        }}

        @media (max-width: 768px) {{
            header {{
                padding: 30px 20px;
            }}

            main {{
                padding: 30px 20px;
            }}

            .header-meta {{
                grid-template-columns: 1fr;
            }}

            h1 {{
                font-size: 24px;
            }}

            h2 {{
                font-size: 20px;
            }}

            table {{
                font-size: 12px !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Decision Report</h1>
            <div class="header-meta">
                <div class="meta-item">
                    <div class="meta-label">Audio File</div>
                    <div class="meta-value">{audio_filename}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">BPM</div>
                    <div class="meta-value">{audio_meta.bpm:.0f}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Duration</div>
                    <div class="meta-value">{duration_str}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Generated</div>
                    <div class="meta-value">{now}</div>
                </div>
            </div>
        </header>

        <main>
            <section>
                <h2>Timeline Visualization</h2>
                <div class="timeline">
                    {timeline_svg}
                </div>
            </section>

            <section>
                <h2>Statistics</h2>
                {stats_summary}
            </section>

            <section>
                <h2>Segment Decisions</h2>
                {decision_table}
            </section>

            <section>
                {config_summary}
            </section>
        </main>

        <footer>
            <p>Generated by Bachata Beat-Story Sync</p>
        </footer>
    </div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

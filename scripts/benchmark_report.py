#!/usr/bin/env python3
"""
Generate an HTML report from benchmark JSON output.

Takes benchmark JSON results and generates a simple, marketing-ready HTML
summary with:
  - Prominent speedup ratio
  - Simple bar chart comparing manual vs. automated time
  - Pure HTML/CSS (no JS dependencies)

Usage:
  python scripts/benchmark_report.py results.json
  python scripts/benchmark_report.py results.json -o report.html
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate HTML report from benchmark JSON output",
    )
    parser.add_argument(
        "input_json",
        type=str,
        help="Path to benchmark results JSON file (from benchmark.py --output-json)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output HTML file (default: report.html or derived from input)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=800,
        help="Chart width in pixels (default: 800)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=400,
        help="Chart height in pixels (default: 400)",
    )
    return parser.parse_args()


def load_benchmark_json(path: str) -> dict:
    """Load and parse benchmark JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def generate_html_report(
    data: dict,
    output_width: int = 800,
    output_height: int = 400,
) -> str:
    """
    Generate HTML report from benchmark data.

    Args:
        data: Benchmark summary dict (from benchmark.py JSON output)
        output_width: Chart width in pixels
        output_height: Chart height in pixels

    Returns:
        HTML string
    """
    summary = data["summary"]
    runs = data.get("runs", [])

    # Extract key metrics
    num_runs = summary["num_runs"]
    speedup_avg = summary["speedup_avg"]
    speedup_min = summary["speedup_min"]
    speedup_max = summary["speedup_max"]
    total_avg_seconds = summary["total_avg"]
    total_avg_minutes = total_avg_seconds / 60.0
    manual_estimate_avg = summary["manual_estimate_avg"]
    output_duration_avg = summary["output_duration_avg"]
    clips_avg = summary["clips_avg"]
    segments_avg = summary["segments_avg"]
    successful = summary["successful_renders"]

    # Calculate bar chart dimensions
    max_time = max(manual_estimate_avg, total_avg_minutes) * 1.2  # 20% padding
    bar_width = int(output_width * 0.6)

    # Scale bars to fit chart
    manual_bar_width = int((manual_estimate_avg / max_time) * bar_width) if max_time > 0 else 0
    auto_bar_width = int((total_avg_minutes / max_time) * bar_width) if max_time > 0 else 0

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bachata Sync Benchmark Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: {output_width + 100}px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        header p {{
            font-size: 1.1em;
            opacity: 0.95;
        }}

        .speedup-hero {{
            text-align: center;
            padding: 40px 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}

        .speedup-value {{
            font-size: 4em;
            font-weight: 700;
            color: #667eea;
            margin: 20px 0;
        }}

        .speedup-label {{
            font-size: 1.2em;
            color: #495057;
            margin-bottom: 10px;
        }}

        .speedup-range {{
            font-size: 0.95em;
            color: #868e96;
            margin-top: 15px;
        }}

        .content {{
            padding: 40px 30px;
        }}

        .chart {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}

        .chart-title {{
            font-size: 1.3em;
            font-weight: 600;
            color: #212529;
            margin-bottom: 20px;
        }}

        .chart-bar {{
            margin-bottom: 25px;
        }}

        .bar-label {{
            font-size: 0.95em;
            color: #495057;
            font-weight: 500;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
        }}

        .bar-value {{
            font-weight: 600;
            color: #212529;
        }}

        .bar {{
            height: 50px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            padding: 0 15px;
            color: white;
            font-weight: 600;
            font-size: 0.95em;
        }}

        .bar-manual {{
            background: linear-gradient(90deg, #ff6b6b 0%, #ff8787 100%);
        }}

        .bar-auto {{
            background: linear-gradient(90deg, #51cf66 0%, #69db7c 100%);
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 30px 0;
        }}

        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}

        .stat-card.alt {{
            border-left-color: #764ba2;
        }}

        .stat-label {{
            font-size: 0.9em;
            color: #868e96;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .stat-value {{
            font-size: 1.8em;
            font-weight: 700;
            color: #212529;
        }}

        .stat-unit {{
            font-size: 0.8em;
            color: #868e96;
            margin-left: 5px;
        }}

        .meta {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            font-size: 0.85em;
            color: #868e96;
        }}

        footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            font-size: 0.85em;
            color: #868e96;
            border-top: 1px solid #e9ecef;
        }}

        @media (max-width: 600px) {{
            header h1 {{
                font-size: 1.8em;
            }}

            .speedup-value {{
                font-size: 2.5em;
            }}

            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Bachata Beat-Story Sync</h1>
            <p>Performance Benchmark Report</p>
        </header>

        <div class="speedup-hero">
            <div class="speedup-label">Automation Speedup</div>
            <div class="speedup-value">{speedup_avg:.0f}x</div>
            <div class="speedup-range">
                Range: {speedup_min:.0f}x to {speedup_max:.0f}x across {num_runs} run(s)
            </div>
        </div>

        <div class="content">
            <div class="chart">
                <div class="chart-title">Manual Editing vs. Automated Sync</div>

                <div class="chart-bar">
                    <div class="bar-label">
                        <span>Manual Beat-Sync Edit (est.)</span>
                        <span class="bar-value">{manual_estimate_avg:.1f} min</span>
                    </div>
                    <div class="bar bar-manual" style="width: {manual_bar_width}px;">
                        {manual_estimate_avg:.1f} min
                    </div>
                </div>

                <div class="chart-bar">
                    <div class="bar-label">
                        <span>Bachata Sync (avg across {num_runs} runs)</span>
                        <span class="bar-value">{total_avg_minutes:.1f} min</span>
                    </div>
                    <div class="bar bar-auto" style="width: {auto_bar_width}px;">
                        {total_avg_minutes:.1f} min
                    </div>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Output Duration</div>
                    <div class="stat-value">
                        {output_duration_avg:.0f}<span class="stat-unit">sec</span>
                    </div>
                </div>

                <div class="stat-card alt">
                    <div class="stat-label">Clips Used (avg)</div>
                    <div class="stat-value">
                        {clips_avg:.0f}<span class="stat-unit">clips</span>
                    </div>
                </div>

                <div class="stat-card alt">
                    <div class="stat-label">Segments Planned (avg)</div>
                    <div class="stat-value">
                        {segments_avg:.0f}<span class="stat-unit">segs</span>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-label">Successful Renders</div>
                    <div class="stat-value">
                        {successful}/{num_runs}<span class="stat-unit">✓</span>
                    </div>
                </div>
            </div>

            <div class="meta">
                <strong>Methodology:</strong><br>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li>Manual estimate: 3 minutes per beat-sync cut (industry baseline)</li>
                    <li>Automated time: Average across {num_runs} full benchmark run(s)</li>
                    <li>Speedup ratio: (Manual estimate) ÷ (Automated time)</li>
                </ul>
            </div>
        </div>

        <footer>
            Generated by Bachata Beat-Story Sync Benchmark Suite
        </footer>
    </div>
</body>
</html>
"""

    return html


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Load input JSON
    try:
        data = load_benchmark_json(args.input_json)
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_json}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 1

    # Determine output path
    output_path = args.output
    if not output_path:
        input_path = Path(args.input_json)
        output_path = input_path.with_stem(input_path.stem + "_report").with_suffix(".html")

    # Generate HTML
    html = generate_html_report(
        data,
        output_width=args.width,
        output_height=args.height,
    )

    # Write to file
    try:
        with open(output_path, "w") as f:
            f.write(html)
        print(f"Report generated: {output_path}")
        return 0
    except IOError as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

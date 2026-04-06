#!/usr/bin/env python3
"""
Benchmarking script for Bachata Beat-Story Sync.

Measures the performance of the tool vs. manual video editing estimates.
Supports multiple runs, dry-run timing, and output to JSON/CSV.

Marketing claim validation:
  "A 4-hour Final Cut Pro project takes 4 minutes here"
  The tool typically completes in 2-5 minutes for a ~60s montage with 15-20 clips.
  Manual beat-synced editing baseline: 3 minutes per cut (industry estimate).

Usage:
  python scripts/benchmark.py --audio track.wav --video-dir clips/
  python scripts/benchmark.py --audio track.wav --video-dir clips/ --runs 3 --output-json results.json
  python scripts/benchmark.py --audio track.wav --video-dir clips/ --test-mode
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkRun:
    """Single benchmark run result."""
    run_number: int
    dry_run_time: float  # Time for dry-run (planning only)
    full_render_time: float  # Time for full render (or -1 if failed)
    total_time: float  # dry_run_time + full_render_time

    # Metrics from dry-run output
    segments_planned: int = 0
    clips_used: int = 0
    output_duration_seconds: float = 0.0

    # Analysis
    estimated_manual_minutes: float = 0.0
    speedup_ratio: float = 0.0
    render_success: bool = False
    error_message: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Summary statistics across multiple runs."""
    num_runs: int

    dry_run_avg: float = 0.0
    dry_run_min: float = 0.0
    dry_run_max: float = 0.0

    render_avg: float = 0.0
    render_min: float = 0.0
    render_max: float = 0.0

    total_avg: float = 0.0
    total_min: float = 0.0
    total_max: float = 0.0

    speedup_avg: float = 0.0
    speedup_min: float = 0.0
    speedup_max: float = 0.0

    successful_renders: int = 0

    segments_avg: float = 0.0
    clips_avg: float = 0.0
    output_duration_avg: float = 0.0
    manual_estimate_avg: float = 0.0

    runs: list = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Benchmark Bachata Beat-Story Sync performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single run
  %(prog)s --audio track.wav --video-dir clips/

  # Multiple runs with JSON output
  %(prog)s --audio track.wav --video-dir clips/ --runs 3 --output-json results.json

  # Quick test mode
  %(prog)s --audio track.wav --video-dir clips/ --test-mode

  # Full output
  %(prog)s --audio track.wav --video-dir clips/ --runs 3 --output-json results.json --output-csv results.csv
        """
    )
    parser.add_argument(
        "--audio",
        type=str,
        required=True,
        help="Path to the input .wav audio file",
    )
    parser.add_argument(
        "--video-dir",
        type=str,
        required=True,
        help="Directory containing .mp4 video clips",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of benchmark runs (default: 1)",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (4 clips, 10 seconds max duration)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_output.mp4",
        help="Output video path for benchmarks (default: benchmark_output.mp4)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        help="Save detailed results to JSON file",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        help="Save summary stats to CSV file",
    )
    parser.add_argument(
        "--manual-estimate-per-cut",
        type=float,
        default=3.0,
        help=(
            "Minutes per cut for manual editing estimate "
            "(default: 3.0 minutes, industry baseline for beat-synced edits)"
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def validate_inputs(audio: str, video_dir: str) -> bool:
    """Validate that input files exist and are readable."""
    if not os.path.exists(audio):
        logger.error(f"Audio file not found: {audio}")
        return False
    if not os.path.isfile(audio):
        logger.error(f"Audio is not a file: {audio}")
        return False
    if not os.path.exists(video_dir):
        logger.error(f"Video directory not found: {video_dir}")
        return False
    if not os.path.isdir(video_dir):
        logger.error(f"Video path is not a directory: {video_dir}")
        return False

    # Check if there are any video clips
    video_files = list(Path(video_dir).glob("**/*.mp4"))
    if not video_files:
        logger.error(f"No .mp4 files found in {video_dir}")
        return False

    logger.info(f"Found {len(video_files)} video clips in {video_dir}")
    return True


def run_main_py(
    audio: str,
    video_dir: str,
    output: str,
    dry_run: bool = False,
    test_mode: bool = False,
) -> tuple[float, dict]:
    """
    Run main.py and measure execution time.

    Returns:
        (elapsed_time, metrics_dict)

    metrics_dict contains:
      - segments_planned: int (from dry-run) or 0
      - clips_used: int
      - output_duration_seconds: float
      - render_success: bool
      - error_message: Optional[str]
    """
    metrics = {
        "segments_planned": 0,
        "clips_used": 0,
        "output_duration_seconds": 0.0,
        "render_success": False,
        "error_message": None,
    }

    cmd = [
        "python",
        "main.py",
        "--audio",
        audio,
        "--video-dir",
        video_dir,
        "--output",
        output,
    ]

    if dry_run:
        cmd.append("--dry-run")

    if test_mode:
        cmd.append("--test-mode")

    logger.debug(f"Running: {' '.join(cmd)}")

    start_time = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        elapsed = time.perf_counter() - start_time

        if result.returncode != 0:
            metrics["error_message"] = result.stderr[:200] if result.stderr else "Unknown error"
            logger.warning(f"Command failed with return code {result.returncode}")
            logger.debug(f"stderr: {result.stderr[:500]}")
            return elapsed, metrics

        # Parse output to extract metrics
        output_text = result.stdout + result.stderr
        metrics.update(_parse_metrics_from_output(output_text, output))
        metrics["render_success"] = True

        return elapsed, metrics

    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start_time
        metrics["error_message"] = "Process timeout (>10 min)"
        logger.warning("Process timed out")
        return elapsed, metrics
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        metrics["error_message"] = str(e)[:100]
        logger.error(f"Exception running main.py: {e}")
        return elapsed, metrics


def _parse_metrics_from_output(output_text: str, output_file: str) -> dict:
    """
    Parse metrics from main.py output.

    This is a best-effort extraction; if it fails, defaults are returned.
    """
    metrics = {
        "segments_planned": 0,
        "clips_used": 0,
        "output_duration_seconds": 0.0,
    }

    # Try to infer clips_used and output_duration from the output file itself
    if os.path.exists(output_file):
        try:
            # Use ffprobe to get video duration (if available)
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1:noesc=1",
                    output_file,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                metrics["output_duration_seconds"] = float(result.stdout.strip())
        except Exception as e:
            logger.debug(f"Could not parse output duration: {e}")

    # Try to extract from log output
    for line in output_text.split("\n"):
        line_lower = line.lower()
        if "found" in line_lower and "clips" in line_lower:
            # e.g., "Found 15 suitable clips."
            try:
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    metrics["clips_used"] = int(parts[1])
            except Exception:
                pass

    return metrics


def calculate_manual_estimate(
    output_duration_seconds: float,
    min_per_cut: float,
) -> float:
    """
    Estimate manual editing time.

    Industry baseline: 3 minutes per cut for beat-synced video editing.
    We estimate roughly (output_duration_seconds / 3) cuts as a conservative base,
    then multiply by the per-cut estimate.

    A 60-second video with 15-20 clips = roughly 15 cuts.
    At 3 min/cut = 45 minutes.

    Args:
        output_duration_seconds: Total output video duration
        min_per_cut: Minutes per cut (default 3.0)

    Returns:
        Estimated minutes for manual editing
    """
    if output_duration_seconds <= 0:
        return 0.0

    # Rough estimate: one cut per 4 seconds of output video
    # (conservative for beat-synced work)
    estimated_cuts = max(1, output_duration_seconds / 4.0)
    return estimated_cuts * min_per_cut


def run_benchmark(
    audio: str,
    video_dir: str,
    output: str,
    num_runs: int = 1,
    test_mode: bool = False,
    manual_estimate_per_cut: float = 3.0,
) -> BenchmarkSummary:
    """
    Run the benchmark suite.

    For each run:
      1. Run main.py with --dry-run to measure planning time
      2. Run main.py with full render to measure total time
      3. Calculate speedup ratio
    """
    logger.info(f"Starting benchmark with {num_runs} run(s)...")

    runs = []

    for run_num in range(1, num_runs + 1):
        logger.info(f"\n--- Run {run_num}/{num_runs} ---")

        # Run dry-run (planning only)
        logger.info("Running dry-run (planning)...")
        dry_time, dry_metrics = run_main_py(
            audio,
            video_dir,
            output,
            dry_run=True,
            test_mode=test_mode,
        )
        logger.info(f"  Dry-run time: {dry_time:.2f}s")

        # Run full render
        logger.info("Running full render...")
        full_time, full_metrics = run_main_py(
            audio,
            video_dir,
            output,
            dry_run=False,
            test_mode=test_mode,
        )
        logger.info(f"  Full render time: {full_time:.2f}s")

        # Merge metrics
        metrics = {**dry_metrics, **full_metrics}

        # Calculate manual estimate and speedup
        manual_estimate = calculate_manual_estimate(
            metrics["output_duration_seconds"],
            manual_estimate_per_cut,
        )

        total_time = dry_time + full_time
        speedup = (
            (manual_estimate * 60) / total_time
            if total_time > 0 and manual_estimate > 0
            else 0.0
        )

        run = BenchmarkRun(
            run_number=run_num,
            dry_run_time=dry_time,
            full_render_time=full_time,
            total_time=total_time,
            segments_planned=metrics.get("segments_planned", 0),
            clips_used=metrics.get("clips_used", 0),
            output_duration_seconds=metrics.get("output_duration_seconds", 0.0),
            estimated_manual_minutes=manual_estimate,
            speedup_ratio=speedup,
            render_success=metrics.get("render_success", False),
            error_message=metrics.get("error_message"),
        )

        runs.append(run)

        logger.info(f"  Output duration: {run.output_duration_seconds:.1f}s")
        logger.info(f"  Estimated manual time: {run.estimated_manual_minutes:.1f} min")
        logger.info(f"  Speedup ratio: {run.speedup_ratio:.1f}x")

    # Compute summary
    summary = _compute_summary(runs)
    return summary


def _compute_summary(runs: list[BenchmarkRun]) -> BenchmarkSummary:
    """Compute summary statistics from runs."""
    n = len(runs)

    dry_times = [r.dry_run_time for r in runs]
    render_times = [r.full_render_time for r in runs if r.full_render_time >= 0]
    total_times = [r.total_time for r in runs]
    speedups = [r.speedup_ratio for r in runs if r.speedup_ratio > 0]

    summary = BenchmarkSummary(
        num_runs=n,
        dry_run_avg=sum(dry_times) / n if dry_times else 0.0,
        dry_run_min=min(dry_times) if dry_times else 0.0,
        dry_run_max=max(dry_times) if dry_times else 0.0,
        render_avg=sum(render_times) / len(render_times) if render_times else 0.0,
        render_min=min(render_times) if render_times else 0.0,
        render_max=max(render_times) if render_times else 0.0,
        total_avg=sum(total_times) / n if total_times else 0.0,
        total_min=min(total_times) if total_times else 0.0,
        total_max=max(total_times) if total_times else 0.0,
        speedup_avg=sum(speedups) / len(speedups) if speedups else 0.0,
        speedup_min=min(speedups) if speedups else 0.0,
        speedup_max=max(speedups) if speedups else 0.0,
        successful_renders=sum(1 for r in runs if r.render_success),
        segments_avg=sum(r.segments_planned for r in runs) / n if runs else 0.0,
        clips_avg=sum(r.clips_used for r in runs) / n if runs else 0.0,
        output_duration_avg=sum(r.output_duration_seconds for r in runs) / n if runs else 0.0,
        manual_estimate_avg=sum(r.estimated_manual_minutes for r in runs) / n if runs else 0.0,
        runs=runs,
    )

    return summary


def print_summary_table(summary: BenchmarkSummary) -> None:
    """Print summary to console using Rich or plain text."""
    if HAS_RICH:
        _print_summary_table_rich(summary)
    else:
        _print_summary_table_plain(summary)


def _print_summary_table_rich(summary: BenchmarkSummary) -> None:
    """Print using Rich tables."""
    console = Console()

    console.print("\n" + "=" * 70)
    console.print("[bold cyan]BENCHMARK SUMMARY[/bold cyan]")
    console.print("=" * 70 + "\n")

    # Timing table
    timing_table = Table(title="Execution Times (seconds)", show_header=True)
    timing_table.add_column("Metric", style="cyan")
    timing_table.add_column("Average", style="green")
    timing_table.add_column("Min", style="yellow")
    timing_table.add_column("Max", style="magenta")

    timing_table.add_row(
        "Dry-run (plan)",
        f"{summary.dry_run_avg:.2f}s",
        f"{summary.dry_run_min:.2f}s",
        f"{summary.dry_run_max:.2f}s",
    )
    timing_table.add_row(
        "Full render",
        f"{summary.render_avg:.2f}s",
        f"{summary.render_min:.2f}s",
        f"{summary.render_max:.2f}s",
    )
    timing_table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{summary.total_avg:.2f}s[/bold]",
        f"[bold]{summary.total_min:.2f}s[/bold]",
        f"[bold]{summary.total_max:.2f}s[/bold]",
    )

    console.print(timing_table)

    # Speedup table
    speedup_table = Table(title="Manual Edit Estimate vs. Automated", show_header=True)
    speedup_table.add_column("Metric", style="cyan")
    speedup_table.add_column("Average", style="green")
    speedup_table.add_column("Min", style="yellow")
    speedup_table.add_column("Max", style="magenta")

    speedup_table.add_row(
        "Est. manual time",
        f"{summary.manual_estimate_avg:.1f} min",
        f"{summary.manual_estimate_avg:.1f} min",
        f"{summary.manual_estimate_avg:.1f} min",
    )
    speedup_table.add_row(
        "Automated time",
        f"{summary.total_avg / 60:.1f} min",
        f"{summary.total_min / 60:.1f} min",
        f"{summary.total_max / 60:.1f} min",
    )
    speedup_table.add_row(
        "[bold]Speedup ratio[/bold]",
        f"[bold cyan]{summary.speedup_avg:.1f}x[/bold cyan]",
        f"[bold cyan]{summary.speedup_min:.1f}x[/bold cyan]",
        f"[bold cyan]{summary.speedup_max:.1f}x[/bold cyan]",
    )

    console.print(speedup_table)

    # Stats table
    stats_table = Table(title="Video Statistics", show_header=True)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Average", style="green")

    stats_table.add_row("Output duration", f"{summary.output_duration_avg:.1f}s")
    stats_table.add_row("Segments planned", f"{summary.segments_avg:.0f}")
    stats_table.add_row("Clips used", f"{summary.clips_avg:.0f}")
    stats_table.add_row("Successful renders", f"{summary.successful_renders}/{summary.num_runs}")

    console.print(stats_table)

    console.print("\n" + "=" * 70 + "\n")


def _print_summary_table_plain(summary: BenchmarkSummary) -> None:
    """Print using plain text (no Rich)."""
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70 + "\n")

    print("Execution Times:")
    print(f"  Dry-run (plan):   {summary.dry_run_avg:.2f}s (min: {summary.dry_run_min:.2f}s, max: {summary.dry_run_max:.2f}s)")
    print(f"  Full render:      {summary.render_avg:.2f}s (min: {summary.render_min:.2f}s, max: {summary.render_max:.2f}s)")
    print(f"  Total:            {summary.total_avg:.2f}s (min: {summary.total_min:.2f}s, max: {summary.total_max:.2f}s)")

    print("\nManual Edit Estimate vs. Automated:")
    print(f"  Est. manual time: {summary.manual_estimate_avg:.1f} minutes")
    print(f"  Automated time:   {summary.total_avg / 60:.1f} minutes")
    print(f"  Speedup ratio:    {summary.speedup_avg:.1f}x (min: {summary.speedup_min:.1f}x, max: {summary.speedup_max:.1f}x)")

    print("\nVideo Statistics:")
    print(f"  Output duration:  {summary.output_duration_avg:.1f}s")
    print(f"  Segments planned: {summary.segments_avg:.0f}")
    print(f"  Clips used:       {summary.clips_avg:.0f}")
    print(f"  Successful renders: {summary.successful_renders}/{summary.num_runs}")

    print("\n" + "=" * 70 + "\n")


def save_json_results(summary: BenchmarkSummary, output_file: str) -> None:
    """Save detailed results to JSON."""
    data = {
        "summary": asdict(summary),
        "runs": [asdict(r) for r in summary.runs],
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved JSON results to {output_file}")


def save_csv_results(summary: BenchmarkSummary, output_file: str) -> None:
    """Save summary stats to CSV."""
    import csv

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            "Metric",
            "Value",
        ])

        # Data rows
        writer.writerow(["Runs", summary.num_runs])
        writer.writerow(["Dry-run avg (s)", f"{summary.dry_run_avg:.2f}"])
        writer.writerow(["Dry-run min (s)", f"{summary.dry_run_min:.2f}"])
        writer.writerow(["Dry-run max (s)", f"{summary.dry_run_max:.2f}"])
        writer.writerow(["Render avg (s)", f"{summary.render_avg:.2f}"])
        writer.writerow(["Render min (s)", f"{summary.render_min:.2f}"])
        writer.writerow(["Render max (s)", f"{summary.render_max:.2f}"])
        writer.writerow(["Total avg (s)", f"{summary.total_avg:.2f}"])
        writer.writerow(["Total min (s)", f"{summary.total_min:.2f}"])
        writer.writerow(["Total max (s)", f"{summary.total_max:.2f}"])
        writer.writerow(["Total avg (min)", f"{summary.total_avg / 60:.1f}"])
        writer.writerow(["Est. manual (min)", f"{summary.manual_estimate_avg:.1f}"])
        writer.writerow(["Speedup avg (x)", f"{summary.speedup_avg:.1f}"])
        writer.writerow(["Speedup min (x)", f"{summary.speedup_min:.1f}"])
        writer.writerow(["Speedup max (x)", f"{summary.speedup_max:.1f}"])
        writer.writerow(["Successful renders", summary.successful_renders])
        writer.writerow(["Output duration avg (s)", f"{summary.output_duration_avg:.1f}"])
        writer.writerow(["Segments avg", f"{summary.segments_avg:.0f}"])
        writer.writerow(["Clips avg", f"{summary.clips_avg:.0f}"])

    logger.info(f"Saved CSV results to {output_file}")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Bachata Beat-Story Sync Benchmark")
    logger.info(f"Audio: {args.audio}")
    logger.info(f"Video dir: {args.video_dir}")
    logger.info(f"Runs: {args.runs}")
    logger.info(f"Manual estimate per cut: {args.manual_estimate_per_cut} min")

    # Validate inputs
    if not validate_inputs(args.audio, args.video_dir):
        logger.error("Input validation failed")
        return 1

    # Run benchmark
    try:
        summary = run_benchmark(
            audio=args.audio,
            video_dir=args.video_dir,
            output=args.output,
            num_runs=args.runs,
            test_mode=args.test_mode,
            manual_estimate_per_cut=args.manual_estimate_per_cut,
        )
    except KeyboardInterrupt:
        logger.error("Benchmark interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Benchmark failed: {e}", exc_info=args.verbose)
        return 1

    # Print results
    print_summary_table(summary)

    # Save outputs
    if args.output_json:
        save_json_results(summary, args.output_json)

    if args.output_csv:
        save_csv_results(summary, args.output_csv)

    logger.info("Benchmark complete!")

    # Return non-zero if any render failed
    return 0 if summary.successful_renders == summary.num_runs else 1


if __name__ == "__main__":
    sys.exit(main())

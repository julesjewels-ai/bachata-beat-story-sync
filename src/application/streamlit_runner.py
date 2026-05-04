"""Background execution helpers for the Streamlit UI."""

from __future__ import annotations

import json
import logging
import queue
import sys
import traceback as tb_module
from typing import Any

from src.application.story_workflow import run_story_workflow
from src.services.reporting import ExcelReportGenerator
from src.workers.progress import QueueLogHandler, QueueProgressObserver


def run_streamlit_generation(
    audio_resolved: str,
    video_dir_path: str,
    broll_path: str | None,
    output_video: str,
    pacing_kwargs: dict[str, Any],
    export_report_path: str | None,
    log_queue: queue.Queue,
) -> None:
    """Run story generation in a background thread and stream progress to a queue."""
    handler = QueueLogHandler(log_queue)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    try:
        log_queue.put("DEBUG: Background thread started")
        log_queue.put(f"DEBUG: Audio: {audio_resolved}")
        log_queue.put(f"DEBUG: Video dir: {video_dir_path}")
        log_queue.put("DEBUG: Modules imported successfully")

        result = run_story_workflow(
            audio_resolved,
            video_dir_path,
            output_video,
            broll_dir=broll_path,
            pacing_overrides=pacing_kwargs,
            scan_observer_factory=lambda: QueueProgressObserver(log_queue),
            render_observer_factory=lambda: QueueProgressObserver(log_queue),
        )

        if result.plan_report is not None:
            log_queue.put("__PLAN_REPORT__" + result.plan_report)
            log_queue.put("✓ Dry-run complete — plan ready (no video rendered)")
            log_queue.put("__DONE__")
            return

        if export_report_path and result.output_path is not None:
            log_queue.put("   → Generating Excel report…")
            ExcelReportGenerator().generate_report(
                result.audio_meta,
                result.video_clips,
                export_report_path,
            )
            log_queue.put(f"   → Report saved to: {export_report_path}")

        if result.output_path is not None:
            log_queue.put("✓ Video rendered successfully!")
            log_queue.put(f"   → Saved to: {result.output_path}")

            # Collect metadata for result metrics panel
            bpm = round(result.audio_meta.bpm, 1) if result.audio_meta else 0
            clips_total = len(result.video_clips) if result.video_clips else 0
            duration_s = (
                round(result.audio_meta.duration, 1) if result.audio_meta else 0
            )
            effects_count = sum([
                bool(pacing_kwargs.get("video_style") not in (None, "none")),
                bool(pacing_kwargs.get("intro_effect") not in (None, "none")),
                bool(pacing_kwargs.get("transition_type") not in (None, "none")),
                bool(pacing_kwargs.get("speed_ramp_organic")),
            ])
            metadata = {
                "bpm": bpm,
                "clips_total": clips_total,
                "duration_s": duration_s,
                "effects_count": effects_count,
            }
            log_queue.put("__METADATA__" + json.dumps(metadata))
            log_queue.put("__RESULT__" + result.output_path)
        log_queue.put("__DONE__")

    except Exception:  # noqa: BLE001
        error_details = tb_module.format_exc()
        log_queue.put(f"__ERROR__{error_details}")
        sys.stderr.write(f"THREAD ERROR:\n{error_details}\n")
        log_queue.put("__DONE__")
    finally:
        root_logger.removeHandler(handler)
        root_logger.removeHandler(console_handler)

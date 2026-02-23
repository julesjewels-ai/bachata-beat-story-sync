"""
EDL (Edit Decision List) Exporter for Bachata Beat-Story Sync.
Generates CMX 3600 compliant EDL files for import into professional NLEs.
"""
import math
import os
from typing import List, TextIO

from src.core.interfaces import TimelineExporter
from src.core.models import SegmentPlan
from src.services.export.exceptions import ExportError


class EdlTimelineExporter(TimelineExporter):
    """
    Exports a montage plan to a CMX 3600 EDL file.
    """

    def export(
        self,
        plans: List[SegmentPlan],
        output_path: str,
        fps: float = 30.0
    ) -> str:
        """
        Generates the EDL file.

        Args:
            plans: List of segment plans.
            output_path: Destination .edl file path.
            fps: Frame rate for timecode calculation (default 30.0).

        Returns:
            The absolute path to the generated EDL file.

        Raises:
            ExportError: If the plan list is empty or file writing fails.
        """
        if not plans:
            raise ExportError("Cannot export an empty segment plan.")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                self._write_header(f, output_path)

                for i, segment in enumerate(plans, 1):
                    self._write_event(f, i, segment, fps)

            return os.path.abspath(output_path)

        except OSError as e:
            raise ExportError(f"Failed to write EDL file: {e}") from e

    def _write_header(self, f: TextIO, output_path: str) -> None:
        """Writes standard CMX 3600 headers."""
        title = os.path.splitext(os.path.basename(output_path))[0].upper()
        f.write(f"TITLE: {title}\n")
        f.write("FCM: NON-DROP FRAME\n\n")

    def _write_event(
        self, f: TextIO, index: int, segment: SegmentPlan, fps: float
    ) -> None:
        """
        Writes a single edit event line.
        Format:
        001  AX       V     C        00:00:00:00 00:00:05:00 00:00:00:00 00:00:05:00
        * FROM CLIP NAME: clip_filename.mp4
        """
        event_num = f"{index:03d}"
        reel_name = "AX"  # "Auxiliary" is standard for file-based sources
        track = "V"       # Video only
        trans = "C"       # Cut

        # Source Timecode
        src_in = self._seconds_to_timecode(segment.start_time, fps)
        src_out = self._seconds_to_timecode(
            segment.start_time + segment.duration, fps
        )

        # Record (Timeline) Timecode
        rec_in = self._seconds_to_timecode(segment.timeline_position, fps)
        rec_out = self._seconds_to_timecode(
            segment.timeline_position + segment.duration, fps
        )

        # Standard CMX 3600 line
        line = (
            f"{event_num}  {reel_name:<8} {track:<5} {trans:<8} "
            f"{src_in} {src_out} {rec_in} {rec_out}\n"
        )
        f.write(line)

        # Comment with full source filename (essential for relinking)
        filename = os.path.basename(segment.video_path)
        f.write(f"* FROM CLIP NAME: {filename}\n")

        # Additional comment for speed change if applicable
        if segment.speed_factor != 1.0:
             f.write(f"* SPEED: {segment.speed_factor:.2f}x\n")

        # Comment for section
        if segment.section_label:
             f.write(f"* SECTION: {segment.section_label}\n")

        f.write("\n")

    def _seconds_to_timecode(self, seconds: float, fps: float) -> str:
        """
        Converts seconds to HH:MM:SS:FF timecode string.
        """
        # Calculate total frames
        total_frames = int(round(seconds * fps))

        # Calculate frame base for modulo arithmetic
        # e.g., 29.97 -> 30 frames per second (non-drop)
        frame_base = int(round(fps))

        ff = total_frames % frame_base
        total_seconds = total_frames // frame_base

        ss = total_seconds % 60
        total_minutes = total_seconds // 60

        mm = total_minutes % 60
        hh = total_minutes // 60

        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

"""
Integration tests for EDL Timeline Export.
"""
import os
import pytest
from src.core.models import SegmentPlan
from src.services.export.edl import EdlTimelineExporter
from src.services.export.exceptions import ExportError


class TestEdlExportIntegration:
    def test_export_creates_file_with_correct_content(self, tmp_path):
        """Verify that a valid plan produces a correct CMX 3600 EDL file."""
        plans = [
            SegmentPlan(
                video_path="/path/to/clip1.mp4",
                start_time=10.0,
                duration=5.0,
                timeline_position=0.0,
                intensity_level="high",
                section_label="intro"
            ),
            SegmentPlan(
                video_path="/path/to/clip2.mp4",
                start_time=0.0,
                duration=2.5,
                timeline_position=5.0,
                intensity_level="low",
                speed_factor=0.5
            )
        ]

        output_file = tmp_path / "test_project.edl"
        exporter = EdlTimelineExporter()
        result = exporter.export(plans, str(output_file), fps=30.0)

        assert os.path.exists(output_file)
        assert result == str(output_file.absolute())

        content = output_file.read_text()

        # Check Headers
        assert "TITLE: TEST_PROJECT" in content
        assert "FCM: NON-DROP FRAME" in content

        # Check Event 1
        # Src In: 10s -> 00:00:10:00
        # Src Out: 15s -> 00:00:15:00
        # Rec In: 0s -> 00:00:00:00
        # Rec Out: 5s -> 00:00:05:00
        expected_line_1 = "001  AX       V     C        00:00:10:00 00:00:15:00 00:00:00:00 00:00:05:00"
        assert expected_line_1 in content
        assert "* FROM CLIP NAME: clip1.mp4" in content
        assert "* SECTION: intro" in content

        # Check Event 2
        # Src In: 0s -> 00:00:00:00
        # Src Out: 2.5s -> 00:00:02:15 (2s + 15 frames)
        # Rec In: 5s -> 00:00:05:00
        # Rec Out: 7.5s -> 00:00:07:15
        expected_line_2 = "002  AX       V     C        00:00:00:00 00:00:02:15 00:00:05:00 00:00:07:15"
        assert expected_line_2 in content
        assert "* FROM CLIP NAME: clip2.mp4" in content
        assert "* SPEED: 0.50x" in content

    def test_export_raises_on_empty_plan(self, tmp_path):
        """Verify that exporting an empty plan raises ExportError."""
        exporter = EdlTimelineExporter()
        with pytest.raises(ExportError, match="empty segment plan"):
            exporter.export([], str(tmp_path / "empty.edl"))

"""
Unit tests for HTML decision report generation (FEAT-025).

Tests cover:
    - HTML file generation with valid path
    - HTML content includes key decision data
    - HTML file contains segment information
    - Proper escaping of special characters
    - Timeline visualization rendering
    - Statistics summary generation
"""

import os
import tempfile

import pytest

from src.core.models import (
    AudioAnalysisResult,
    MusicalSection,
    PacingConfig,
    SegmentDecision,
)
from src.services.explain_html import generate_explain_html


@pytest.fixture
def temp_output_path():
    """Create a temporary file path for HTML output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "report.html")
        yield output_path


@pytest.fixture
def audio_data():
    """Audio data with sections and metadata."""
    return AudioAnalysisResult(
        filename="test_track.wav",
        bpm=120.0,
        duration=60.0,
        peaks=[10.0, 25.0, 40.0],
        sections=[
            MusicalSection(
                label="intro",
                start_time=0.0,
                end_time=10.0,
                avg_intensity=0.3,
            ),
            MusicalSection(
                label="high_energy",
                start_time=10.0,
                end_time=35.0,
                avg_intensity=0.8,
            ),
            MusicalSection(
                label="breakdown",
                start_time=35.0,
                end_time=60.0,
                avg_intensity=0.4,
            ),
        ],
        beat_times=[float(i) * 0.5 for i in range(120)],
        intensity_curve=[0.5] * 120,
    )


@pytest.fixture
def decisions():
    """Sample segment decisions for testing."""
    return [
        SegmentDecision(
            timeline_start=0.0,
            clip_path="/videos/clip1.mp4",
            intensity_score=0.8,
            section_label="intro",
            duration=2.5,
            speed=1.2,
            reason="Intensity matched: high pool (score=0.80)",
        ),
        SegmentDecision(
            timeline_start=2.5,
            clip_path="/videos/clip2.mp4",
            intensity_score=0.5,
            section_label="high_energy",
            duration=4.0,
            speed=1.0,
            reason="Intensity matched: medium pool (score=0.50)",
        ),
        SegmentDecision(
            timeline_start=6.5,
            clip_path="/videos/clip3.mp4",
            intensity_score=0.2,
            section_label="breakdown",
            duration=6.0,
            speed=0.9,
            reason="Intensity matched: low pool (score=0.20)",
        ),
    ]


@pytest.fixture
def config():
    """Default pacing configuration."""
    return PacingConfig(
        min_clip_seconds=1.5,
        high_intensity_seconds=2.5,
        medium_intensity_seconds=4.0,
        low_intensity_seconds=6.0,
        video_style="warm",
        intro_effect="bloom",
        genre="bachata",
    )


def test_generate_explain_html_creates_file(
    temp_output_path, audio_data, decisions, config
):
    """Test that generate_explain_html creates a file at the specified path."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)
    assert os.path.exists(temp_output_path)


def test_generate_explain_html_contains_valid_html(
    temp_output_path, audio_data, decisions, config
):
    """Test that the generated file contains valid HTML structure."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "<!DOCTYPE html>" in content
    assert "<html" in content
    assert "</html>" in content
    assert "<head>" in content
    assert "<body>" in content


def test_generate_explain_html_contains_audio_metadata(
    temp_output_path, audio_data, decisions, config
):
    """Test that HTML includes audio metadata."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert audio_data.filename in content
    assert "120" in content  # BPM
    assert "Decision Report" in content


def test_generate_explain_html_contains_decision_table(
    temp_output_path, audio_data, decisions, config
):
    """Test that HTML includes the decision table with segment data."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "<table" in content
    assert "Segment Decisions" in content
    # Check for decision data
    assert "clip1.mp4" in content
    assert "clip2.mp4" in content
    assert "clip3.mp4" in content


def test_generate_explain_html_contains_timeline_visualization(
    temp_output_path, audio_data, decisions, config
):
    """Test that HTML includes SVG timeline visualization."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "<svg" in content
    assert "Timeline" in content
    assert "<rect" in content  # SVG rectangles for segments


def test_generate_explain_html_contains_statistics(
    temp_output_path, audio_data, decisions, config
):
    """Test that HTML includes statistics summary."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Statistics" in content
    assert "Total Segments" in content
    assert "Unique Clips" in content


def test_generate_explain_html_contains_config_summary(
    temp_output_path, audio_data, decisions, config
):
    """Test that HTML includes configuration summary."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Configuration Applied" in content
    assert "Min clip duration" in content


def test_generate_explain_html_escapes_special_characters(
    temp_output_path, audio_data, config
):
    """Test that special HTML characters in paths/names are properly escaped."""
    # Create decisions with special characters
    decisions_with_special_chars = [
        SegmentDecision(
            timeline_start=0.0,
            clip_path='/videos/clip_"special".mp4',
            intensity_score=0.8,
            section_label="<script>alert('xss')</script>",
            duration=2.5,
            speed=1.2,
            reason="Test & reason with <quotes>",
        ),
    ]

    generate_explain_html(temp_output_path, audio_data, decisions_with_special_chars, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check that dangerous characters are escaped
    assert "&lt;script&gt;" in content
    assert "&quot;" in content
    assert "&amp;" in content
    # Ensure script tag is not directly present
    assert "<script>" not in content


def test_generate_explain_html_handles_empty_decisions(
    temp_output_path, audio_data, config
):
    """Test that HTML generation handles empty decision list gracefully."""
    decisions = []
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert os.path.exists(temp_output_path)
    assert "<!DOCTYPE html>" in content


def test_generate_explain_html_intensity_colors(
    temp_output_path, audio_data, config
):
    """Test that intensity scores are color-coded correctly."""
    decisions_varied = [
        SegmentDecision(
            timeline_start=0.0,
            clip_path="/videos/high.mp4",
            intensity_score=0.75,  # Should be red (#ef4444)
            section_label="high",
            duration=2.5,
            speed=1.2,
            reason="High intensity",
        ),
        SegmentDecision(
            timeline_start=2.5,
            clip_path="/videos/medium.mp4",
            intensity_score=0.5,  # Should be yellow (#eab308)
            section_label="medium",
            duration=4.0,
            speed=1.0,
            reason="Medium intensity",
        ),
        SegmentDecision(
            timeline_start=6.5,
            clip_path="/videos/low.mp4",
            intensity_score=0.2,  # Should be blue (#3b82f6)
            section_label="low",
            duration=6.0,
            speed=0.9,
            reason="Low intensity",
        ),
    ]

    generate_explain_html(temp_output_path, audio_data, decisions_varied, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check that color codes are present
    assert "#ef4444" in content  # Red for high
    assert "#eab308" in content  # Yellow for medium
    assert "#3b82f6" in content  # Blue for low


def test_generate_explain_html_file_is_readable_utf8(
    temp_output_path, audio_data, decisions, config
):
    """Test that the generated HTML file is valid UTF-8."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    # Should be able to read as UTF-8 without errors
    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 0


def test_generate_explain_html_with_sections(
    temp_output_path, audio_data, decisions, config
):
    """Test that musical sections are included in the timeline."""
    generate_explain_html(temp_output_path, audio_data, decisions, config)

    with open(temp_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Section labels from audio_data should be present
    assert "intro" in content
    assert "high_energy" in content
    assert "breakdown" in content

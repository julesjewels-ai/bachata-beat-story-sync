"""
Unit tests for the `detect_sections` function in `src.core.audio_analyzer`.

Target: src.core.audio_analyzer.detect_sections
Focus: Behavior, Edge Cases, Boundary Conditions, Parametrization
"""
import pytest
import numpy as np
from src.core.audio_analyzer import detect_sections
from src.core.models import MusicalSection

@pytest.mark.parametrize("beat_times, intensity_curve, duration, smoothing_window, expected_labels", [
    # Case 1: Insufficient data (Empty)
    ([], [], 10.0, 8, ["full_track"]),

    # Case 2: Insufficient data (Single beat)
    ([0.0], [0.5], 10.0, 8, ["full_track"]),

    # Case 3: Flat Low Intensity -> "intro" because it's the first section and avg < 0.5
    ([0.0, 1.0, 2.0, 3.0], [0.2, 0.2, 0.2, 0.2], 4.0, 1, ["intro"]),

    # Case 4: Flat High Intensity -> "high_energy"
    ([0.0, 1.0, 2.0, 3.0], [0.8, 0.8, 0.8, 0.8], 4.0, 1, ["high_energy"]),

    # Case 5: Two Sections (Low -> High)
    ([float(i) for i in range(8)], [0.2]*4 + [0.8]*4, 8.0, 1, ["intro", "high_energy"]),

    # Case 6: Three Sections (Low -> High -> Low)
    ([float(i) for i in range(12)], [0.2]*4 + [0.8]*4 + [0.2]*4, 12.0, 1, ["intro", "high_energy", "outro"]),

    # Case 7: Short Section Merging
    ([float(i) for i in range(12)], [0.2]*5 + [0.8]*2 + [0.2]*5, 12.0, 1, ["intro", "outro"]),

    # Case 8: Mid Energy (0.5)
    ([0.0, 1.0, 2.0, 3.0], [0.5, 0.5, 0.5, 0.5], 4.0, 1, ["mid_energy"]),

    # Case 9: High -> Low -> High (Tests "low_energy" branch)
    # 0-4: 0.8 (High), 4-8: 0.2 (Low), 8-12: 0.8 (High)
    ([float(i) for i in range(12)], [0.8]*4 + [0.2]*4 + [0.8]*4, 12.0, 1, ["high_energy", "low_energy", "high_energy"]),
])
def test_detect_sections_scenarios(beat_times, intensity_curve, duration, smoothing_window, expected_labels):
    sections = detect_sections(
        beat_times,
        intensity_curve,
        duration,
        smoothing_window=smoothing_window
    )

    actual_labels = [s.label for s in sections]
    assert len(sections) == len(expected_labels), \
        f"Count mismatch. Expected {expected_labels}, got {actual_labels}. Sections: {sections}"

    assert actual_labels == expected_labels

    for s in sections:
        assert isinstance(s, MusicalSection)

def test_detect_sections_buildup():
    """
    Test buildup detection.
    Use a range that avoids 'intro' (<0.5) and 'high_energy' (>=0.65) defaults.
    Range 0.4 to 0.6. Avg 0.5.
    """
    count = 20
    beat_times = [float(i) for i in range(count)]
    # Linear ramp from 0.4 to 0.6
    intensity_curve = list(np.linspace(0.4, 0.6, count))
    duration = 20.0

    # smoothing_window=4.
    # The gradient is small (0.2 / 20 = 0.01 per step).
    # change_threshold default 0.15.
    # So no boundaries should be detected (except maybe artifacts at ends).

    sections = detect_sections(beat_times, intensity_curve, duration, smoothing_window=4)

    # Should have at least one section.
    assert len(sections) >= 1

    # The main section (or the first one if artifact exists) should be buildup.
    # Delta: 0.6 - 0.4 = 0.2. > 0.1. -> Buildup.
    assert sections[0].label == "buildup", f"Got {sections[0].label}. Avg: {sections[0].avg_intensity}"

def test_detect_sections_breakdown():
    """
    Test breakdown detection.
    Range 0.7 to 0.4. Avg 0.55.
    Use smoothing_window=1 to avoid edge artifacts and test pure logic.
    """
    count = 20
    beat_times = [float(i) for i in range(count)]
    intensity_curve = list(np.linspace(0.7, 0.4, count))
    duration = 20.0

    # Use smoothing_window=1 so smoothed == curve.
    # Delta = 0.4 - 0.7 = -0.3.
    sections = detect_sections(beat_times, intensity_curve, duration, smoothing_window=1)

    assert len(sections) >= 1
    assert sections[0].label == "breakdown", f"Got {sections[0].label}. Avg: {sections[0].avg_intensity}"

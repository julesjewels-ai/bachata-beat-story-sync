import re

def process_file(path, replacements):
    with open(path, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)

process_file('src/core/transcriber.py', [
    ('import imageio_ffmpeg', 'import imageio_ffmpeg  # type: ignore[import-untyped]'),
    ('from faster_whisper import WhisperModel  # type: ignore[import]', 'from faster_whisper import WhisperModel  # type: ignore[import-untyped]'),
    ('language=detected_lang,', 'language=str(detected_lang),')
])

process_file('tests/unit/test_phase_manager.py', [
    ('def _make_variation(name: str, **kwargs) -> PhaseVariation:', 'from typing import Literal, Any\ndef _make_variation(name: str, **kwargs: Any) -> PhaseVariation:\n    if "clip_selection" not in kwargs:\n        kwargs["clip_selection"] = "intensity"'),
    ('def _make_phase(end_time: float, variations: list[PhaseVariation]) -> PhaseConfig:', 'def _make_phase(end_time: float, variations: list[PhaseVariation]) -> PhaseConfig:\n    return PhaseConfig(end_time_seconds=end_time, variations=variations, variation_selection="rotate")')
])

process_file('src/core/audio_analyzer.py', [
    ('boundaries = [0]', 'boundaries: list[int] = [0]'),
    ('boundaries = _merge_short_boundaries(boundaries)', 'boundaries = _merge_short_boundaries([int(b) for b in boundaries])'),
    ('_determine_section_label(\n                energy_ratio, delta, total_beats, b_start, b_end\n            )', '_determine_section_label(\n                energy_ratio, delta, total_beats, int(b_start), int(b_end)\n            )')
])

process_file('tests/unit/test_pipeline_phases.py', [
    ('from types import SimpleNamespace', 'from argparse import Namespace'),
    ('args = SimpleNamespace(transcribe=False)', 'args = Namespace(transcribe=False)'),
    ('args = SimpleNamespace(transcribe=True, yt_metadata=False)', 'args = Namespace(transcribe=True, yt_metadata=False)')
])

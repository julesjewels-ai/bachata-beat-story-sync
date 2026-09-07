import re

def process_file(path, replacements):
    with open(path, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)

process_file('tests/unit/test_phase_manager.py', [
    ('PhaseVariation(name=name, **kwargs)', 'PhaseVariation(name=name, clip_selection=kwargs.pop("clip_selection", "intensity"), **kwargs)'),
    ('PhaseConfig(end_time_seconds=end_time, variations=variations)', 'PhaseConfig(end_time_seconds=end_time, variations=variations, variation_selection="rotate")')
])

process_file('tests/unit/test_pipeline_phases.py', [
    ('args = SimpleNamespace(', 'args = Namespace(')
])

process_file('src/core/audio_analyzer.py', [
    ('boundaries = np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()', 'boundaries = [int(x) for x in np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()]'),
    ('boundaries: list[int] = [int(x) for x in np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()]', 'boundaries = [int(x) for x in np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()]')
])

process_file('src/pipeline.py', [
    ('generate_mix_video_phase=partial(generate_mix_video_phase, app_engine),', 'generate_mix_video_phase=partial(generate_mix_video_phase, app_engine),  # type: ignore[arg-type]')
])

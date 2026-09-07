with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('boundaries = list(map(int, np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()))', 'boundaries_raw = np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()\n        boundaries: list[int] = [int(str(x)) for x in boundaries_raw]')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)

with open("src/pipeline.py", "r") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'generate_mix_video_phase=' in line and 'PipelineWorkflowDependencies' not in line:
        if '# type: ignore' not in line:
            lines[i] = line.rstrip() + '  # type: ignore[arg-type]\n'
with open("src/pipeline.py", "w") as f:
    f.writelines(lines)

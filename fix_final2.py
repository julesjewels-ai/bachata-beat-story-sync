with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('b_arr = np.where(beats_df["energy_ratio"] > 1.8)[0]\n        boundaries = [int(x) for x in b_arr.tolist()]', 'boundaries = list(map(int, np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()))')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)

with open("src/pipeline.py", "r") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'generate_mix_video_phase=partial(generate_mix_video_phase, app_engine)' in line:
        if 'type: ignore' not in line:
            lines[i] = line.rstrip() + '  # type: ignore[arg-type]\n'
with open("src/pipeline.py", "w") as f:
    f.writelines(lines)

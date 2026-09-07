with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('boundaries = np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()', 'boundaries: list[int] = [int(x) for x in np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()]')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)

with open("src/pipeline.py", "r") as f:
    c = f.read()
c = c.replace('generate_mix_video_phase=partial(generate_mix_video_phase, app_engine),', 'generate_mix_video_phase=partial(generate_mix_video_phase, app_engine),  # type: ignore[arg-type]')
with open("src/pipeline.py", "w") as f:
    f.write(c)

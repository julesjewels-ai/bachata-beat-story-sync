with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('boundaries = [int(x) for x in np.where(beats_df["energy_ratio"] > 1.8)[0]]', 'b_arr = np.where(beats_df["energy_ratio"] > 1.8)[0]\n        boundaries = [int(x) for x in b_arr.tolist()]')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)

with open("src/pipeline.py", "r") as f:
    c = f.read()
c = c.replace('generate_mix_video_phase=partial(generate_mix_video_phase, app_engine)', 'generate_mix_video_phase=partial(generate_mix_video_phase, app_engine)  # type: ignore[arg-type]')
import re
c = re.sub(r'generate_mix_video_phase=partial\(generate_mix_video_phase, app_engine\)(?!\s*#)', 'generate_mix_video_phase=partial(generate_mix_video_phase, app_engine),  # type: ignore[arg-type]', c)
with open("src/pipeline.py", "w") as f:
    f.write(c)

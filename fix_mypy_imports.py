with open("tests/unit/test_phase_manager.py", "r") as f:
    c = f.read()
c = c.replace('import pytest\nfrom typing import Literal', 'import pytest\nfrom typing import Literal')
if 'from typing import Literal' not in c:
    c = 'from typing import Literal\n' + c
with open("tests/unit/test_phase_manager.py", "w") as f:
    f.write(c)

with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('boundaries: list[int] = [int(x) for x in np.where(beats_df["energy_ratio"] > 1.8)[0].tolist()]', 'boundaries = [int(x) for x in np.where(beats_df["energy_ratio"] > 1.8)[0]]')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)

with open("src/pipeline.py", "r") as f:
    c = f.read()
c = c.replace('generate_mix_video_phase=partial(generate_mix_video_phase, app_engine),  # type: ignore[arg-type]', 'generate_mix_video_phase=partial(generate_mix_video_phase, app_engine), # type: ignore[arg-type]')
if '# type: ignore[arg-type]' not in c:
    import re
    c = re.sub(r'generate_mix_video_phase=partial\(generate_mix_video_phase, app_engine\),', 'generate_mix_video_phase=partial(generate_mix_video_phase, app_engine),  # type: ignore[arg-type]', c)
with open("src/pipeline.py", "w") as f:
    f.write(c)

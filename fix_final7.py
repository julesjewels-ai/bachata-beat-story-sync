with open("src/core/audio_analyzer.py", "r") as f:
    c = f.read()
c = c.replace('change_points = [int(x) for x in (np.where(gradient >= change_threshold)[0] + 1).tolist()]', 'cp_arr = np.where(gradient >= change_threshold)[0] + 1\n    change_points = [int(x) for x in cp_arr.tolist()]')
c = c.replace('boundaries = sorted(list(set(boundaries)))', 'boundaries = sorted(set(boundaries))')
with open("src/core/audio_analyzer.py", "w") as f:
    f.write(c)

with open("tests/unit/test_phase_manager.py", "r") as f:
    c = f.read()
c = c.replace('from typing import Literal\n"""Unit tests for the video phase system (PhaseManager)."""', '"""Unit tests for the video phase system (PhaseManager)."""\n\nfrom typing import Literal')
with open("tests/unit/test_phase_manager.py", "w") as f:
    f.write(c)

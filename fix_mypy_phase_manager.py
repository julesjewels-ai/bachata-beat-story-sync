with open("tests/unit/test_phase_manager.py", "r") as f:
    c = f.read()
c = c.replace('clip_selection: str = "intensity"', 'clip_selection: Literal["intensity", "highest_intensity"] = "intensity"')
c = c.replace('import pytest', 'import pytest\nfrom typing import Literal')
c = c.replace('def _make_phase(end_time: float, variations: list[PhaseVariation]) -> PhaseConfig:', 'def _make_phase(end_time: float, variations: list[PhaseVariation]) -> PhaseConfig:\n    # type: ignore')
c = c.replace('variation_selection="rotate"', 'variation_selection="rotate" # type: ignore')
with open("tests/unit/test_phase_manager.py", "w") as f:
    f.write(c)

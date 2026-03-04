# Implementation Plan

## Gap Analysis
- `features.md` lists several features as `IMPLEMENTED` but not `VERIFIED` or `Done`.
- Project validation gates (`mypy` and `ruff`) are currently failing on the main branch.
- No `progress.txt` exists to track the current state.

## Tasks
1. **Fix Validation Gates**
   - Fix `mypy` issues in `src/core/montage.py` and `tests/unit/test_audio_mixer.py`.
   - Fix `ruff` issue in `tests/unit/test_montage.py`.
   - Ensure `pydeps .` passes.
   - Run `pytest` to confirm all tests pass.
2. **Verify FEAT-001: Variable Clip Duration Based on Intensity**
   - Ensure tests cover FEAT-001.
   - Mark as `VERIFIED`.
3. **Verify FEAT-002: Speed Ramping (Slow-Mo / Fast-Forward)**
   - Ensure tests cover FEAT-002.
   - Mark as `VERIFIED`.

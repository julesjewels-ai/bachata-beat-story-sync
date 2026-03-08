# Implementation Plan - Bachata Beat-Story Sync

## 1. Goal
Implement FEAT-013: Music-Synced Waveform Overlay.

## 2. Approach
*   **Domain Models:** Add `audio_overlay` (`Literal["none", "waveform", "bars"]`) and `audio_overlay_opacity` (`float`) to `PacingConfig` in `src/core/models.py`.
*   **Montage Generator:** Modify `_overlay_audio` in `src/core/montage.py` to accept `config` and apply `-filter_complex` (`showwaves` or `showcqt`) if an overlay is requested. Re-encode video instead of stream copy when using `filter_complex`.
*   **CLI Integration:** Add `--audio-overlay` and `--audio-overlay-opacity` arguments to `main.py` and `src/shorts_maker.py`.
*   **Security:** Enforce strict `Literal` types to prevent command injection into the FFmpeg filter string. Ensure `shell=False` on `subprocess.run` calls.

## 3. Tasks
1.  [ ] Update `PacingConfig` with new attributes and strict `Literal` validation.
2.  [ ] Update `MontageGenerator._overlay_audio` to construct the appropriate FFmpeg command with the correct filter chain and encoding parameters.
3.  [ ] Update `MontageGenerator.generate` to pass `config` to `_overlay_audio`.
4.  [ ] Add `--audio-overlay` and `--audio-overlay-opacity` arguments to `main.py` and `src/shorts_maker.py`.
5.  [ ] Update or add tests in `tests/unit/test_montage.py` to verify the correct FFmpeg arguments are built for each overlay type.
6.  [ ] Run validation gates (pytest, mypy, ruff).

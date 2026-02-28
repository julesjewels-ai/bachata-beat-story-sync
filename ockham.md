# Ockham's Razor Log

## 2024-05-21
**Target:** `MontageGenerator.build_segment_plan` in `src/core/montage.py`
**Delta:** Complexity reduced by extracting logic into `_prepare_clips` and `_calculate_segment_params`.
**Summary:** Refactored the monolithic `build_segment_plan` method by moving clip preparation (deduplication, sorting) and segment parameter calculation (duration, intensity, speed) into static helper methods. This adheres to the Single Responsibility Principle and makes the main orchestration logic cleaner and more readable.

## 2024-05-22
**Target:** `detect_sections` in `src/core/audio_analyzer.py`
**Delta:** Complexity reduced by extracting logical components into helper functions `_compute_smoothed_curve`, `_find_section_boundaries`, `_merge_short_sections`, `_check_energy_label`, and `_check_transition_label`.
**Summary:** Refactored the monolithic `detect_sections` to adhere to the Single Responsibility Principle. This isolated the computation of the intensity curve, calculating boundaries, and segment labeling.

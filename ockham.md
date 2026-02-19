# Ockham Refactor Log

## 2026-02-19
- **Target:** `detect_sections` in `src/core/audio_analyzer.py`
- **Delta:** Complexity Score 21 -> 11
- **Summary:** Extracted complex label determination logic into a pure helper function `_determine_section_label`, reducing the main function's cyclomatic complexity and improving readability.

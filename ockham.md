# Ockham's Razor - Technical Debt Log

## 2024-05-22
* **Target:** `MontageGenerator.generate` in `src/core/montage.py`
* **Delta:** Complexity Score 11 -> 7
* **Summary:** Extracted the video clip sequence generation loop into a private helper method `_create_clip_sequence` to separate clip selection logic from the main generation flow.

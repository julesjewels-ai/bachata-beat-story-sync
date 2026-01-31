# Implementation Plan - Refactor Audio Analysis Architecture

## Goal
Refactor the audio analysis logic out of `BachataSyncEngine` (in `src/core/app.py`) into a dedicated `AudioAnalyzer` class (in `src/core/audio_analyzer.py`) to improve separation of concerns and maintainability.

## Tasks
- [ ] Refactor Audio Analysis Architecture
    - [ ] Create `src/core/audio_analyzer.py`
    - [ ] Implement `AudioAnalyzer` logic
    - [ ] Update `src/core/app.py` to remove legacy audio logic
    - [ ] Update `main.py` to use `AudioAnalyzer`
    - [ ] Add unit tests
    - [ ] Verify with validation gates

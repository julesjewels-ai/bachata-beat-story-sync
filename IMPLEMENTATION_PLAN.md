# Implementation Plan - Refactor Audio Analysis Logic

The goal is to extract audio analysis logic from `BachataSyncEngine` into a dedicated `AudioAnalyzer` class to improve separation of concerns and maintainability.

## Proposed Changes

### 1. Create `src/core/audio_analyzer.py`
- Define `AudioAnalyzer` class.
- Move `AudioAnalysisInput` model here (or keep in `models.py` if shared). `AudioAnalysisInput` is currently in `app.py`. It makes sense to move it to `audio_analyzer.py` as it's specific to that analyzer, or `models.py` if it's a DTO. The memory says "The `AudioAnalysisInput` model is defined in `src/core/audio_analyzer.py` to decouple it from the core engine." So I'll move it there.
- Implement `analyze` method in `AudioAnalyzer` that returns `AudioAnalysisResult`.
- Use `SUPPORTED_AUDIO_EXTENSIONS` constant.

### 2. Refactor `src/core/app.py`
- Remove `AudioAnalysisInput` class.
- Remove `analyze_audio` method from `BachataSyncEngine`.
- Update imports.

### 3. Update `main.py`
- Import `AudioAnalyzer` and `AudioAnalysisInput` from `src/core/audio_analyzer.py`.
- Instantiate `AudioAnalyzer` and use it to analyze audio.

### 4. Update Tests
- Add unit tests for `AudioAnalyzer` in `tests/test_core.py`.
- Update existing tests that rely on `BachataSyncEngine.analyze_audio`.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_core.py` to verify audio analysis logic.
- Run `mypy .` to check type safety.
- Run `flake8 .` for linting.

### Manual Verification
- Run `main.py` with a dummy audio file to ensure the flow works.

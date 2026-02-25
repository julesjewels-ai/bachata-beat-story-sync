# Implementation Plan - Bachata Beat-Story Sync

## Gap Analysis

### Architecture
- **Complexity:**
    - `src/core/montage.py`: `MontageGenerator.build_segment_plan` has a Cyclomatic Complexity of 33 (Rank E).
    - `src/core/audio_analyzer.py`: `detect_sections` has a Cyclomatic Complexity of 21 (Rank D).
    - `src/shorts_maker.py`: `main` function is monolithic and handles too many responsibilities (Complexity 14).
- **Coupling:**
    - `MontageGenerator` is tightly coupled with `AudioAnalysisResult` and `VideoAnalysisResult`.
    - `shorts_maker.py` directly orchestrates core services.

### Security (GRASP/SCP)
- **Input Validation:**
    - File paths in `shorts_maker.py` and `src/core/models.py` need rigorous validation (directory traversal, file extensions).
- **Dependency Management:**
    - `requirements.txt` versions should be pinned to prevent supply chain attacks.
    - `subprocess` calls in `AudioMixer` and `MontageGenerator` need to be checked for shell injection vulnerabilities.

### Quality Assurance
- **Type Safety:**
    - `mypy` reports 1 error in `tests/unit/test_audio_mixer.py`.
- **Linting:**
    - `flake8` and `ruff` report multiple unused imports and line length violations.
- **Testing:**
    - Unit tests pass (78/78), but coverage for edge cases in complex functions might be low.

## Execution Plan

1.  **[High Priority] Fix Type Safety Issues**
    - [ ] Fix `mypy` error in `tests/unit/test_audio_mixer.py`.
    - [ ] Run `mypy` again to ensure zero errors.

2.  **[High Priority] Refactor `MontageGenerator`**
    - [ ] Decompose `build_segment_plan` into smaller, testable helper methods.
    - [ ] Goal: Reduce Cyclomatic Complexity to < 10.
    - [ ] Verify with `radon` and existing unit tests.

3.  **[Medium Priority] Refactor `AudioAnalyzer`**
    - [ ] Decompose `detect_sections` into smaller functions.
    - [ ] Goal: Reduce Cyclomatic Complexity to < 10.
    - [ ] Verify with `radon` and existing unit tests.

4.  **[Medium Priority] Refactor Entry Point (`shorts_maker.py`)**
    - [ ] Implement a `BatchController` or `Application` class to encapsulate the orchestration logic.
    - [ ] Use Dependency Injection for `BachataSyncEngine` and `AudioAnalyzer`.
    - [ ] Validate inputs using Pydantic models where possible.

5.  **[Low Priority] Security Hardening**
    - [ ] Audit `subprocess` calls.
    - [ ] Implement strict file path validation.
    - [ ] Pin dependencies.

## Validation Gates
- **Unit Tests:** `pytest` (Must Pass)
- **Type Check:** `mypy .` (Must Pass - Zero Errors)
- **Linting:** `flake8 .` (Must Pass)
- **Complexity:** `radon cc src -s -a` (Target: Average < B)

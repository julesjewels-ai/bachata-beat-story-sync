# Implementation Plan - Bachata Beat-Story Sync

## Gap Analysis

### Current State
- The `AudioAnalyzer` currently returns a placeholder section `["full_track"]`.
- `AudioAnalysisResult` uses `List[str]` for sections, which lacks timing information.
- No actual musical segmentation is performed.

### Desired State
- `AudioAnalyzer` should detect musical sections (e.g., Intro, Verse, Chorus) using structural analysis.
- `AudioAnalysisResult` should return `List[AudioSection]` where `AudioSection` contains `start_time`, `end_time`, `duration`, and `label`.
- The application should be able to use these sections for better video syncing (though the syncing logic update might be a separate task, the data structure must support it).

## Proposed Changes

### 1. Update Data Models (`src/core/models.py`)
- Create `AudioSection` Pydantic model.
- Update `AudioAnalysisResult.sections` type to `List[AudioSection]`.

### 2. Implement Segmentation Logic (`src/core/audio_analyzer.py`)
- Extract Chroma and MFCC features.
- Use `librosa.segment.agglomerative` to cluster frames into sections.
- Convert frame indices to time boundaries.
- Label sections (initially generic labels like "Section A", "Section B").

### 3. Update Consumers
- Verify if any other part of the code consumes `sections`. Based on current exploration, it seems mostly unused or used for reporting.
- Update `ExcelReportGenerator` if it uses sections.

### 4. Testing
- Update `tests/unit/test_audio_analyzer.py` to verify segmentation.
- Ensure `AudioAnalysisResult` validation passes.

## Execution Plan

1.  **Define `AudioSection` Model**: Add the new model to `src/core/models.py` and update `AudioAnalysisResult`.
2.  **Implement Segmentation**: Modify `AudioAnalyzer.analyze` in `src/core/audio_analyzer.py` to perform structural segmentation.
3.  **Update Tests**: Fix and extend unit tests to cover the new functionality.
4.  **Verify**: Run all validation gates.

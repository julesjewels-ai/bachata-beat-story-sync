# Refactor Branch Strategy

## Goals

- Keep `main` stable and releasable at all times.
- Isolate architectural refactors from bug-fix hotpaths.
- Ship in small, test-verified increments.

## Branch Topology

- `main`
  - Production branch, only receives reviewed PRs.
- `codex/refactor-architecture-hardening`
  - Integration branch for refactor work.
  - Should remain green (`pytest`) after every merged slice.
- `codex/refactor-phase-*` (short-lived)
  - Optional sub-branches for scoped slices.
  - Merge back into `codex/refactor-architecture-hardening` when green.

## Execution Rules

1. Every slice must be independently testable and revertable.
2. No behavior-changing refactor without regression tests.
3. Keep feature work off the refactor branch unless strictly required.
4. Prefer extraction + compatibility wrappers over big-bang rewrites.
5. Merge to `main` only when:
   - Unit tests pass
   - Existing workflows (`main.py`, `pipeline.py`, `shorts_maker.py`) remain stable
   - No performance or memory regression in FFmpeg path

## Phase Plan

1. **Phase 1: Planning Safety Rails**
   - Add pure planner validation (`src/core/plan_validation.py`).
   - Validate segment timeline continuity and duration invariants.
   - Add focused unit tests.

2. **Phase 2: Montage Decomposition**
   - Extract planner submodules from `src/core/montage.py`:
     - clip selection
     - beat-to-segment mapping
     - tail coverage
   - Keep `MontageGenerator` as orchestration facade.

3. **Phase 3: Config Separation**
   - Split `PacingConfig` by concern (planning/render/overlay).
   - Add mapper layer from CLI/YAML to composed config objects.

4. **Phase 4: Pipeline Application Layer**
   - Move orchestration from `src/pipeline.py` into application services.
   - Keep CLI entrypoint thin (parse args + call service + exit code).

5. **Phase 5: Integration and Soak Tests**
   - Add small real-media integration fixtures.
   - Add duration/coverage canary checks in CI.

## Current Status

- Active branch: `codex/refactor-architecture-hardening`
- Completed: Phase 1 initial safety rails and tests.

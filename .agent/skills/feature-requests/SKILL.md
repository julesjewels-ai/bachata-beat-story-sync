---
description: Track, plan, and implement feature requests one at a time
---

# Feature Request Skill

A structured workflow for tracking and implementing feature requests in the **Bachata Beat-Story Sync** project. Features are tracked in `features.md` and implemented one at a time using the lifecycle below.

## Feature Lifecycle

Each feature moves through these states:

```
PROPOSED → PLANNED → IN_PROGRESS → IMPLEMENTED → VERIFIED
```

| State         | Meaning                                        |
|---------------|------------------------------------------------|
| `PROPOSED`    | Idea captured, not yet scoped                  |
| `PLANNED`     | Implementation plan written and approved       |
| `IN_PROGRESS` | Actively being coded                           |
| `IMPLEMENTED` | Code complete, awaiting verification           |
| `VERIFIED`    | Tests pass, feature confirmed working          |

## Workflow

### 1. Select Next Feature
- Open `features.md` in this skill directory
- Pick the highest-priority feature in `PROPOSED` or `PLANNED` state
- Only work on **one feature at a time**

### 2. Plan
- Create an implementation plan artifact (standard `implementation_plan.md`)
- Identify which files need changes
- Define the verification approach (tests + manual)
- Get user approval before writing code

### 3. Implement
- Update the feature's status to `IN_PROGRESS` in `features.md`
- Write the code changes per the approved plan
- Keep changes focused — don't scope-creep into other features

### 4. Verify
- Run existing tests: `make test` (or `python -m pytest tests/`)
- Run any new tests added for the feature
- Update the feature's status to `IMPLEMENTED`

### 5. Close
- Confirm with the user that the feature works as expected
- Update the feature's status to `VERIFIED`
- Proceed to the next feature

## File Reference

| File                     | Purpose                                          |
|--------------------------|--------------------------------------------------|
| `SKILL.md`               | This file — workflow instructions                |
| `features.md`            | **Active** feature backlog (proposed/in-progress)|
| `archive/completed.md`   | Full specs of completed features (reference only)|

## Quick Commands

- **Show backlog**: Read `features.md`
- **Start next feature**: Follow the workflow above from step 1
- **Check progress**: Look at status fields in `features.md`

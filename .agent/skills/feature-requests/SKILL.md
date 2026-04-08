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
- Confirm with the user that the feature works as expected
- Update the feature's status to `VERIFIED`

### 5. Archive
- **Move to Archive**: Copy the feature's row from `features.md` to `archive/completed.md`.
- **Remove from Backlog**: Delete the row from `features.md`.
- **Update Count**: Increment the "core features complete" count in the `features.md` header.
- **Maintenance**: Periodically prune full specs from `archive/completed.md` to keep context windows clean.

## File Reference

| File                     | Purpose                                          |
|--------------------------|--------------------------------------------------|
| `SKILL.md`               | This file — workflow instructions                |
| `features.md`            | **Backlog ONLY** — items yet to be implemented   |
| `archive/completed.md`   | **Archive** — historical record of done items    |

## Quick Commands

- **Show backlog**: Read `features.md`
- **Start next feature**: Follow the workflow above from step 1
- **Check progress**: Look at status fields in `features.md`

# Project Context

This is a Python video production automation tool. It uses MoviePy v2 — ensure all code changes are compatible with the MoviePy v2 API (not v1). When in doubt, check the installed version before making assumptions about method signatures or class interfaces.

# Workflow

After any refactoring or bug fix, always run the existing test suite before considering the task complete:

```bash
make test
```

If `make` is unavailable, run directly:

```bash
python -m pytest --tb=short -q
```

# Refactoring Guidelines

When refactoring, prefer incremental decomposition:

1. Extract one module, class, or function at a time
2. Run tests after each extraction
3. Only proceed to the next extraction if tests pass
4. Summarise architectural changes made at the end
---
name: release-check
description: Pre-release validation checklist. Use before tagging a version or publishing to PyPI. Manual invocation only.
disable-model-invocation: true
allowed-tools:
  - Bash(poetry *)
  - Bash(python *)
  - Bash(git *)
  - Read
  - Grep
  - Glob
---

# Release Checklist for v$ARGUMENTS

Run every gate. ALL must pass before release.

## 1. Test Suite
```bash
poetry run pytest tests/ --cov=openclaw_sdk --cov-report=term-missing -x
```
Gate: 0 failures, 90%+ coverage

## 2. Type Checking
```bash
poetry run mypy --strict src/openclaw_sdk
```
Gate: 0 errors

## 3. Linting
```bash
poetry run ruff check src/ tests/ && poetry run black --check src/ tests/
```
Gate: 0 issues

## 4. Docs Build
```bash
PYTHONIOENCODING=utf-8 python -m mkdocs build 2>&1
```
Gate: No broken links or warnings

## 5. Version Consistency
Check that version matches across:
- `pyproject.toml` → `version = "..."`
- `CHANGELOG.md` → has entry for this version
- `STATUS.md` → reflects current state
- `src/openclaw_sdk/__init__.py` → `__version__` if present

## 6. Package Build
```bash
poetry build
```
Gate: Produces .tar.gz and .whl without errors

## 7. Git Status
```bash
git status
git log --oneline -5
```
Gate: Clean working tree, on correct branch

## Report
Summarize: PASS/FAIL for each gate, total test count, coverage %, version string.

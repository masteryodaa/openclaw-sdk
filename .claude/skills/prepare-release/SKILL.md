---
name: prepare-release
description: Prepare and publish a new SDK release. Bumps version, runs quality gate, tags, pushes, and triggers PyPI publish. Use with version argument e.g. /prepare-release 2.2.0
disable-model-invocation: true
allowed-tools:
  - Bash(poetry *)
  - Bash(python *)
  - Bash(git *)
  - Read
  - Edit
  - Grep
  - Glob
  - WebFetch
---

# Prepare Release v$ARGUMENTS

Full release pipeline. ALL gates must pass before tagging.

## Step 1: Validate Version Argument
- `$ARGUMENTS` must be a valid semver (e.g. `2.2.0`)
- Must be greater than current version in `pyproject.toml`
- If invalid or missing, stop and ask for correct version

## Step 2: Bump Version
Update version string in all locations:
```bash
grep -n 'version' pyproject.toml | head -3
```
Edit `pyproject.toml` → `version = "$ARGUMENTS"`

Check if `src/openclaw_sdk/__init__.py` has `__version__` — update it too if present.

## Step 3: Update CHANGELOG
- Read `CHANGELOG.md`
- Add a new section for v$ARGUMENTS at the top with today's date
- Summarize changes since last release using:
```bash
git log --oneline $(git describe --tags --abbrev=0 2>/dev/null || echo HEAD~10)..HEAD
```

## Step 4: Quality Gate (ALL must pass)

### 4a. Tests
```bash
poetry run pytest tests/ --cov=openclaw_sdk --cov-report=term-missing -x -q
```
Gate: 0 failures, 90%+ coverage

### 4b. Type Checking
```bash
poetry run mypy --strict src/openclaw_sdk
```
Gate: 0 errors

### 4c. Linting
```bash
poetry run ruff check src/ tests/ && poetry run black --check src/ tests/
```
Gate: 0 issues

### 4d. Docs Build
```bash
PYTHONIOENCODING=utf-8 python -m mkdocs build --strict 2>&1 | tail -5
```
Gate: No errors

### 4e. Package Build
```bash
poetry build
```
Gate: Produces .tar.gz and .whl

## Step 5: Commit Version Bump
```bash
git add pyproject.toml CHANGELOG.md src/openclaw_sdk/__init__.py
git commit -m "chore: bump version to v$ARGUMENTS"
```

## Step 6: Tag and Push
```bash
git tag -a "v$ARGUMENTS" -m "v$ARGUMENTS"
git push origin main
git push origin "v$ARGUMENTS"
```

## Step 7: Trigger PyPI Publish
Tell the user to create a GitHub Release at:
  https://github.com/masteryodaa/openclaw-sdk/releases/new?tag=v$ARGUMENTS

- Tag: `v$ARGUMENTS` (already pushed)
- Title: `v$ARGUMENTS`
- Description: paste the CHANGELOG entry
- Click "Publish release" → triggers the PyPI workflow

## Step 8: Verify
After user publishes the release, check:
- Workflow status: https://github.com/masteryodaa/openclaw-sdk/actions/workflows/publish.yml
- PyPI page: https://pypi.org/p/openclaw-sdk/

## Report
| Gate | Result |
|------|--------|
| Tests | PASS/FAIL (count, coverage%) |
| mypy --strict | PASS/FAIL |
| ruff + black | PASS/FAIL |
| Docs build | PASS/FAIL |
| Package build | PASS/FAIL |
| Version bumped | $ARGUMENTS |
| Tag pushed | v$ARGUMENTS |
| Release URL | https://github.com/masteryodaa/openclaw-sdk/releases/new?tag=v$ARGUMENTS |

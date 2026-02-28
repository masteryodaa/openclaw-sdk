---
name: verify-sdk
description: Run the full SDK quality gate — pytest, mypy, and ruff. Use after making code changes to verify nothing is broken.
allowed-tools:
  - Bash(poetry *)
  - Bash(python *)
  - Read
  - Grep
---

# SDK Verification

Run all three quality checks in sequence. Report results clearly.

## Step 1: Tests
```bash
poetry run pytest tests/ --cov=openclaw_sdk --cov-report=term-missing -x -q
```

## Step 2: Type Checking
```bash
poetry run mypy --strict src/openclaw_sdk
```

## Step 3: Linting
```bash
poetry run ruff check src/ tests/ && poetry run black --check src/ tests/
```

## After Running
- If ALL pass: report "SDK verification PASSED" with test count and coverage %
- If ANY fail: report which gate failed, show the error output, and suggest fixes
- Do NOT mark work as complete until all 3 gates pass

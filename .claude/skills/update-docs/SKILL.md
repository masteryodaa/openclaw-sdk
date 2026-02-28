---
name: update-docs
description: Find and update documentation after code changes. Use after implementing features, fixing bugs, or changing APIs to keep docs in sync.
allowed-tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Bash(python -m mkdocs build *)
---

# Update Documentation

After code changes, find and update all affected documentation.

## Step 1: Identify What Changed
Check `$ARGUMENTS` or recent git diff to understand what changed:
```bash
git diff --name-only HEAD~1
```

## Step 2: Find Affected Docs
Search for references to changed modules/classes/functions in docs/:
- `docs/guides/` — feature guides
- `docs/api/` — API reference pages
- `docs/getting-started/` — quickstart guides
- `docs/examples/` — example code
- `CHANGELOG.md` — add entry for the change
- `README.md` — update if public API changed

## Step 3: Update Each File
- API pages use mkdocstrings `::: module.Class` directives (auto-generated from docstrings)
- If docstrings changed, API pages update automatically — just verify the build
- For guide pages, update prose and code examples manually
- Add CHANGELOG.md entry under the appropriate version heading

## Step 4: Verify Build
```bash
PYTHONIOENCODING=utf-8 python -m mkdocs build 2>&1 | tail -5
```

If build succeeds with no warnings about broken links, docs are updated.

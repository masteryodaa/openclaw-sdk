---
name: deploy-docs
description: Build and deploy documentation to GitHub Pages. Verifies the build locally, then triggers the GitHub Actions workflow. Use after docs/code changes to update the live site.
disable-model-invocation: true
allowed-tools:
  - Bash(python *)
  - Bash(git *)
  - Bash(curl *)
  - Read
  - Grep
  - Glob
  - WebFetch
---

# Deploy Documentation

Build docs locally to verify, then trigger the GitHub Actions deploy workflow.

## Step 1: Verify Local Build
```bash
PYTHONIOENCODING=utf-8 python -m mkdocs build --strict 2>&1 | tail -10
```
Gate: Must succeed with no errors. If it fails, fix the issue before proceeding.

## Step 2: Check Git Status
```bash
git status
```
- If there are uncommitted docs/source changes, warn the user — those changes won't be in the deployed build unless pushed first.
- If clean and up to date with remote, proceed.

## Step 3: Trigger Deploy Workflow
```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/masteryodaa/openclaw-sdk/actions/workflows/docs.yml/dispatches \
  -d '{"ref":"main"}'
```
- If `$GITHUB_TOKEN` is not set, tell the user to either:
  - Push changes to main (auto-triggers the workflow), OR
  - Go to https://github.com/masteryodaa/openclaw-sdk/actions/workflows/docs.yml and click "Run workflow"

## Step 4: Verify Deployment
Check the workflow status:
```bash
curl -s \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/masteryodaa/openclaw-sdk/actions/workflows/docs.yml/runs?per_page=1 \
  | python -c "import sys,json; r=json.load(sys.stdin)['workflow_runs'][0]; print(f'Run #{r[\"run_number\"]}: {r[\"status\"]} ({r[\"conclusion\"] or \"in progress\"})')"
```
If no token available, use WebFetch to check:
  https://github.com/masteryodaa/openclaw-sdk/actions/workflows/docs.yml

## Report
- Build result: PASS/FAIL
- Deploy triggered: YES/NO
- Live URL: https://masteryodaa.github.io/openclaw-sdk/

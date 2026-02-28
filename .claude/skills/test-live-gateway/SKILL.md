---
name: test-live-gateway
description: Run integration tests against the live OpenClaw gateway at ws://127.0.0.1:18789. Use when verifying SDK changes work against the real gateway.
allowed-tools:
  - Bash(poetry *)
  - Bash(python *)
  - Read
  - Grep
---

# Live Gateway Integration Tests

Test the SDK against the live OpenClaw gateway running on this system.

## Step 1: Check Gateway Health
```bash
python -c "import asyncio, websockets; asyncio.run(websockets.connect('ws://127.0.0.1:18789/gateway'))" 2>&1 || echo "GATEWAY UNREACHABLE"
```

## Step 2: Run Integration Tests
```bash
poetry run pytest tests/integration/ -v --tb=short
```

## Step 3: Specific Feature Test (if $ARGUMENTS provided)
```bash
poetry run pytest tests/integration/ -k "$ARGUMENTS" -v
```

## Important
- Gateway must be running at `ws://127.0.0.1:18789/gateway`
- If gateway is unreachable, report it — do NOT run tests that will all skip
- Auth requires device identity files at `~/.openclaw/identity/`
- Reference: `.claude/context/protocol-notes.md` for verified protocol details

---
paths:
  - "tests/**/*.py"
  - "conftest.py"
---

# Testing Rules

- `asyncio_mode = "auto"` in pyproject.toml — do NOT add `@pytest.mark.asyncio` to tests
- All unit tests use `MockGateway` — no live OpenClaw required
- MockGateway: pre-emit events BEFORE calling `execute()` (asyncio.Queue pattern)
- Integration tests: skip when gateway port unreachable OR health returns unhealthy
- Integration tests use `@pytest.mark.integration` marker
- 90%+ coverage required on all modules
- Run tests: `poetry run pytest tests/ --cov=openclaw_sdk --cov-report=term-missing -x`
- Run specific test: `poetry run pytest tests/unit/test_client.py -v`
- Run by pattern: `poetry run pytest tests/ -k "test_connect" -v`
- Always run full test suite after changes to verify no regressions
- Token usage: NOT available per-query (gateway limitation). Cumulative totals in sessions.list only
- Real gateway sends `agent`/`chat` events, NOT `content`/`done`/`thinking` — SDK handles both

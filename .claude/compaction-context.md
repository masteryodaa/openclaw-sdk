# Post-Compaction Context Reload

You just went through context compaction. Here is critical context to remember:

## Commands
- Tests: `poetry run pytest tests/ --cov=openclaw_sdk --cov-report=term-missing -x`
- Types: `poetry run mypy --strict src/openclaw_sdk`
- Lint: `poetry run ruff check src/ tests/ && poetry run black --check src/ tests/`
- Docs: `PYTHONIOENCODING=utf-8 python -m mkdocs build`

## Protocol Essentials
- All RPC requests MUST include `"type":"req"` — gateway rejects without it
- `idempotencyKey` is MANDATORY in `chat.send`
- Gateway responses use `"payload"` not `"result"`
- Session key format: `"agent:{agent_id}:{session_name}"`
- Full reference: `.claude/context/protocol-notes.md`

## Architecture
- `OpenClawClient` → factory via `.connect()` in core/client.py
- Gateway ABC in gateway/base.py — facade methods are concrete, delegate to `call()`
- `MockGateway` for unit tests — pre-emit events BEFORE `execute()`

## Key Rules
- `datetime.now(timezone.utc)` never `utcnow()`
- structlog: first positional arg is event key
- `_AgentLike` Protocol (never import Agent directly)
- Update docs after code changes
- Windows: `PYTHONIOENCODING=utf-8` for Unicode

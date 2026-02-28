# openclaw-sdk

Python SDK wrapping the OpenClaw autonomous AI agent framework (Node.js/TypeScript).
**We do NOT reimplement execution logic.** OpenClaw runs agents; we wrap its protocol.

## Architecture
```
Python App → openclaw-sdk → OpenClaw Gateway (ws://127.0.0.1:18789/gateway)
```

## Commands
```bash
poetry run pytest tests/ --cov=openclaw_sdk --cov-report=term-missing -x   # Tests
poetry run mypy --strict src/openclaw_sdk                                    # Type check
poetry run ruff check src/ tests/ && poetry run black --check src/ tests/    # Lint
PYTHONIOENCODING=utf-8 python -m mkdocs build                               # Docs build
PYTHONIOENCODING=utf-8 python -m mkdocs serve -a 127.0.0.1:8100             # Docs serve
```

## Non-Negotiable
- `datetime.now(timezone.utc)` — NEVER `datetime.utcnow()` (deprecated 3.12+)
- `mypy --strict` must pass with zero errors at all times
- `idempotencyKey` is MANDATORY in `chat.send` (auto-generated via uuid4)
- All RPC requests MUST include `"type":"req"` field
- Gateway responses use `"payload"` NOT `"result"` field
- structlog: first positional arg IS the event key; never pass `event=` as kwarg
- `_AgentLike` Protocol in structured.py — never import Agent directly (circular)
- MockGateway: pre-emit events BEFORE `execute()` (asyncio.Queue pattern)

## Compaction
When compacting, always preserve: current task context, files modified this session, test results, gateway protocol details discussed, and the current git branch.

## References
- Gateway protocol (VERIFIED): @.claude/context/protocol-notes.md
- Task tracking: @.claude/tasks/TASK_TRACKER.md
- Phase specs: @.claude/tasks/phase-specs.md
- Project status: @STATUS.md

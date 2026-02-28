---
paths:
  - "src/**/*.py"
---

# Python Style Rules

- `datetime.now(timezone.utc)` — NEVER `datetime.utcnow()` (deprecated 3.12+)
- `Pipeline(client)` — always takes `OpenClawClient` as first argument
- `ShellToolConfig.allowed_commands = None` means all allowed; `[]` means none allowed
- `_AgentLike` Protocol in structured.py — never import Agent directly (causes circular import)
- `TYPE_CHECKING` pattern to avoid circular imports in pipeline.py
- fastapi.py: module docstring must be BEFORE `from __future__ import annotations` (ruff E402)
- structlog: first positional arg IS the event key; never pass `event=` as kwarg
- All async functions use `async/await`, never blocking I/O
- Runtime deps ONLY: pydantic, websockets, httpx, structlog
- FastAPI is optional: `pip install openclaw-sdk[fastapi]`
- Dev tools (pytest, mypy, ruff, black) live in `[tool.poetry.dev-dependencies]` only
- Never use `Any` as a production type — always provide proper type annotations
- Pydantic v2 models for all data structures

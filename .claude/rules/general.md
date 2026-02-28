# General Conventions

- `mypy --strict` must pass with zero errors at all times
- `ruff check` and `black --check` must pass before any commit
- Production-ready code only — no workarounds, no temporary fixes, no TODO hacks
- No hardcoded secrets, API keys, or credentials in source code
- Conventional commit messages: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`
- Gateway facade methods in gateway/base.py are **concrete** (not abstract) — they delegate to `call()`
- Subclasses only implement 5 abstract methods: connect, close, health, call, subscribe
- Always update tracking files (STATUS.md, SPRINT.md, TASK_TRACKER.md, FEEDBACK.md) after work sessions
- Python ^3.11 required (StrEnum dependency)
- Package manager: Poetry (never pip install directly)

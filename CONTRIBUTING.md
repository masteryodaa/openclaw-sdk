# Contributing to openclaw-sdk

Thank you for your interest in contributing! This is the official Python SDK for the [OpenClaw](https://github.com/openclaw/openclaw) autonomous AI agent framework. Whether you're fixing a typo or shipping a new module — all contributions are welcome.

---

## Ways to Contribute

- **Bug reports** — open an issue with steps to reproduce
- **Feature requests** — open an issue describing the use case
- **Pull requests** — bug fixes, new features, documentation improvements
- **Examples** — add real-world usage examples under `live-examples/`
- **Docs** — improve or expand `docs/`

---

## Development Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) package manager
- OpenClaw running locally (`ws://127.0.0.1:18789/gateway`) for integration tests

### Clone & Install

```bash
git clone https://github.com/masteryodaa/openclaw-sdk.git
cd openclaw-sdk
poetry install --with dev
```

### Run Tests

```bash
python -m pytest tests/ -q
```

All unit tests use `MockGateway` — no live OpenClaw required.

### Type Check

```bash
python -m mypy src/ --ignore-missing-imports
```

### Lint & Format

```bash
python -m ruff check src/ tests/
python -m black --check src/ tests/
```

To auto-fix formatting:

```bash
python -m black src/ tests/
python -m ruff check --fix src/ tests/
```

All three checks (pytest, mypy, ruff) must pass before submitting a PR.

---

## Project Structure

```
src/openclaw_sdk/       # SDK source
  core/                 # Client, Agent, config, types
  gateway/              # Protocol gateway (WebSocket RPC)
  pipeline/             # Multi-step agent pipelines
  guardrails/           # Input/output validation
  templates/            # Project template registry
  coordination/         # Supervisor, workflow engine
  tracking/             # Cost tracking
  integrations/         # FastAPI, Flask, Django, Streamlit adapters
tests/
  unit/                 # MockGateway-based tests (always run)
  integration/          # Live gateway tests (skipped if gateway unreachable)
docs/                   # MkDocs documentation
live-examples/          # Full-stack showcase apps
  clawforge/            # AI app builder (FastAPI + Next.js)
  command-center/       # Admin dashboard (FastAPI + vanilla JS)
```

---

## Branching Strategy

Always branch off `main`. Use these prefixes:

| Prefix | When to use | Example |
|--------|-------------|---------|
| `feat/` | New feature or module | `feat/goal-loop-timeout` |
| `fix/` | Bug fix | `fix/pipeline-retry-loop` |
| `docs/` | Docs-only change | `docs/add-guardrails-guide` |
| `test/` | Tests only, no code change | `test/coverage-structured-output` |
| `chore/` | Tooling, deps, CI | `chore/bump-pydantic-v2` |
| `refactor/` | Internal cleanup, no behavior change | `refactor/gateway-base-cleanup` |

### Step-by-step

```bash
# 1. Make sure you're on a fresh main
git checkout main
git pull origin main

# 2. Create your branch
git checkout -b feat/my-feature

# 3. Make changes, write tests
# ...

# 4. Verify everything passes
python -m pytest tests/ -q
python -m mypy src/ --ignore-missing-imports
python -m ruff check src/ tests/

# 5. Commit with a descriptive message
git add <files>
git commit -m "feat(pipeline): add timeout support for long-running steps"

# 6. Push and open a PR
git push origin feat/my-feature
```

---

## Commit Style

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(module): short description
fix(module): short description
docs(module): short description
chore: short description
test(module): short description
refactor(module): short description
```

**Good examples:**
```
feat(guardrails): add regex-based output filter
fix(gateway): handle reconnect on WebSocket timeout
docs(pipeline): add multi-step example with structured output
test(coordination): cover supervisor fallback behavior
chore: upgrade websockets to 13.x
```

**Rules:**
- Use the imperative mood — "add", not "added" or "adds"
- Keep the subject line under 72 characters
- Reference issues when relevant: `fix(agent): handle empty response (#42)`
- No period at the end of the subject line

---

## Pull Request Guidelines

1. **Branch from `main`** — never commit directly to `main`
2. **Write tests** — new features need unit tests; bug fixes need regression tests
3. **Keep mypy clean** — `python -m mypy src/ --ignore-missing-imports` must pass
4. **Update docs** — if you add/change a public API, update the relevant `docs/` page
5. **One PR per concern** — keep PRs focused and small; easier to review, faster to merge
6. **Descriptive PR title** — same format as commit messages (`feat(module): description`)
7. **Fill the PR template** — describe what changed and why, link related issues

### PR Checklist

Before opening a PR, make sure:

- [ ] `python -m pytest tests/ -q` passes
- [ ] `python -m mypy src/ --ignore-missing-imports` passes
- [ ] `python -m ruff check src/ tests/` passes
- [ ] `python -m black --check src/ tests/` passes
- [ ] New/changed public API has updated `docs/` page
- [ ] New features have unit tests in `tests/unit/`

---

## Code Style

- **Formatter**: `black` (line length 100)
- **Linter**: `ruff`
- **Types**: `mypy` (use `--ignore-missing-imports` for optional deps)
- **Async**: always `async/await`, never blocking calls in async context
- **Dates**: always `datetime.now(timezone.utc)`, never `datetime.utcnow()`
- **Imports**: stdlib → third-party → local, separated by blank lines
- **Docstrings**: Google style, required on all public classes and methods

---

## Reporting Bugs

Please include:
- Python version (`python --version`)
- SDK version (`pip show openclaw-sdk`)
- OpenClaw version (visible in gateway hello response)
- Minimal reproduction code
- Full error traceback

Open an issue at: https://github.com/masteryodaa/openclaw-sdk/issues

---

## Gateway Protocol Notes

The OpenClaw gateway protocol is documented in `.claude/context/protocol-notes.md`.
Always verify method names/params against a live gateway before implementing — the protocol
has nuances that differ from what older docs may suggest.

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

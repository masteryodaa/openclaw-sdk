# Phase Specifications — Per-Agent Instructions

Each section here is a self-contained brief for one Claude Code agent session.
Before starting any phase, read `CLAUDE.md` (global context) + this section.
After finishing, update `TASK_TRACKER.md`.

---

## MD1 — Scaffold & Types {#md1}

**Read first**: `CLAUDE.md`, `plan.md` Sections 2, 3, 4.1–4.6, 4.14

**Your job**: Build the installable skeleton. No logic — pure types, enums, models.

### pyproject.toml requirements
```toml
[tool.poetry]
name = "openclaw-sdk"
version = "0.1.0"
description = "Python SDK for the OpenClaw autonomous AI agent framework"
packages = [{ include = "openclaw_sdk", from = "src" }]

[tool.poetry.dependencies]
python = "^3.10"
pydantic = ">=2.0"
websockets = ">=12.0"
httpx = ">=0.25"
structlog = ">=23.0"

[tool.poetry.extras]
fastapi = ["fastapi>=0.100", "uvicorn"]

[tool.poetry.dev-dependencies]
pytest = ">=7.0"
pytest-asyncio = ">=0.21"
pytest-cov = ">=4.0"
mypy = ">=1.0"
ruff = ">=0.1"
black = ">=23.0"

[tool.mypy]
strict = true
python_version = "3.10"

[tool.ruff]
target-version = "py310"
line-length = 100
```

### Files to create (in order)
1. `src/openclaw_sdk/__init__.py` — export public API
2. `src/openclaw_sdk/__version__.py` — `__version__ = "0.1.0"`
3. `src/openclaw_sdk/core/constants.py` — all StrEnum classes
4. `src/openclaw_sdk/core/exceptions.py` — full exception hierarchy
5. `src/openclaw_sdk/core/config.py` — ClientConfig, AgentConfig, ExecutionOptions
6. `src/openclaw_sdk/core/types.py` — all type models (use `datetime.now(timezone.utc)`)
7. `src/openclaw_sdk/tools/config.py` — all tool configs
8. `src/openclaw_sdk/channels/config.py` — all channel configs
9. `src/openclaw_sdk/memory/config.py` — MemoryConfig
10. All `__init__.py` stubs for remaining packages

### Key constraints
- `datetime.now(timezone.utc)` — never `datetime.utcnow()`
- `ShellToolConfig.allowed_commands: list[str] | None = None` (None=all, []=none)
- Pydantic v2 syntax throughout (`model_config`, not `class Config`)
- `from __future__ import annotations` at top of every file

### Success check
```bash
poetry install
poetry run mypy --strict src/openclaw_sdk
poetry run python -c "from openclaw_sdk import __version__; print(__version__)"
```

---

## MD2 — Gateway Base + Mock {#md2}

**Read first**: `CLAUDE.md`, `plan.md` Sections 1.3, 4.15

**Your job**: The Gateway ABC and a fully functional MockGateway that all other
tests will depend on. This is the testing foundation — get it right.

### gateway/base.py
- Abstract base class with these abstract methods:
  - `async connect() -> None`
  - `async close() -> None`
  - `async health() -> HealthStatus`
  - `async call(method: str, params: dict | None = None) -> dict`
  - `async subscribe(event_types: list[str] | None = None) -> AsyncIterator[StreamEvent]`
- Non-abstract facade methods are stubs that call `self.call()` with the right method string
- Mark all facade stubs with `# VERIFY: method name against protocol-notes.md`

### gateway/mock.py
MockGateway must support:
```python
mock = MockGateway()
mock.register("sessions.list", {"sessions": []})  # static response
mock.register("chat.send", lambda params: {"taskId": "task_1"})  # dynamic
mock.emit_event(StreamEvent(event_type=EventType.CONTENT, data={"content": "hello"}))
```

### tests/conftest.py
```python
@pytest.fixture
def mock_gateway():
    return MockGateway()

@pytest.fixture
async def connected_mock_gateway():
    gw = MockGateway()
    await gw.connect()
    yield gw
    await gw.close()
```

### Success check
```bash
poetry run pytest tests/unit/test_mock_gateway.py -v
```

---

## MD3A — Protocol Gateway {#md3a}

**Read first**: `CLAUDE.md`, `plan.md` Section 4.15, `.claude/context/protocol-notes.md` (REQUIRED)

**STOP**: Do not start this phase until `protocol-notes.md` has real protocol data.

**Your job**: The real WebSocket client. This is the most risk-prone module.
Implement conservatively — prefer `call()` over adding lots of facade methods.

### gateway/protocol.py key requirements
1. **Connection**: `websockets.connect()` with auto-reconnect + exponential backoff (start 1s, max 30s, jitter)
2. **Request correlation**: Generate unique IDs; maintain `_pending: dict[str, asyncio.Future]`
3. **Event dispatch**: Separate task consuming incoming messages; route responses to futures, events to subscriber queues
4. **Handshake**: Implement exactly as documented in `protocol-notes.md`
5. **Idempotency**: Accept `idempotency_key` in `call()` kwargs; pass through to protocol
6. **Reconnect safety**: Fail in-flight requests with `ConnectionError` on disconnect; let caller retry

### gateway/openai_compat.py
- HTTP-only adapter via httpx AsyncClient
- `POST /v1/chat/completions` → returns `ExecutionResult`
- `POST /v1/responses` → same
- `POST /v1/tools/invoke` → `ToolCall` result
- `call()` and `subscribe()` must raise `NotImplementedError` (HTTP-only)

### Success check
```bash
poetry run pytest tests/unit/test_protocol_gateway.py -v
poetry run mypy --strict src/openclaw_sdk/gateway/
```

---

## MD3B — Managers {#md3b}

**Read first**: `CLAUDE.md`, `plan.md` Sections 4.7–4.9, 4.15

**Your job**: All manager classes that wrap Gateway methods. These are thin — no
business logic. They call `self._gateway.call(method, params)` and parse the result.

### Pattern for every manager method
```python
async def list_schedules(self) -> list[ScheduleConfig]:
    result = await self._gateway.call("cron.list", {})  # VERIFY: method name
    return [ScheduleConfig(**item) for item in result.get("schedules", [])]
```

### Managers to implement
1. `channels/manager.py` — ChannelManager
2. `skills/manager.py` — SkillManager
3. `skills/clawhub.py` — ClawHub (if CLI-only per protocol-notes, shell out instead)
4. `webhooks/manager.py` — WebhookManager
5. `scheduling/manager.py` — ScheduleManager (full cron surface + wake)
6. `utils/logging.py` — structlog JSON setup
7. `utils/async_helpers.py` — `run_sync(coro)`, `with_timeout(coro, seconds)`

### Testing pattern
Every manager test mocks the gateway:
```python
async def test_list_schedules(connected_mock_gateway):
    connected_mock_gateway.register("cron.list", {"schedules": [...]})
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.list_schedules()
    assert len(result) == 1
```

### Success check
```bash
poetry run pytest tests/unit/test_channels.py tests/unit/test_skills.py \
    tests/unit/test_webhooks.py tests/unit/test_scheduling.py -v
```

---

## MD3C — Python-Native Features {#md3c}

**Read first**: `CLAUDE.md`, `plan.md` Sections 4.10–4.13

**Your job**: Four pure-Python modules. No Gateway calls in this phase — these
modules use `Agent` as a dependency injected at runtime, not at import time.

### pipeline/pipeline.py
- `Pipeline(client: OpenClawClient)` — takes client, not agent
- Steps are added with `pipeline.add_step(name, agent_id, prompt_template, output_key="content")`
- `{variable_name}` in prompt_template is replaced with output from the named step
- `await pipeline.run(**initial_variables)` returns `PipelineResult`
- Error in any step sets `PipelineResult.success = False` and stops execution

### output/structured.py
- `StructuredOutput.schema_prompt(model)` → appends JSON schema to prompt
- `StructuredOutput.parse(response, model)` → extracts JSON block, validates with Pydantic
- `StructuredOutput.execute(agent, query, model, max_retries=2)` → retries on parse failure
- Use `json.loads()` with regex to extract first JSON block from response string

### callbacks/handler.py
- `CallbackHandler` is an ABC with all methods having default no-op implementations
- `LoggingCallbackHandler` uses structlog
- `CompositeCallbackHandler(handlers: list[CallbackHandler])` fans out to all handlers
- All callback methods are `async def`

### tracking/cost.py
- `DEFAULT_PRICING: dict[str, dict]` — document clearly as approximate, overridable
- `CostTracker.record(result, agent_id, model, user_id=None)` — calculates cost from TokenUsage
- `CostTracker.get_summary(agent_id=None, user_id=None, since=None)` — filters + aggregates
- `await CostTracker.export_csv(path)` — writes CostEntry rows to CSV

### Success check
```bash
poetry run pytest tests/unit/test_pipeline.py tests/unit/test_structured_output.py \
    tests/unit/test_callbacks.py tests/unit/test_cost_tracker.py -v
```

---

## MD4 — Client, Agent & FastAPI {#md4}

**Read first**: `CLAUDE.md`, `plan.md` Sections 4.16, 4.17, 4.18

**Your job**: Wire everything together. This is the surface developers actually use.

### core/client.py — Auto-detection logic
```python
@classmethod
async def connect(cls, **kwargs) -> "OpenClawClient":
    config = ClientConfig(**kwargs)
    if config.gateway_ws_url:
        gateway = ProtocolGateway(config.gateway_ws_url)
    elif config.openai_base_url:
        gateway = OpenAICompatGateway(config.openai_base_url)
    elif _openclaw_is_running():  # check ws://127.0.0.1:18789/gateway
        gateway = LocalGateway(config)
    else:
        raise ConfigurationError("No OpenClaw gateway found. Run 'openclaw start' or set gateway_ws_url.")
    await gateway.connect()
    return cls(config=config, gateway=gateway, callbacks=kwargs.get("callbacks", []))
```

### core/agent.py — Callback wiring
```python
async def execute(self, query, options=None, callbacks=None, attachments=None):
    all_callbacks = CompositeCallbackHandler(self._client._callbacks + (callbacks or []))
    await all_callbacks.on_execution_start(self.agent_id, query)
    try:
        result = await self._client.gateway.chat(self.agent_id, query, options, attachments)
        await all_callbacks.on_execution_end(self.agent_id, result)
        return result
    except Exception as e:
        await all_callbacks.on_error(self.agent_id, e)
        raise
```

### integrations/fastapi.py
- `get_openclaw_client()` — FastAPI dependency using `Depends()`; reads env vars for config
- `create_agent_router(client, prefix)` — CRUD endpoints + `POST /{agent_id}/execute`
- `create_channel_router(client, prefix)` — configure + login + status
- `create_admin_router(client, prefix)` — skills, clawhub, webhooks, schedules

### Success check
```bash
poetry run pytest tests/unit/test_client.py tests/unit/test_agent.py \
    tests/test_fastapi_integration.py -v
```

---

## MD5A — Examples {#md5a}

**Read first**: `CLAUDE.md`, `plan.md` Section 10 (example usage)

**Your job**: 10 working examples. All must run against MockGateway — no live OpenClaw.
Use `AsyncMock` or `MockGateway` to simulate responses in each example's `__main__` block.
Add a `# RUN: python examples/XX_name.py` comment at top of each file.

Examples to write (follow the patterns in plan.md Section 10):
1. `01_hello_world.py` — connect + create agent + execute + print result
2. `02_streaming.py` — execute_stream + handle events
3. `03_fastapi_backend.py` — full FastAPI app with agent router
4. `04_channel_config.py` — WhatsApp + Telegram setup + login flow
5. `05_tool_config.py` — DatabaseToolConfig + FileToolConfig
6. `06_skills_clawhub.py` — search skills + install + list
7. `07_pipeline.py` — 3-step researcher → writer → reviewer pipeline
8. `08_structured_output.py` — execute_structured with SalesReport model
9. `09_callbacks.py` — custom AuditHandler + LoggingCallbackHandler
10. `10_cost_tracking.py` — CostTracker + CostCallbackHandler + export_csv

---

## MD5B — Integration Tests {#md5b}

**Read first**: `CLAUDE.md`, `plan.md` Section 8, 8.1

**Your job**: Fill gaps and write integration-level tests. Still MockGateway-based
for unit tests; integration tests can use a real local gateway if available.

### Coverage targets
Run `poetry run pytest --cov=openclaw_sdk --cov-report=term-missing` and fill gaps.
Target: every module ≥ 90%. Focus on error paths, edge cases, reconnect scenarios.

### Integration tests structure
```python
# tests/integration/test_protocol_gateway.py
@pytest.mark.integration
async def test_connect_to_real_gateway():
    """Requires openclaw running locally. Skip if not available."""
    pytest.importorskip("openclaw_gateway_available")  # custom marker
    async with ProtocolGateway("ws://127.0.0.1:18789/gateway") as gw:
        status = await gw.health()
        assert status.healthy
```

---

## MD6 — Polish & Release {#md6}

**Read first**: `CLAUDE.md`, `plan.md` Sections 8, 8.1, 8.2

**Your job**: Make it ship-ready.

### README.md must include
1. One-line description
2. "5 lines of code" quickstart (copy from doc.md)
3. Installation (`pip install openclaw-sdk`, prerequisites)
4. Feature matrix table
5. Link to docs/quickstart.md
6. License badge + version badge

### docs/quickstart.md must include
1. Prerequisites: Node.js 22+, `npm install -g openclaw`, `openclaw start`
2. Install: `pip install openclaw-sdk`
3. Hello world example (full, runnable)
4. Streaming example
5. Link to examples/

### Compatibility matrix (add to README.md)
| SDK Version | Min OpenClaw | Max Tested | Notes |
|------------|--------------|------------|-------|
| `0.1.x` | [fill from protocol-notes] | [fill] | Initial release |

### Final gate checklist
```bash
poetry run pytest --cov=openclaw_sdk --cov-report=term-missing
# → all tests pass, coverage ≥ 90%

poetry run mypy --strict src/openclaw_sdk
# → zero errors

poetry run ruff check src/ tests/ && poetry run black --check src/ tests/
# → zero issues

for f in examples/*.py; do poetry run python "$f"; done
# → all examples exit 0
```

# Plugins

The OpenClaw SDK includes an extensible plugin system that lets you hook into
every stage of agent execution. Plugins can observe, modify, or augment SDK
behaviour without changing application code. The system provides six lifecycle
hook points, a central registry, and automatic discovery via Python entry points.

## Quick Start

```python
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from openclaw_sdk.plugins import (
    Plugin,
    PluginHook,
    PluginMetadata,
    PluginRegistry,
)


class TimingPlugin(Plugin):
    """Logs execution duration for every agent call."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="timing",
            version="1.0.0",
            description="Logs execution timing",
            author="my-team",
        )

    def hooks(self) -> dict[PluginHook, Callable[..., Awaitable[Any]]]:
        return {
            PluginHook.POST_EXECUTE: self._on_post_execute,
        }

    async def _on_post_execute(self, **kwargs: Any) -> None:
        result = kwargs.get("result")
        if result is not None:
            print(f"Execution took {result.latency_ms}ms")


async def main():
    registry = PluginRegistry()

    # Register the plugin (calls setup() automatically)
    await registry.register(TimingPlugin())

    # List registered plugins
    for meta in registry.list_plugins():
        print(f"Active plugin: {meta.name} v{meta.version}")

    # Dispatch a hook manually (the SDK does this internally)
    await registry.hooks.dispatch(PluginHook.POST_EXECUTE, result=some_result)

asyncio.run(main())
```

## Plugin ABC

Every plugin extends the `Plugin` abstract base class. You must implement two
methods and may optionally override two lifecycle hooks:

```python
from openclaw_sdk.plugins import Plugin, PluginHook, PluginMetadata

class MyPlugin(Plugin):

    def metadata(self) -> PluginMetadata:
        """Return a PluginMetadata identifying this plugin."""
        return PluginMetadata(name="my-plugin", version="0.1.0")

    def hooks(self) -> dict[PluginHook, Callable[..., Awaitable[Any]]]:
        """Return a mapping of hook points to async handler functions."""
        return {
            PluginHook.PRE_EXECUTE: self._before,
            PluginHook.ON_ERROR: self._on_error,
        }

    async def setup(self) -> None:
        """Called once when the plugin is registered. Use for initialisation."""
        ...

    async def teardown(self) -> None:
        """Called once when the plugin is unregistered. Use for cleanup."""
        ...
```

| Method       | Required | Description                                          |
|--------------|----------|------------------------------------------------------|
| `metadata()` | Yes      | Returns a `PluginMetadata` identifying the plugin    |
| `hooks()`    | Yes      | Returns a dict mapping `PluginHook` to async handler |
| `setup()`    | No       | Async initialisation, called on registration         |
| `teardown()` | No       | Async cleanup, called on unregistration              |

## PluginMetadata

`PluginMetadata` is a Pydantic model that describes a plugin:

```python
from openclaw_sdk.plugins import PluginMetadata

meta = PluginMetadata(
    name="my-plugin",
    version="2.0.0",
    description="Adds custom telemetry",
    author="engineering-team",
)
```

| Field         | Type  | Default | Description                         |
|---------------|-------|---------|-------------------------------------|
| `name`        | `str` | --      | Unique plugin name (required)       |
| `version`     | `str` | `"0.1.0"` | Semantic version string          |
| `description` | `str` | `""`    | Human-readable description          |
| `author`      | `str` | `""`    | Author or team name                 |

!!! warning "Unique names required"
    The registry enforces unique plugin names. Attempting to register a second
    plugin with the same name raises `ValueError`.

## PluginHook

`PluginHook` is a `StrEnum` with six hook points that cover the full agent
execution lifecycle:

| Hook              | Value             | When it fires                              |
|-------------------|-------------------|--------------------------------------------|
| `PRE_EXECUTE`     | `"pre_execute"`   | Before an agent execution starts           |
| `POST_EXECUTE`    | `"post_execute"`  | After an agent execution completes         |
| `ON_ERROR`        | `"on_error"`      | When an execution raises an error          |
| `ON_TOOL_CALL`    | `"on_tool_call"`  | When the agent invokes a tool              |
| `ON_TOOL_RESULT`  | `"on_tool_result"`| When a tool returns its result             |
| `ON_STREAM`       | `"on_stream"`     | On each streaming chunk during execution   |

Each handler receives keyword arguments relevant to the hook point. For example,
`POST_EXECUTE` handlers receive `result`, while `ON_ERROR` handlers receive
`error`.

```python
async def my_error_handler(**kwargs: Any) -> None:
    error = kwargs.get("error")
    print(f"Agent error: {error}")
```

!!! tip "Errors are isolated"
    If a hook handler raises an exception, the error is logged but never
    propagated. One faulty plugin cannot break the dispatch chain or crash
    the SDK.

## PluginRegistry

`PluginRegistry` is the central manager for plugin lifecycle and hook dispatch:

```python
from openclaw_sdk.plugins import PluginRegistry

registry = PluginRegistry()

# Register a plugin (async — calls plugin.setup())
await registry.register(my_plugin)

# Unregister by name (async — calls plugin.teardown())
await registry.unregister("my-plugin")

# List all registered plugins
for meta in registry.list_plugins():
    print(f"{meta.name} v{meta.version}")

# Dispatch a hook to all registered handlers
await registry.hooks.dispatch(PluginHook.PRE_EXECUTE, query="Hello")
```

| Method              | Returns               | Description                                   |
|---------------------|-----------------------|-----------------------------------------------|
| `register(plugin)`  | `None`                | Register plugin, call `setup()`, wire hooks   |
| `unregister(name)`  | `None`                | Remove hooks, call `teardown()`, de-register  |
| `list_plugins()`    | `list[PluginMetadata]`| Metadata for all registered plugins           |
| `discover(group)`   | `list[str]`           | Discover entry-point names (see below)        |
| `hooks`             | `HookManager`         | Access the hook dispatch manager              |

## HookManager

The `HookManager` is the low-level dispatcher that the registry delegates to.
You rarely interact with it directly, but it is available via `registry.hooks`:

```python
# Manual handler registration (prefer using Plugin.hooks() instead)
registry.hooks.register(PluginHook.ON_STREAM, my_stream_handler)

# Dispatch a hook event
await registry.hooks.dispatch(PluginHook.ON_STREAM, chunk="Hello")

# Remove a handler
registry.hooks.unregister(PluginHook.ON_STREAM, my_stream_handler)
```

## Entry-Point Discovery

Plugins can be discovered automatically from installed Python packages using
`importlib.metadata` entry points. This enables a "pip install and go"
experience for third-party plugins.

### Publishing a Plugin Package

In your plugin package's `pyproject.toml`, declare the entry point:

```toml
[project.entry-points."openclaw_sdk.plugins"]
my_plugin = "my_package.plugin:MyPlugin"
```

### Discovering Plugins

```python
registry = PluginRegistry()

# Discover all installed plugins in the default group
names = registry.discover()  # group="openclaw_sdk.plugins"
print(f"Found plugins: {names}")

# Use a custom entry-point group
names = registry.discover(group="my_org.openclaw_plugins")
```

| Parameter | Type  | Default                    | Description                     |
|-----------|-------|----------------------------|---------------------------------|
| `group`   | `str` | `"openclaw_sdk.plugins"`   | Entry-point group to search     |

!!! note "Discovery vs. registration"
    `discover()` only returns entry-point names; it does not instantiate or
    register the plugins. You must load and register them yourself after
    discovery. This gives you control over which discovered plugins are
    actually activated.

## Full Example: Logging + Metrics Plugin

```python
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from openclaw_sdk.plugins import (
    Plugin,
    PluginHook,
    PluginMetadata,
    PluginRegistry,
)


class ObservabilityPlugin(Plugin):
    """Captures pre/post execution events and tool calls."""

    def __init__(self) -> None:
        self._call_count = 0

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="observability",
            version="1.0.0",
            description="Logs execution lifecycle events",
        )

    def hooks(self) -> dict[PluginHook, Callable[..., Awaitable[Any]]]:
        return {
            PluginHook.PRE_EXECUTE: self._pre,
            PluginHook.POST_EXECUTE: self._post,
            PluginHook.ON_TOOL_CALL: self._tool,
            PluginHook.ON_ERROR: self._error,
        }

    async def setup(self) -> None:
        print("ObservabilityPlugin initialised")

    async def teardown(self) -> None:
        print(f"ObservabilityPlugin shutting down ({self._call_count} calls)")

    async def _pre(self, **kwargs: Any) -> None:
        self._call_count += 1
        print(f"[pre] Starting execution #{self._call_count}")

    async def _post(self, **kwargs: Any) -> None:
        result = kwargs.get("result")
        if result:
            print(f"[post] Completed in {result.latency_ms}ms")

    async def _tool(self, **kwargs: Any) -> None:
        print(f"[tool] Tool called: {kwargs}")

    async def _error(self, **kwargs: Any) -> None:
        print(f"[error] {kwargs.get('error')}")


async def main():
    registry = PluginRegistry()
    await registry.register(ObservabilityPlugin())

    # The SDK dispatches hooks internally during agent.execute()
    # For demonstration, dispatch manually:
    await registry.hooks.dispatch(PluginHook.PRE_EXECUTE, query="Hello")
    await registry.hooks.dispatch(
        PluginHook.POST_EXECUTE, result=None
    )

    await registry.unregister("observability")

asyncio.run(main())
```

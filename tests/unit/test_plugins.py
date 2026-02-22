"""Tests for plugins/ — registry, hooks, and plugin lifecycle."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from openclaw_sdk.plugins.base import Plugin, PluginHook, PluginMetadata
from openclaw_sdk.plugins.hooks import HookManager
from openclaw_sdk.plugins.registry import PluginRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class SamplePlugin(Plugin):
    """A minimal plugin for testing."""

    def __init__(self, name: str = "sample", version: str = "1.0.0") -> None:
        self._name = name
        self._version = version
        self.setup_called = False
        self.teardown_called = False
        self.pre_execute_calls: list[dict[str, Any]] = []
        self.post_execute_calls: list[dict[str, Any]] = []

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name=self._name, version=self._version, description="A test plugin")

    def hooks(self) -> dict[PluginHook, Callable[..., Awaitable[Any]]]:
        return {
            PluginHook.PRE_EXECUTE: self._on_pre_execute,
            PluginHook.POST_EXECUTE: self._on_post_execute,
        }

    async def setup(self) -> None:
        self.setup_called = True

    async def teardown(self) -> None:
        self.teardown_called = True

    async def _on_pre_execute(self, **kwargs: Any) -> None:
        self.pre_execute_calls.append(kwargs)

    async def _on_post_execute(self, **kwargs: Any) -> None:
        self.post_execute_calls.append(kwargs)


class EmptyPlugin(Plugin):
    """Plugin with no hooks."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="empty")

    def hooks(self) -> dict[PluginHook, Callable[..., Awaitable[Any]]]:
        return {}

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass


class BrokenHookPlugin(Plugin):
    """Plugin whose hook always raises."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="broken_hook")

    def hooks(self) -> dict[PluginHook, Callable[..., Awaitable[Any]]]:
        return {PluginHook.PRE_EXECUTE: self._broken}

    async def _broken(self, **kwargs: Any) -> None:
        raise RuntimeError("hook exploded")


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


async def test_register_plugin() -> None:
    registry = PluginRegistry()
    plugin = SamplePlugin()
    await registry.register(plugin)

    names = [m.name for m in registry.list_plugins()]
    assert "sample" in names


async def test_duplicate_registration_raises() -> None:
    registry = PluginRegistry()
    await registry.register(SamplePlugin())
    with pytest.raises(ValueError, match="already registered"):
        await registry.register(SamplePlugin())


async def test_unregister_plugin() -> None:
    registry = PluginRegistry()
    plugin = SamplePlugin()
    await registry.register(plugin)
    await registry.unregister("sample")

    assert registry.list_plugins() == []
    assert plugin.teardown_called


async def test_unregister_nonexistent_raises() -> None:
    registry = PluginRegistry()
    with pytest.raises(KeyError, match="not registered"):
        await registry.unregister("nonexistent")


async def test_hook_dispatch() -> None:
    registry = PluginRegistry()
    plugin = SamplePlugin()
    await registry.register(plugin)

    await registry.hooks.dispatch(PluginHook.PRE_EXECUTE, agent_id="a1", query="hello")
    assert len(plugin.pre_execute_calls) == 1
    assert plugin.pre_execute_calls[0] == {"agent_id": "a1", "query": "hello"}


async def test_hook_error_isolation() -> None:
    """A broken hook should not prevent other hooks from running."""
    registry = PluginRegistry()
    broken = BrokenHookPlugin()
    good = SamplePlugin(name="good")
    await registry.register(broken)
    await registry.register(good)

    # Should not raise despite broken hook
    await registry.hooks.dispatch(PluginHook.PRE_EXECUTE, agent_id="a1")
    assert len(good.pre_execute_calls) == 1


async def test_setup_called_on_register() -> None:
    registry = PluginRegistry()
    plugin = SamplePlugin()
    assert not plugin.setup_called
    await registry.register(plugin)
    assert plugin.setup_called


async def test_teardown_called_on_unregister() -> None:
    registry = PluginRegistry()
    plugin = SamplePlugin()
    await registry.register(plugin)
    assert not plugin.teardown_called
    await registry.unregister("sample")
    assert plugin.teardown_called


async def test_list_plugins() -> None:
    registry = PluginRegistry()
    await registry.register(SamplePlugin(name="a", version="1.0.0"))
    await registry.register(SamplePlugin(name="b", version="2.0.0"))

    metas = registry.list_plugins()
    assert len(metas) == 2
    names = {m.name for m in metas}
    assert names == {"a", "b"}


async def test_discover_entry_points() -> None:
    """Discover should use importlib.metadata.entry_points."""
    mock_ep = MagicMock()
    mock_ep.name = "my-plugin"

    with patch(
        "importlib.metadata.entry_points", return_value=[mock_ep]
    ) as mock_fn:
        registry = PluginRegistry()
        discovered = registry.discover(group="openclaw_sdk.plugins")
        mock_fn.assert_called_once_with(group="openclaw_sdk.plugins")
        assert discovered == ["my-plugin"]


async def test_multiple_hooks() -> None:
    """Plugin with multiple hooks should have all dispatched correctly."""
    registry = PluginRegistry()
    plugin = SamplePlugin()
    await registry.register(plugin)

    await registry.hooks.dispatch(PluginHook.PRE_EXECUTE, step="pre")
    await registry.hooks.dispatch(PluginHook.POST_EXECUTE, step="post")

    assert len(plugin.pre_execute_calls) == 1
    assert plugin.pre_execute_calls[0] == {"step": "pre"}
    assert len(plugin.post_execute_calls) == 1
    assert plugin.post_execute_calls[0] == {"step": "post"}


async def test_empty_hooks() -> None:
    """A plugin with no hooks should register fine and dispatches should be no-ops."""
    registry = PluginRegistry()
    await registry.register(EmptyPlugin())

    # Dispatching any hook should not raise
    await registry.hooks.dispatch(PluginHook.PRE_EXECUTE, foo="bar")
    assert registry.list_plugins()[0].name == "empty"


async def test_hooks_property() -> None:
    """Registry.hooks should return the HookManager instance."""
    registry = PluginRegistry()
    assert isinstance(registry.hooks, HookManager)

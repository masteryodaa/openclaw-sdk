"""Hook dispatch manager for the plugin system."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from openclaw_sdk.plugins.base import PluginHook

logger = structlog.get_logger(__name__)


class HookManager:
    """Dispatches hooks to registered handlers.

    Errors from individual handlers are logged but never propagated,
    ensuring one faulty plugin does not break the entire pipeline.
    """

    def __init__(self) -> None:
        self._hooks: dict[PluginHook, list[Callable[..., Awaitable[Any]]]] = {
            hook: [] for hook in PluginHook
        }

    def register(self, hook: PluginHook, handler: Callable[..., Awaitable[Any]]) -> None:
        """Register a handler for the given hook point."""
        self._hooks[hook].append(handler)

    def unregister(self, hook: PluginHook, handler: Callable[..., Awaitable[Any]]) -> None:
        """Remove a previously registered handler.

        Raises:
            ValueError: If the handler was not registered for the given hook.
        """
        self._hooks[hook].remove(handler)

    async def dispatch(self, hook: PluginHook, **kwargs: Any) -> None:
        """Call all handlers for the given hook.

        Each handler receives ``**kwargs``. Errors are logged but not
        propagated so that one failing handler cannot break the dispatch chain.
        """
        for handler in self._hooks.get(hook, []):
            try:
                await handler(**kwargs)
            except Exception as exc:  # noqa: BLE001
                logger.warning("plugin_hook_error", hook=hook.value, error=str(exc))

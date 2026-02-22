"""Central registry for SDK plugins."""
from __future__ import annotations

import structlog

from openclaw_sdk.plugins.base import Plugin, PluginMetadata
from openclaw_sdk.plugins.hooks import HookManager

logger = structlog.get_logger(__name__)


class PluginRegistry:
    """Central registry for SDK plugins.

    Supports manual registration and entry-point discovery via
    ``importlib.metadata``.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._hooks = HookManager()

    async def register(self, plugin: Plugin) -> None:
        """Register a plugin and wire its hooks.

        Calls :meth:`Plugin.setup` before wiring hooks so the plugin can
        initialise resources.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        meta = plugin.metadata()
        if meta.name in self._plugins:
            raise ValueError(f"Plugin '{meta.name}' already registered")
        await plugin.setup()
        for hook, handler in plugin.hooks().items():
            self._hooks.register(hook, handler)
        self._plugins[meta.name] = plugin
        logger.info("plugin_registered", plugin=meta.name, version=meta.version)

    async def unregister(self, name: str) -> None:
        """Unregister a plugin by name, calling its teardown and removing hooks.

        Raises:
            KeyError: If no plugin with the given name is registered.
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not registered")
        plugin = self._plugins.pop(name)
        # Remove all hooks registered by this plugin
        for hook, handler in plugin.hooks().items():
            try:
                self._hooks.unregister(hook, handler)
            except ValueError:
                pass  # Handler may have already been removed
        await plugin.teardown()
        logger.info("plugin_unregistered", plugin=name)

    def discover(self, group: str = "openclaw_sdk.plugins") -> list[str]:
        """Discover plugins via ``importlib.metadata`` entry points.

        Returns:
            List of discovered entry-point names.
        """
        from importlib.metadata import entry_points

        discovered: list[str] = []
        for ep in entry_points(group=group):
            discovered.append(ep.name)
        return discovered

    def list_plugins(self) -> list[PluginMetadata]:
        """Return metadata for all registered plugins."""
        return [plugin.metadata() for plugin in self._plugins.values()]

    @property
    def hooks(self) -> HookManager:
        """Access the hook manager for dispatching events."""
        return self._hooks

"""Plugin system for extending the SDK."""
from __future__ import annotations

from openclaw_sdk.plugins.base import Plugin, PluginHook, PluginMetadata
from openclaw_sdk.plugins.hooks import HookManager
from openclaw_sdk.plugins.registry import PluginRegistry

__all__ = ["Plugin", "PluginHook", "PluginMetadata", "PluginRegistry", "HookManager"]

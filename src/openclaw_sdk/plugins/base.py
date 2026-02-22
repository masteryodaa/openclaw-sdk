"""Base classes for the SDK plugin system."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PluginHook(StrEnum):
    """Hook points where plugins can intercept SDK operations."""

    PRE_EXECUTE = "pre_execute"
    POST_EXECUTE = "post_execute"
    ON_ERROR = "on_error"
    ON_TOOL_CALL = "on_tool_call"
    ON_TOOL_RESULT = "on_tool_result"
    ON_STREAM = "on_stream"


class PluginMetadata(BaseModel):
    """Metadata describing a plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""


class Plugin(ABC):
    """Base class for SDK plugins.

    Subclass this to create a plugin. Implement :meth:`metadata` to identify
    the plugin and :meth:`hooks` to register hook handlers.

    Optionally override :meth:`setup` / :meth:`teardown` for lifecycle management.
    """

    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return metadata describing this plugin."""
        ...

    @abstractmethod
    def hooks(self) -> dict[PluginHook, Callable[..., Awaitable[Any]]]:
        """Return a mapping of hook points to async handler callables."""
        ...

    async def setup(self) -> None:
        """Called when the plugin is registered. Override for initialisation logic."""

    async def teardown(self) -> None:
        """Called when the plugin is unregistered. Override for cleanup logic."""

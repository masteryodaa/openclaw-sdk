from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Protocol, runtime_checkable

from openclaw_sdk.core.types import HealthStatus, StreamEvent


@runtime_checkable
class GatewayProtocol(Protocol):
    """Structural type for any Gateway implementation.

    All managers accept this Protocol so they work with any backend
    (ProtocolGateway, MockGateway, etc.) without importing concrete classes.
    """

    async def call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    async def subscribe(
        self, event_types: list[str] | None = None
    ) -> AsyncIterator[StreamEvent]: ...


class Gateway(ABC):
    """Abstract base for all Gateway implementations.

    v0.1 implementation note: implement call() and subscribe() first.
    All facade methods are typed wrappers over those two primitives.
    Facade methods should only be added after verifying against protocol-notes.md.
    """

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def health(self) -> HealthStatus: ...

    # ------------------------------------------------------------------ #
    # Protocol primitives
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def subscribe(
        self, event_types: list[str] | None = None
    ) -> AsyncIterator[StreamEvent]: ...

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "Gateway":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

"""Base classes for the SaaS connectors system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ConnectorConfig(BaseModel):
    """Configuration for a SaaS connector.

    Attributes:
        api_key: Primary API key or OAuth access token.
        api_secret: Secondary secret (e.g. for Basic auth password / API secret).
        base_url: Override the default API base URL.
        timeout: HTTP request timeout in seconds.
        extra_headers: Additional headers merged into every request.
    """

    api_key: str | None = None
    api_secret: str | None = None
    base_url: str | None = None
    timeout: float = 30.0
    extra_headers: dict[str, str] = Field(default_factory=dict)


class ConnectorAction(BaseModel):
    """Describes a single action a connector can perform.

    Attributes:
        name: Machine-readable action name (e.g. ``"list_repos"``).
        description: Human-readable description of the action.
        required_params: Parameter names that must be provided.
        optional_params: Parameter names that may be omitted.
    """

    name: str
    description: str = ""
    required_params: list[str] = Field(default_factory=list)
    optional_params: list[str] = Field(default_factory=list)


class Connector(ABC):
    """Abstract base for SaaS connectors.

    All connectors use :mod:`httpx` for real HTTP API calls. Subclasses must
    implement :meth:`_build_headers` and :meth:`list_actions`.

    Usage::

        config = ConnectorConfig(api_key="tok_xxx")
        async with GitHubConnector(config) as gh:
            repos = await gh.list_repos()
    """

    DEFAULT_BASE_URL: str = ""

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def config(self) -> ConnectorConfig:
        """Return the connector configuration."""
        return self._config

    async def connect(self) -> None:
        """Open the underlying HTTP client."""
        base_url = self._config.base_url or self.DEFAULT_BASE_URL
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=self._build_headers(),
            timeout=self._config.timeout,
        )
        logger.info(
            "connector.connected",
            connector=type(self).__name__,
            base_url=base_url,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("connector.closed", connector=type(self).__name__)

    @abstractmethod
    def _build_headers(self) -> dict[str, str]:
        """Build the default headers for every request."""
        ...

    @abstractmethod
    def list_actions(self) -> list[ConnectorAction]:
        """Return the list of actions this connector supports."""
        ...

    def _ensure_connected(self) -> httpx.AsyncClient:
        """Return the HTTP client, raising if not connected."""
        if self._client is None:
            raise RuntimeError(
                f"{type(self).__name__} is not connected. Call connect() first."
            )
        return self._client

    async def __aenter__(self) -> Connector:
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

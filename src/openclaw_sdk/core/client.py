from __future__ import annotations

import socket
from typing import TYPE_CHECKING, Any

from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.channels.manager import ChannelManager
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.exceptions import ConfigurationError
from openclaw_sdk.core.types import HealthStatus
from openclaw_sdk.gateway.base import Gateway
from openclaw_sdk.scheduling.manager import ScheduleManager
from openclaw_sdk.skills.clawhub import ClawHub
from openclaw_sdk.skills.manager import SkillManager

if TYPE_CHECKING:
    from openclaw_sdk.core.agent import Agent
    from openclaw_sdk.pipeline.pipeline import Pipeline


def _openclaw_is_running(host: str = "127.0.0.1", port: int = 18789) -> bool:
    """Return True if an OpenClaw gateway is reachable at the default local port."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


class OpenClawClient:
    """Top-level client for the OpenClaw SDK.

    Create via the :meth:`connect` factory method::

        client = await OpenClawClient.connect()
        agent = client.get_agent("my-agent")
        result = await agent.execute("Summarise the sales report")
        print(result.content)

    Or use as an async context manager::

        async with await OpenClawClient.connect() as client:
            agent = client.get_agent("my-agent")
            result = await agent.execute("hello")
    """

    def __init__(
        self,
        *,
        config: ClientConfig,
        gateway: Gateway,
        callbacks: list[CallbackHandler] | None = None,
    ) -> None:
        self._config = config
        self._gateway = gateway
        self._callbacks: list[CallbackHandler] = list(callbacks or [])

        # Lazy-initialised manager instances
        self._channels: ChannelManager | None = None
        self._scheduling: ScheduleManager | None = None
        self._skills: SkillManager | None = None
        self._clawhub: ClawHub | None = None

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #

    @classmethod
    async def connect(cls, **kwargs: Any) -> "OpenClawClient":
        """Auto-detect and connect to an OpenClaw gateway.

        Auto-detection order:
        1. ``gateway_ws_url`` kwarg / ClientConfig field → :class:`ProtocolGateway`
        2. ``openai_base_url`` kwarg / ClientConfig field → :class:`OpenAICompatGateway`
        3. Local OpenClaw running at ``ws://127.0.0.1:18789`` → :class:`LocalGateway`
        4. Raises :class:`ConfigurationError`.

        Any ``ClientConfig`` field can be passed as a keyword argument.
        The special ``callbacks`` kwarg accepts a list of
        :class:`~openclaw_sdk.callbacks.handler.CallbackHandler` instances.

        Returns:
            A connected :class:`OpenClawClient`.

        Raises:
            ConfigurationError: When no gateway can be found or configured.
            GatewayError: When the connection or auth handshake fails.
        """
        # Separate gateway-config fields from other kwargs
        config_fields = set(ClientConfig.model_fields)
        config_kwargs = {k: v for k, v in kwargs.items() if k in config_fields}
        callbacks: list[CallbackHandler] = kwargs.get("callbacks") or []

        config = ClientConfig(**config_kwargs)
        gateway = cls._build_gateway(config)

        await gateway.connect()
        return cls(config=config, gateway=gateway, callbacks=callbacks)

    @staticmethod
    def _build_gateway(config: ClientConfig) -> Gateway:
        """Select and instantiate the right gateway from *config*."""
        # Deferred imports to break potential circular deps and keep startup cheap.
        if config.gateway_ws_url is not None:
            from openclaw_sdk.gateway.protocol import ProtocolGateway  # noqa: PLC0415

            return ProtocolGateway(config.gateway_ws_url, token=config.api_key)

        if config.openai_base_url is not None:
            from openclaw_sdk.gateway.openai_compat import OpenAICompatGateway  # noqa: PLC0415

            return OpenAICompatGateway(config.openai_base_url, api_key=config.api_key)

        if config.mode == "local" or (config.mode == "auto" and _openclaw_is_running()):
            from openclaw_sdk.gateway.local import LocalGateway  # noqa: PLC0415

            return LocalGateway()

        raise ConfigurationError(
            "No OpenClaw gateway found. "
            "Run 'openclaw start', set gateway_ws_url, or set openai_base_url."
        )

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def config(self) -> ClientConfig:
        return self._config

    @property
    def gateway(self) -> Gateway:
        """The underlying :class:`~openclaw_sdk.gateway.base.Gateway`."""
        return self._gateway

    @property
    def channels(self) -> ChannelManager:
        """Manager for channel operations (WhatsApp, Telegram, …)."""
        if self._channels is None:
            self._channels = ChannelManager(self._gateway)
        return self._channels

    @property
    def scheduling(self) -> ScheduleManager:
        """Manager for scheduled jobs (cron)."""
        if self._scheduling is None:
            self._scheduling = ScheduleManager(self._gateway)
        return self._scheduling

    @property
    def skills(self) -> SkillManager:
        """Manager for installed OpenClaw skills (CLI-backed)."""
        if self._skills is None:
            self._skills = SkillManager()
        return self._skills

    @property
    def clawhub(self) -> ClawHub:
        """Access the ClawHub marketplace (CLI-backed)."""
        if self._clawhub is None:
            self._clawhub = ClawHub()
        return self._clawhub

    # ------------------------------------------------------------------ #
    # Agent & pipeline helpers
    # ------------------------------------------------------------------ #

    def get_agent(self, agent_id: str, session_name: str = "main") -> "Agent":
        """Return an :class:`~openclaw_sdk.core.agent.Agent` for *agent_id*.

        Args:
            agent_id: The agent's identifier (e.g. ``"my-agent"``).
            session_name: The session name within the agent (default ``"main"``).
                The ``session_key`` sent to the gateway is
                ``"{agent_id}:{session_name}"``.
        """
        from openclaw_sdk.core.agent import Agent  # noqa: PLC0415

        return Agent(self, agent_id, session_name)

    def pipeline(self) -> "Pipeline":
        """Return a new :class:`~openclaw_sdk.pipeline.pipeline.Pipeline` for this client."""
        from openclaw_sdk.pipeline.pipeline import Pipeline  # noqa: PLC0415

        return Pipeline(self)

    # ------------------------------------------------------------------ #
    # Health & lifecycle
    # ------------------------------------------------------------------ #

    async def health(self) -> HealthStatus:
        """Delegate to the underlying gateway health check."""
        return await self._gateway.health()

    async def close(self) -> None:
        """Close the gateway connection."""
        await self._gateway.close()

    async def __aenter__(self) -> "OpenClawClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

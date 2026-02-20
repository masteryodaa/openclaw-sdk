from __future__ import annotations

import json
import socket
from typing import TYPE_CHECKING, Any

from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.cache.base import ResponseCache
from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.channels.manager import ChannelManager
from openclaw_sdk.config.manager import ConfigManager
from openclaw_sdk.core.config import AgentConfig, ClientConfig
from openclaw_sdk.core.constants import AgentStatus
from openclaw_sdk.core.exceptions import ConfigurationError
from openclaw_sdk.core.types import AgentSummary, HealthStatus
from openclaw_sdk.gateway.base import Gateway
from openclaw_sdk.devices.manager import DeviceManager
from openclaw_sdk.nodes.manager import NodeManager
from openclaw_sdk.ops.manager import OpsManager
from openclaw_sdk.scheduling.manager import ScheduleManager
from openclaw_sdk.skills.clawhub import ClawHub
from openclaw_sdk.skills.manager import SkillManager
from openclaw_sdk.webhooks.manager import WebhookManager

if TYPE_CHECKING:
    from openclaw_sdk.channels.config import ChannelConfig
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
        cache: ResponseCache | None = None,
    ) -> None:
        self._config = config
        self._gateway = gateway
        self._callbacks: list[CallbackHandler] = list(callbacks or [])
        self._cache = cache

        # Lazy-initialised manager instances
        self._channels: ChannelManager | None = None
        self._scheduling: ScheduleManager | None = None
        self._skills: SkillManager | None = None
        self._clawhub: ClawHub | None = None
        self._webhooks: WebhookManager | None = None
        self._config_mgr: ConfigManager | None = None
        self._approvals: ApprovalManager | None = None
        self._nodes: NodeManager | None = None
        self._ops: OpsManager | None = None
        self._devices: DeviceManager | None = None

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

    @property
    def webhooks(self) -> WebhookManager:
        """Manager for webhook operations (stub — CLI-backed)."""
        if self._webhooks is None:
            self._webhooks = WebhookManager()
        return self._webhooks

    @property
    def schedules(self) -> ScheduleManager:
        """Manager for scheduled jobs (cron) — canonical property name."""
        if self._scheduling is None:
            self._scheduling = ScheduleManager(self._gateway)
        return self._scheduling

    @property
    def config_mgr(self) -> ConfigManager:
        """Manager for OpenClaw runtime configuration (``config.*`` methods)."""
        if self._config_mgr is None:
            self._config_mgr = ConfigManager(self._gateway)
        return self._config_mgr

    @property
    def approvals(self) -> ApprovalManager:
        """Manager for execution approval requests."""
        if self._approvals is None:
            self._approvals = ApprovalManager(self._gateway)
        return self._approvals

    @property
    def nodes(self) -> NodeManager:
        """Manager for node / presence operations."""
        if self._nodes is None:
            self._nodes = NodeManager(self._gateway)
        return self._nodes

    @property
    def ops(self) -> OpsManager:
        """Manager for operational utilities (logs, updates, usage)."""
        if self._ops is None:
            self._ops = OpsManager(self._gateway)
        return self._ops

    @property
    def devices(self) -> DeviceManager:
        """Manager for device token operations (rotate, revoke)."""
        if self._devices is None:
            self._devices = DeviceManager(self._gateway)
        return self._devices

    # ------------------------------------------------------------------ #
    # Agent & pipeline helpers
    # ------------------------------------------------------------------ #

    def get_agent(self, agent_id: str, session_name: str = "main") -> "Agent":
        """Return an :class:`~openclaw_sdk.core.agent.Agent` for *agent_id*.

        This is a lightweight factory — no network call is made.
        Use :meth:`create_agent` to create a new agent on the gateway.

        Args:
            agent_id: The agent's identifier (e.g. ``"my-agent"``).
            session_name: The session name within the agent (default ``"main"``).
                The ``session_key`` sent to the gateway is
                ``"{agent_id}:{session_name}"``.
        """
        from openclaw_sdk.core.agent import Agent  # noqa: PLC0415

        return Agent(self, agent_id, session_name)

    async def create_agent(self, config: AgentConfig) -> "Agent":
        """Create a new agent on the gateway via read-modify-write on config.

        Reads the current config with ``config.get``, merges the new agent
        definition, then writes back with ``config.set``.

        Args:
            config: :class:`~openclaw_sdk.core.config.AgentConfig` for the new agent.

        Returns:
            An :class:`~openclaw_sdk.core.agent.Agent` connected to the new agent.
        """
        from openclaw_sdk.core.agent import Agent  # noqa: PLC0415

        current = await self._gateway.call("config.get", {})
        raw_str = current.get("raw", "{}")
        parsed = json.loads(raw_str) if isinstance(raw_str, str) else {}

        if "agents" not in parsed:
            parsed["agents"] = {}
        agent_data = config.model_dump(exclude_none=True)
        agent_data.pop("agent_id", None)
        parsed["agents"][config.agent_id] = agent_data

        new_raw = json.dumps(parsed, indent=2)
        await self._gateway.call("config.set", {"raw": new_raw})
        return Agent(self, config.agent_id)

    async def list_agents(self) -> list[AgentSummary]:
        """List all agent sessions known to the gateway.

        Gateway method: ``sessions.list``

        Returns:
            List of :class:`~openclaw_sdk.core.types.AgentSummary` objects.
        """
        result = await self._gateway.call("sessions.list", {})
        summaries: list[AgentSummary] = []
        for session in result.get("sessions", []):
            # Session objects use "key" (not "sessionKey") — verified
            key = session.get("key", "")
            # Session key format: "agent:{agent_id}:{session_name}"
            parts = key.split(":", 2)
            agent_id = parts[1] if len(parts) >= 2 else key
            status_str = session.get("status", "idle")
            try:
                status = AgentStatus(status_str)
            except ValueError:
                status = AgentStatus.IDLE
            summaries.append(
                AgentSummary(
                    agent_id=agent_id,
                    name=session.get("name"),
                    status=status,
                )
            )
        return summaries

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent and all its sessions from the gateway.

        Gateway method: ``sessions.delete``
        Verified param: ``{key}``

        Args:
            agent_id: The agent's identifier to delete.

        Returns:
            ``True`` on success.
        """
        await self._gateway.call(
            "sessions.delete",
            {"key": f"agent:{agent_id}:main"},
        )
        return True

    async def configure_channel(self, config: "ChannelConfig") -> dict[str, Any]:
        """Configure a messaging channel on the gateway via read-modify-write.

        Reads the current config with ``config.get``, merges the channel
        definition, then writes back with ``config.set``.

        Args:
            config: A :class:`~openclaw_sdk.channels.config.ChannelConfig` instance.

        Returns:
            Gateway response dict from ``config.set``.
        """
        current = await self._gateway.call("config.get", {})
        raw_str = current.get("raw", "{}")
        parsed = json.loads(raw_str) if isinstance(raw_str, str) else {}

        if "channels" not in parsed:
            parsed["channels"] = {}
        channel_data = config.model_dump(exclude_none=True)
        parsed["channels"][config.channel_type] = channel_data

        new_raw = json.dumps(parsed, indent=2)
        return await self._gateway.call("config.set", {"raw": new_raw})

    async def list_channels(self) -> list[dict[str, Any]]:
        """List all configured channels and their status.

        Gateway method: ``channels.status``

        Returns:
            List of dicts, each representing one channel with its status fields.
        """
        result = await self._gateway.call("channels.status", {})
        channels: dict[str, Any] = result.get("channels", {})
        return [{"name": k, **v} for k, v in channels.items()]

    async def remove_channel(self, channel_name: str) -> bool:
        """Remove / logout a channel from the gateway.

        Gateway method: ``channels.logout``

        Args:
            channel_name: The channel identifier (e.g. ``"whatsapp"``).

        Returns:
            ``True`` on success.
        """
        await self._gateway.call("channels.logout", {"channel": channel_name})
        return True

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

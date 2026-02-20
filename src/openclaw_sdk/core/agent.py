from __future__ import annotations

import asyncio
import base64
import json
import time
import warnings
from typing import TYPE_CHECKING, Any, AsyncIterator, Type, TypeVar

from pydantic import BaseModel

from openclaw_sdk.callbacks.handler import CallbackHandler, CompositeCallbackHandler
from openclaw_sdk.core.config import ExecutionOptions
from openclaw_sdk.core.constants import AgentStatus, EventType
from openclaw_sdk.core.exceptions import AgentExecutionError, OpenClawError
from openclaw_sdk.core.exceptions import TimeoutError as OcTimeoutError
from openclaw_sdk.core.types import ExecutionResult, StreamEvent
from openclaw_sdk.tools.config import ToolConfig

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient
    from openclaw_sdk.mcp.server import HttpMcpServer, StdioMcpServer
    from openclaw_sdk.tools.policy import ToolPolicy

T = TypeVar("T", bound=BaseModel)


class Agent:
    """Represents a single OpenClaw agent and exposes execution methods.

    Obtain via :meth:`~openclaw_sdk.core.client.OpenClawClient.get_agent`::

        agent = client.get_agent("research-bot")
        result = await agent.execute("Summarise recent AI papers")
        print(result.content)

    The *session_key* sent to the gateway is ``"agent:{agent_id}:{session_name}"``.
    """

    def __init__(
        self,
        client: "OpenClawClient",
        agent_id: str,
        session_name: str = "main",
    ) -> None:
        self._client = client
        self.agent_id = agent_id
        self.session_name = session_name

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def session_key(self) -> str:
        """Gateway session key for this agent, e.g. ``"agent:main:main"``."""
        return f"agent:{self.agent_id}:{self.session_name}"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def execute(
        self,
        query: str,
        options: ExecutionOptions | None = None,
        callbacks: list[CallbackHandler] | None = None,
        idempotency_key: str | None = None,
    ) -> ExecutionResult:
        """Send *query* to the agent and return the final result.

        For WebSocket gateways (ProtocolGateway / LocalGateway):
            Subscribes to push events, sends ``chat.send``, then waits for a
            ``DONE`` or ``ERROR`` event.

        For HTTP-only gateways (OpenAICompatGateway):
            Uses the response body from ``chat.send`` directly.

        Args:
            query: The message to send to the agent.
            options: Optional execution controls (timeout, streaming, etc.).
            callbacks: Per-call callbacks; merged with client-level callbacks.
            idempotency_key: Optional idempotency key forwarded to the gateway.

        Returns:
            An :class:`~openclaw_sdk.core.types.ExecutionResult`.

        Raises:
            AgentExecutionError: On agent-level failure or unhandled exception.
            TimeoutError: If the agent does not respond within *timeout*.
        """
        resolved_cbs = CompositeCallbackHandler(
            self._client._callbacks + list(callbacks or [])
        )
        timeout = int(
            (options.timeout_seconds if options else None)
            or self._client.config.timeout
        )

        await resolved_cbs.on_execution_start(self.agent_id, query)
        t0 = time.monotonic()

        try:
            # Check cache before hitting the gateway.
            if self._client._cache is not None:
                cached = await self._client._cache.get(self.agent_id, query)
                if cached is not None:
                    await resolved_cbs.on_execution_end(self.agent_id, cached)
                    return cached

            params: dict[str, Any] = {
                "sessionKey": self.session_key,
                "message": query,
            }
            if idempotency_key is not None:
                params["idempotencyKey"] = idempotency_key

            result = await self._execute_impl(params, timeout, resolved_cbs, t0)

            # Store successful results in cache.
            if self._client._cache is not None and result.success:
                await self._client._cache.set(self.agent_id, query, result)

            await resolved_cbs.on_execution_end(self.agent_id, result)
            return result

        except OpenClawError:
            raise
        except Exception as exc:
            await resolved_cbs.on_error(self.agent_id, exc)
            raise AgentExecutionError(
                f"Agent '{self.agent_id}' execution failed: {exc}"
            ) from exc

    async def execute_stream(
        self,
        query: str,
        options: ExecutionOptions | None = None,
        callbacks: list[CallbackHandler] | None = None,
        idempotency_key: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Send *query* and yield push events until the agent finishes.

        Requires a WebSocket-capable gateway.  Raises :class:`NotImplementedError`
        if the underlying gateway does not support streaming.

        Yields:
            :class:`~openclaw_sdk.core.types.StreamEvent` objects until a
            ``DONE`` or ``ERROR`` event is received.
        """
        params: dict[str, Any] = {
            "sessionKey": self.session_key,
            "message": query,
        }
        if idempotency_key is not None:
            params["idempotencyKey"] = idempotency_key

        subscriber = await self._client.gateway.subscribe()
        await self._client.gateway.call("chat.send", params)

        return self._yield_events(subscriber)

    async def _yield_events(
        self,
        subscriber: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        async for event in subscriber:
            yield event
            if event.event_type in (EventType.DONE, EventType.ERROR):
                break

    async def batch(
        self,
        queries: list[str],
        options: ExecutionOptions | None = None,
        callbacks: list[CallbackHandler] | None = None,
        max_concurrency: int | None = None,
    ) -> list[ExecutionResult]:
        """Execute multiple queries in parallel.

        Args:
            queries: List of query strings to execute.
            options: Shared execution options for all queries.
            callbacks: Shared callbacks for all queries.
            max_concurrency: Max parallel executions (default: unlimited).

        Returns:
            List of ExecutionResult in the same order as queries.
        """
        sem = asyncio.Semaphore(max_concurrency if max_concurrency is not None else len(queries))

        async def _run(query: str) -> ExecutionResult:
            async with sem:
                return await self.execute(query, options=options, callbacks=callbacks)

        return list(await asyncio.gather(*[_run(q) for q in queries]))

    async def execute_structured(
        self,
        query: str,
        output_model: Type[T],
        options: ExecutionOptions | None = None,
        max_retries: int = 2,
    ) -> T:
        """Execute *query* and parse the response into a Pydantic model.

        Delegates to :class:`~openclaw_sdk.output.structured.StructuredOutput`.

        Args:
            query: The user query.
            output_model: The Pydantic model class to validate the response against.
            options: Optional execution controls.
            max_retries: Extra attempts on parse failure (default 2).

        Returns:
            A validated *output_model* instance.
        """
        from openclaw_sdk.output.structured import StructuredOutput  # noqa: PLC0415

        return await StructuredOutput.execute(
            self, query, output_model, max_retries=max_retries
        )

    async def get_file(self, file_path: str) -> bytes:
        """Download a file generated by this agent.

        Gateway method: ``files.get``

        Args:
            file_path: The path returned in a :class:`~openclaw_sdk.core.types.GeneratedFile`.

        Returns:
            Raw file bytes.
        """
        result = await self._client.gateway.call(
            "files.get",
            {"sessionKey": self.session_key, "path": file_path},
        )
        content = result.get("content", "")
        if result.get("encoding") == "base64":
            return base64.b64decode(content)
        return content.encode() if isinstance(content, str) else bytes(content)

    async def configure_tools(self, tools: list[ToolConfig]) -> dict[str, Any]:
        """Configure tools for this agent session.

        Gateway method: ``config.setTools``

        Args:
            tools: List of :class:`~openclaw_sdk.tools.config.ToolConfig` instances.

        Returns:
            Gateway response dict.

        .. deprecated::
            Use :meth:`set_tool_policy` with a :class:`ToolPolicy` instead.
        """
        warnings.warn(
            "configure_tools() is deprecated. Use set_tool_policy(ToolPolicy(...)) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        params: dict[str, Any] = {
            "sessionKey": self.session_key,
            "tools": [t.model_dump() for t in tools],
        }
        return await self._client.gateway.call("config.setTools", params)

    async def reset_memory(self) -> bool:
        """Clear this agent's conversation memory.

        Gateway method: ``sessions.reset``
        Verified param: ``{key}``

        Returns:
            ``True`` on success.
        """
        await self._client.gateway.call(
            "sessions.reset",
            {"key": self.session_key},
        )
        return True

    async def get_memory_status(self) -> dict[str, Any]:
        """Return memory / session state for this agent.

        Gateway method: ``sessions.preview``
        Verified param: ``{keys: [key]}``

        Returns:
            Gateway response dict with session preview.
        """
        return await self._client.gateway.call(
            "sessions.preview",
            {"keys": [self.session_key]},
        )

    async def get_status(self) -> AgentStatus:
        """Return the current :class:`~openclaw_sdk.core.constants.AgentStatus`.

        Gateway method: ``sessions.resolve``
        Verified param: ``{key}``

        Returns:
            An :class:`~openclaw_sdk.core.constants.AgentStatus` enum value.
        """
        result = await self._client.gateway.call(
            "sessions.resolve",
            {"key": self.session_key},
        )
        status_str = result.get("status", "idle")
        try:
            return AgentStatus(status_str)
        except ValueError:
            return AgentStatus.IDLE

    async def wait_for_run(self, run_id: str) -> dict[str, Any]:
        """Wait for a specific run to complete.

        Gateway method: ``agent.wait``

        Args:
            run_id: The run ID from a ``chat.send`` response.

        Returns:
            Gateway response dict with run result.
        """
        return await self._client.gateway.call("agent.wait", {"runId": run_id})

    async def set_tool_policy(self, policy: "ToolPolicy") -> dict[str, Any]:
        """Set the tool policy for this agent at runtime via ``config.patch``.

        Args:
            policy: The :class:`~openclaw_sdk.tools.policy.ToolPolicy` to apply.

        Returns:
            Gateway response dict.
        """
        return await self._patch_agent_config({"tools": policy.to_openclaw()})

    async def deny_tools(self, *tools: str) -> dict[str, Any]:
        """Add tools to this agent's deny list at runtime.

        Args:
            *tools: Tool names to deny (e.g. ``"browser"``, ``"group:runtime"``).

        Returns:
            Gateway response dict.
        """
        current = await self._get_agent_tools_config()
        deny_list = sorted(set(current.get("deny", [])) | set(tools))
        return await self._patch_agent_config({"tools": {**current, "deny": deny_list}})

    async def allow_tools(self, *tools: str) -> dict[str, Any]:
        """Add tools to this agent's ``alsoAllow`` list at runtime.

        Args:
            *tools: Tool names to additionally allow.

        Returns:
            Gateway response dict.
        """
        current = await self._get_agent_tools_config()
        also = sorted(set(current.get("alsoAllow", [])) | set(tools))
        return await self._patch_agent_config({"tools": {**current, "alsoAllow": also}})

    async def add_mcp_server(
        self,
        name: str,
        server: "StdioMcpServer | HttpMcpServer",
    ) -> dict[str, Any]:
        """Add or replace an MCP server in this agent's config.

        Args:
            name: Server name (e.g. ``"postgres"``).
            server: Server config from :class:`~openclaw_sdk.mcp.server.McpServer`.

        Returns:
            Gateway response dict.
        """
        current_servers = await self._get_agent_mcp_config()
        current_servers[name] = server.to_openclaw()
        return await self._patch_agent_config({"mcpServers": current_servers})

    async def remove_mcp_server(self, name: str) -> dict[str, Any]:
        """Remove an MCP server from this agent's config.

        Args:
            name: Server name to remove.

        Returns:
            Gateway response dict.
        """
        current_servers = await self._get_agent_mcp_config()
        current_servers.pop(name, None)
        return await self._patch_agent_config({"mcpServers": current_servers})

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _get_full_config(self) -> tuple[dict[str, Any], str | None]:
        """Read current OpenClaw config, return (parsed_dict, base_hash)."""
        result = await self._client.gateway.call("config.get", {})
        raw_str = result.get("raw", "{}")
        parsed = json.loads(raw_str) if isinstance(raw_str, str) else {}
        return parsed, result.get("hash")

    async def _get_agent_tools_config(self) -> dict[str, Any]:
        """Read this agent's current tools config section."""
        parsed, _ = await self._get_full_config()
        agent = parsed.get("agents", {}).get(self.agent_id, {})
        tools = agent.get("tools", {})
        return tools if isinstance(tools, dict) else {}

    async def _get_agent_mcp_config(self) -> dict[str, Any]:
        """Read this agent's current mcpServers config."""
        parsed, _ = await self._get_full_config()
        agent: dict[str, Any] = parsed.get("agents", {}).get(self.agent_id, {})
        mcp: dict[str, Any] = agent.get("mcpServers", {})
        return mcp

    async def _patch_agent_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Read-modify-write this agent's config via ``config.patch``."""
        parsed, base_hash = await self._get_full_config()
        if "agents" not in parsed:
            parsed["agents"] = {}
        if self.agent_id not in parsed["agents"]:
            parsed["agents"][self.agent_id] = {}
        parsed["agents"][self.agent_id].update(updates)

        params: dict[str, Any] = {"raw": json.dumps(parsed, indent=2)}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self._client.gateway.call("config.patch", params)

    async def _execute_impl(
        self,
        params: dict[str, Any],
        timeout: int,
        cb: CompositeCallbackHandler,
        t0: float,
    ) -> ExecutionResult:
        """Core execution — handles both WS and HTTP-only gateways."""
        # Try to subscribe before sending so we don't miss events.
        try:
            subscriber: AsyncIterator[StreamEvent] | None = (
                await self._client.gateway.subscribe()
            )
            has_stream = True
        except NotImplementedError:
            subscriber = None
            has_stream = False

        send_result = await self._client.gateway.call("chat.send", params)

        if not has_stream or subscriber is None:
            # HTTP-only path: result comes back in the send response.
            content = (
                send_result.get("content")
                or send_result.get("text")
                or send_result.get("message")
                or ""
            )
            return ExecutionResult(
                success=True,
                content=content,
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

        # WebSocket path: collect events until DONE / ERROR.
        run_id: str = send_result.get("runId", "")
        content_parts: list[str] = []

        try:
            async with asyncio.timeout(timeout):
                async for event in subscriber:
                    payload: dict[str, Any] = event.data.get("payload") or {}
                    event_run_id: str = payload.get("runId", "")

                    # Skip events that belong to a different run.
                    if run_id and event_run_id and event_run_id != run_id:
                        continue

                    if event.event_type == EventType.CONTENT:
                        chunk = payload.get("content") or payload.get("text") or ""
                        content_parts.append(chunk)
                        await cb.on_stream_event(self.agent_id, event)

                    elif event.event_type == EventType.DONE:
                        final = payload.get("content") or payload.get("text") or ""
                        if final:
                            content_parts.append(final)
                        break

                    elif event.event_type == EventType.ERROR:
                        error_msg = (
                            payload.get("message")
                            or payload.get("error")
                            or "Agent reported an error"
                        )
                        raise AgentExecutionError(
                            f"Agent '{self.agent_id}': {error_msg}"
                        )

        except asyncio.TimeoutError as exc:
            raise OcTimeoutError(
                f"Agent '{self.agent_id}' timed out after {timeout}s"
            ) from exc

        return ExecutionResult(
            success=True,
            content="".join(content_parts),
            latency_ms=int((time.monotonic() - t0) * 1000),
        )

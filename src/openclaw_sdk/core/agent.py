from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Type, TypeVar

from pydantic import BaseModel

from openclaw_sdk.callbacks.handler import CallbackHandler, CompositeCallbackHandler
from openclaw_sdk.core.config import ExecutionOptions
from openclaw_sdk.core.constants import AgentStatus, EventType
from openclaw_sdk.core.exceptions import AgentExecutionError, OpenClawError
from openclaw_sdk.core.exceptions import TimeoutError as OcTimeoutError
from openclaw_sdk.core.types import (
    Attachment,
    ContentBlock,
    ContentEvent,
    DoneEvent,
    ErrorEvent,
    ExecutionResult,
    FileEvent,
    GeneratedFile,
    StreamEvent,
    ThinkingEvent,
    TokenUsage,
    ToolCall,
    ToolCallEvent,
    ToolResultEvent,
    TypedStreamEvent,
)

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient
    from openclaw_sdk.core.conversation import Conversation
    from openclaw_sdk.mcp.server import HttpMcpServer, StdioMcpServer
    from openclaw_sdk.skills.config import SkillEntry, SkillsConfig
    from openclaw_sdk.tools.policy import ToolPolicy

T = TypeVar("T", bound=BaseModel)


def _parse_content(raw: Any) -> tuple[str, list[ContentBlock], list[str]]:
    """Parse gateway content -- plain string or array of content blocks.

    Returns:
        (flat_text, content_blocks, thinking_parts)
    """
    if isinstance(raw, str):
        return raw, [], []
    if isinstance(raw, list):
        text_parts: list[str] = []
        thinking_parts: list[str] = []
        blocks: list[ContentBlock] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            block = ContentBlock(
                type=item.get("type", "text"),
                text=item.get("text"),
                thinking=item.get("thinking"),
            )
            blocks.append(block)
            if block.type == "thinking" and block.thinking:
                thinking_parts.append(block.thinking)
            elif block.text:
                text_parts.append(block.text)
        return "".join(text_parts), blocks, thinking_parts
    return str(raw) if raw else "", [], []


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

    def __repr__(self) -> str:
        return f"Agent(agent_id={self.agent_id!r}, session={self.session_name!r})"

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def session_key(self) -> str:
        """Gateway session key for this agent, e.g. ``"agent:main:main"``."""
        return f"agent:{self.agent_id}:{self.session_name}"

    def conversation(self, session_name: str = "main") -> Conversation:
        """Create a multi-turn :class:`Conversation` helper for this agent.

        Args:
            session_name: Session name for the conversation (default ``"main"``).

        Returns:
            A :class:`~openclaw_sdk.core.conversation.Conversation` instance.

        Usage::

            async with agent.conversation("session-1") as convo:
                r1 = await convo.say("Hello")
                r2 = await convo.say("Follow-up")
                print(convo.turns)  # 2
        """
        from openclaw_sdk.core.conversation import Conversation as _Conv  # noqa: PLC0415

        return _Conv(self, session_name)

    # ------------------------------------------------------------------ #
    # Params builder (shared by execute / execute_stream)
    # ------------------------------------------------------------------ #

    def _build_send_params(
        self,
        query: str,
        options: ExecutionOptions | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Build the ``chat.send`` params dict from query + options."""
        params: dict[str, Any] = {
            "sessionKey": self.session_key,
            "message": query,
            "idempotencyKey": idempotency_key or uuid.uuid4().hex,
        }

        if options and options.attachments:
            gateway_attachments: list[dict[str, Any]] = []
            for att in options.attachments:
                if isinstance(att, (str, Path)):
                    att = Attachment.from_path(att)
                gateway_attachments.append(att.to_gateway())
            params["attachments"] = gateway_attachments

        if options:
            if options.thinking:
                # Gateway expects a string: "enabled", "disabled", "auto", or budget
                if isinstance(options.thinking, str):
                    params["thinking"] = options.thinking
                else:
                    params["thinking"] = "enabled"
            if options.deliver is not None:
                params["deliver"] = options.deliver
            params["timeoutMs"] = options.timeout_seconds * 1000

        return params

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

            params = self._build_send_params(query, options, idempotency_key)

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
        params = self._build_send_params(query, options, idempotency_key)

        _EXEC_EVENTS = ["agent", "chat", "content", "done", "error", "thinking",
                        "tool_call", "tool_result", "file_generated"]
        subscriber = await self._client.gateway.subscribe(event_types=_EXEC_EVENTS)
        await self._client.gateway.call("chat.send", params)

        return self._yield_events(subscriber)

    async def _yield_events(
        self,
        subscriber: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        async for event in subscriber:
            yield event
            # Break on terminal events (both mock and real gateway)
            if event.event_type in (EventType.DONE, EventType.ERROR):
                break
            if event.event_type == EventType.CHAT:
                payload = event.data.get("payload") or {}
                if payload.get("state") in ("final", "error", "aborted"):
                    break
            if event.event_type == EventType.AGENT:
                payload = event.data.get("payload") or {}
                stream = payload.get("stream", "")
                data = payload.get("data") or {}
                if stream == "lifecycle" and data.get("phase") == "end":
                    break
                if stream == "lifecycle" and data.get("phase") == "error":
                    break

    async def stream_events(
        self,
        query: str,
        *,
        event_types: list[str] | None = None,
        options: ExecutionOptions | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Yield filtered stream events from an agent execution.

        Subscribes to gateway push events, sends ``chat.send``, and yields
        :class:`~openclaw_sdk.core.types.StreamEvent` objects filtered by
        the requested *event_types*.

        Unlike :meth:`execute_stream` which yields all execution events and
        stops at ``DONE``/``ERROR``, this method lets callers select only
        specific event types (e.g. ``["content", "tool_call"]``) for typed
        processing.

        Args:
            query: The message to send to the agent.
            event_types: Optional list of event type strings to include.
                If ``None``, all events are yielded.  Event types correspond
                to :class:`~openclaw_sdk.core.constants.EventType` values
                (e.g. ``"content"``, ``"tool_call"``, ``"done"``).
            options: Optional execution controls (timeout, attachments, etc.).

        Yields:
            :class:`~openclaw_sdk.core.types.StreamEvent` objects matching
            the requested event types, until a terminal event (``DONE`` or
            ``ERROR``) is received.
        """
        params = self._build_send_params(query, options, None)

        # Subscribe to all execution events so we can detect terminal ones
        # regardless of the user-requested filter.
        _EXEC_EVENTS = [
            "agent", "chat", "content", "done", "error", "thinking",
            "tool_call", "tool_result", "file_generated",
        ]
        subscriber = await self._client.gateway.subscribe(event_types=_EXEC_EVENTS)
        await self._client.gateway.call("chat.send", params)

        async for event in subscriber:
            # Always break on terminal events.
            is_terminal = event.event_type in (EventType.DONE, EventType.ERROR)
            if event.event_type == EventType.CHAT:
                payload = event.data.get("payload") or {}
                if payload.get("state") in ("final", "error", "aborted"):
                    is_terminal = True

            # Yield only if the event matches the requested filter.
            if event_types is None or event.event_type in event_types:
                yield event

            if is_terminal:
                break

    async def execute_stream_typed(
        self,
        query: str,
        options: ExecutionOptions | None = None,
        idempotency_key: str | None = None,
    ) -> AsyncIterator[TypedStreamEvent]:
        """Send *query* and yield strongly-typed events until completion.

        Instead of raw :class:`StreamEvent` with untyped ``data`` dicts,
        this method yields concrete subclasses of :class:`TypedStreamEvent`:

        - :class:`ContentEvent` — text chunks
        - :class:`ThinkingEvent` — reasoning chunks
        - :class:`ToolCallEvent` — tool invocation
        - :class:`ToolResultEvent` — tool output
        - :class:`FileEvent` — generated files
        - :class:`DoneEvent` — execution complete (terminal)
        - :class:`ErrorEvent` — execution error (terminal)

        Handles both real gateway events (``EventType.AGENT`` / ``EventType.CHAT``)
        and MockGateway SDK-level events (``CONTENT``, ``DONE``, etc.) for
        backward compatibility.

        Example::

            async for event in agent.execute_stream_typed("Hello"):
                if isinstance(event, ContentEvent):
                    print(event.text, end="")
                elif isinstance(event, DoneEvent):
                    print(f"\\nDone: {event.stop_reason}")

        Yields:
            :class:`TypedStreamEvent` subclass instances.
        """
        params = self._build_send_params(query, options, idempotency_key)

        _EXEC_EVENTS = [
            "agent", "chat", "content", "done", "error", "thinking",
            "tool_call", "tool_result", "file_generated",
        ]
        subscriber = await self._client.gateway.subscribe(event_types=_EXEC_EVENTS)
        await self._client.gateway.call("chat.send", params)

        _pending_tool_name: str | None = None

        async for event in subscriber:
            payload = event.data.get("payload") or event.data

            # ---- Real gateway: "agent" events (stream deltas) ----

            if event.event_type == EventType.AGENT:
                stream = payload.get("stream", "")
                data = payload.get("data") or {}

                if stream == "assistant":
                    delta = data.get("delta") or data.get("text") or ""
                    if delta:
                        yield ContentEvent(text=delta)

                elif stream == "thinking":
                    chunk = data.get("text") or data.get("delta") or ""
                    if chunk:
                        yield ThinkingEvent(thinking=chunk)

                elif stream == "tool":
                    phase = data.get("phase", "")
                    if phase == "call":
                        tool_name = data.get("tool") or data.get("name") or ""
                        tool_input = data.get("input") or ""
                        if isinstance(tool_input, dict):
                            tool_input = json.dumps(tool_input)
                        _pending_tool_name = tool_name
                        yield ToolCallEvent(tool=tool_name, input=tool_input)
                    elif phase == "result":
                        tool_output = data.get("output") or data.get("result") or ""
                        if isinstance(tool_output, dict):
                            tool_output = json.dumps(tool_output)
                        yield ToolResultEvent(
                            tool=_pending_tool_name or "",
                            output=tool_output,
                            duration_ms=data.get("durationMs", 0),
                        )
                        _pending_tool_name = None

                elif stream == "file":
                    yield FileEvent(
                        name=data.get("name") or data.get("fileName") or "",
                        path=data.get("path") or "",
                        size_bytes=data.get("sizeBytes") or data.get("size") or 0,
                        mime_type=(
                            data.get("mimeType")
                            or data.get("mime_type")
                            or "application/octet-stream"
                        ),
                    )

                elif stream == "lifecycle":
                    phase = data.get("phase", "")
                    if phase == "error":
                        error_msg = data.get("error") or "Agent execution error"
                        yield ErrorEvent(message=error_msg)
                        break

            # ---- Real gateway: "chat" events (state transitions) ----

            elif event.event_type == EventType.CHAT:
                state = payload.get("state", "")

                if state == "delta":
                    # Content comes via "agent" stream events; skip chat deltas
                    # to avoid duplicating text.
                    continue

                elif state == "final":
                    msg = payload.get("message") or {}
                    raw_content = msg.get("content") or ""
                    text, _blocks, _thinking = _parse_content(raw_content)

                    # Token usage from message metadata
                    usage_data = (
                        msg.get("usage")
                        or msg.get("tokenUsage")
                        or payload.get("usage")
                        or {}
                    )
                    token_usage = (
                        TokenUsage.from_gateway(usage_data) if usage_data else TokenUsage()
                    )

                    stop_reason = (
                        msg.get("stopReason")
                        or payload.get("stopReason")
                        or "complete"
                    )
                    yield DoneEvent(
                        content=text,
                        token_usage=token_usage,
                        stop_reason=stop_reason,
                    )
                    break

                elif state == "error":
                    msg = payload.get("message") or {}
                    error_msg = (
                        msg.get("error")
                        or payload.get("error")
                        or "Agent reported an error"
                    )
                    yield ErrorEvent(message=error_msg)
                    break

                elif state == "aborted":
                    yield DoneEvent(content="", stop_reason="aborted")
                    break

            # ---- MockGateway / SDK-level event types (backward compat) ----

            elif event.event_type == EventType.CONTENT:
                text = payload.get("content") or payload.get("text") or ""
                yield ContentEvent(text=text)

            elif event.event_type == EventType.THINKING:
                thinking = payload.get("thinking") or payload.get("content") or ""
                yield ThinkingEvent(thinking=thinking)

            elif event.event_type == EventType.TOOL_CALL:
                tool_name = payload.get("tool") or payload.get("name") or ""
                tool_input = payload.get("input") or ""
                if isinstance(tool_input, dict):
                    tool_input = json.dumps(tool_input)
                _pending_tool_name = tool_name
                yield ToolCallEvent(tool=tool_name, input=tool_input)

            elif event.event_type == EventType.TOOL_RESULT:
                tool_output = payload.get("output") or payload.get("result") or ""
                if isinstance(tool_output, dict):
                    tool_output = json.dumps(tool_output)
                yield ToolResultEvent(
                    tool=_pending_tool_name or "",
                    output=tool_output,
                    duration_ms=payload.get("durationMs", 0),
                )
                _pending_tool_name = None

            elif event.event_type == EventType.FILE_GENERATED:
                yield FileEvent(
                    name=payload.get("name") or payload.get("fileName") or "",
                    path=payload.get("path") or "",
                    size_bytes=payload.get("sizeBytes") or payload.get("size") or 0,
                    mime_type=payload.get("mimeType") or "application/octet-stream",
                )

            elif event.event_type == EventType.DONE:
                content = payload.get("content") or payload.get("text") or ""
                usage_data = payload.get("usage") or payload.get("tokenUsage") or {}
                token_usage = TokenUsage.from_gateway(usage_data) if usage_data else TokenUsage()
                yield DoneEvent(
                    content=content if isinstance(content, str) else "",
                    token_usage=token_usage,
                    stop_reason=payload.get("stopReason") or "complete",
                )
                break

            elif event.event_type == EventType.ERROR:
                msg = payload.get("message") or payload.get("error") or "Unknown error"
                yield ErrorEvent(message=msg)
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

        .. warning::
            **Not available on OpenClaw gateway 2026.2.3-1 and earlier.**
            The ``files.get`` RPC method is not implemented by the current OpenClaw
            gateway and raises ``GatewayError: unknown method: files.get``.

            As a workaround for co-located deployments (SDK and gateway on the same
            machine), read the file directly from the agent's workspace directory:
            ``~/.openclaw/workspace/<path>``

            Remote file access is a planned gateway feature. Track progress at
            https://github.com/openclaw/openclaw/issues.

        Args:
            file_path: The path returned in a :class:`~openclaw_sdk.core.types.GeneratedFile`.

        Returns:
            Raw file bytes.

        Raises:
            GatewayError: Always raises on OpenClaw ≤ 2026.2.3-1 because
                ``files.get`` is not a recognised gateway method.
        """
        result = await self._client.gateway.call(
            "files.get",
            {"sessionKey": self.session_key, "path": file_path},
        )
        content = result.get("content", "")
        if result.get("encoding") == "base64":
            return base64.b64decode(content)
        return content.encode() if isinstance(content, str) else bytes(content)

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

    async def set_skills(self, skills: "SkillsConfig") -> dict[str, Any]:
        """Set the skills configuration for this agent at runtime.

        Controls which bundled skills are available (including ClawHub for
        dynamic discovery), filesystem loading, and per-skill overrides.

        Args:
            skills: The :class:`~openclaw_sdk.skills.config.SkillsConfig` to apply.

        Returns:
            Gateway response dict.
        """
        return await self._patch_agent_config({"skills": skills.to_openclaw()})

    async def configure_skill(
        self, name: str, entry: "SkillEntry"
    ) -> dict[str, Any]:
        """Add or update a single skill's configuration at runtime.

        Args:
            name: Skill name (e.g. ``"web-scraper"``).
            entry: Per-skill config from :class:`~openclaw_sdk.skills.config.SkillEntry`.

        Returns:
            Gateway response dict.
        """
        current = await self._get_agent_skills_config()
        entries = current.get("entries", {})
        entries[name] = entry.to_openclaw()
        current["entries"] = entries
        return await self._patch_agent_config({"skills": current})

    async def disable_skill(self, name: str) -> dict[str, Any]:
        """Disable a specific skill at runtime.

        Args:
            name: Skill name to disable.

        Returns:
            Gateway response dict.
        """
        current = await self._get_agent_skills_config()
        entries = current.get("entries", {})
        entries.setdefault(name, {})["enabled"] = False
        current["entries"] = entries
        return await self._patch_agent_config({"skills": current})

    async def enable_skill(self, name: str) -> dict[str, Any]:
        """Enable a previously disabled skill at runtime.

        Args:
            name: Skill name to enable.

        Returns:
            Gateway response dict.
        """
        current = await self._get_agent_skills_config()
        entries = current.get("entries", {})
        entries.setdefault(name, {})["enabled"] = True
        current["entries"] = entries
        return await self._patch_agent_config({"skills": current})

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

    async def _get_agent_skills_config(self) -> dict[str, Any]:
        """Read this agent's current skills config section."""
        parsed, _ = await self._get_full_config()
        agent: dict[str, Any] = parsed.get("agents", {}).get(self.agent_id, {})
        skills: dict[str, Any] = agent.get("skills", {})
        return skills

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
        # Filter for agent/chat events + SDK-level events (for MockGateway compat).
        _EXEC_EVENTS = ["agent", "chat", "content", "done", "error", "thinking",
                        "tool_call", "tool_result", "file_generated"]
        try:
            subscriber: AsyncIterator[StreamEvent] | None = (
                await self._client.gateway.subscribe(event_types=_EXEC_EVENTS)
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

        # WebSocket path: collect events until DONE / ERROR / aborted.
        run_id: str = send_result.get("runId", "")
        content_parts: list[str] = []
        thinking_parts: list[str] = []
        content_blocks: list[ContentBlock] = []
        tool_calls: list[ToolCall] = []
        files: list[GeneratedFile] = []
        token_usage = TokenUsage()
        stop_reason: str | None = None
        error_message: str | None = None
        success = True

        # Track pending tool call for pairing TOOL_CALL → TOOL_RESULT.
        _pending_tool: dict[str, Any] | None = None

        try:
            async with asyncio.timeout(timeout):
                async for event in subscriber:
                    payload: dict[str, Any] = event.data.get("payload") or {}
                    event_run_id: str = payload.get("runId", "")

                    # Skip events that belong to a different run.
                    if run_id and event_run_id and event_run_id != run_id:
                        continue

                    # ---- Real gateway events: "chat" and "agent" ----

                    if event.event_type == EventType.CHAT:
                        state = payload.get("state", "")
                        msg = payload.get("message") or {}
                        raw_content = msg.get("content") or ""

                        if state == "delta":
                            # Skip — content is streamed via "agent" events.
                            # Using chat deltas too would duplicate every chunk.
                            await cb.on_stream_event(self.agent_id, event)

                        elif state == "final":
                            # Detect empty final: gateway sends state=final
                            # with no "message" field when the LLM fails
                            # (e.g. 429 rate-limit, auth error).  The error
                            # details are stored in OpenClaw's session log
                            # but not pushed through the gateway.
                            if "message" not in payload and not content_parts:
                                stop_reason = "error"
                                error_message = (
                                    "Agent completed with no response — "
                                    "the LLM may be rate-limited or "
                                    "unavailable (check OpenClaw logs)"
                                )
                                success = False
                                break

                            # Final message — extract full content
                            text, blocks, thinking = _parse_content(raw_content)
                            # Replace accumulated deltas with the final text
                            content_parts.clear()
                            if text:
                                content_parts.append(text)
                            if blocks:
                                content_blocks = blocks
                            thinking_parts.extend(thinking)

                            # Token usage from message metadata
                            usage_data = (
                                msg.get("usage")
                                or msg.get("tokenUsage")
                                or payload.get("usage")
                                or {}
                            )
                            if usage_data:
                                token_usage = TokenUsage.from_gateway(usage_data)

                            stop_reason = (
                                msg.get("stopReason")
                                or payload.get("stopReason")
                                or "complete"
                            )
                            await cb.on_stream_event(self.agent_id, event)
                            break

                        elif state == "error":
                            error_msg = (
                                msg.get("error")
                                or payload.get("error")
                                or "Agent reported an error"
                            )
                            raise AgentExecutionError(
                                f"Agent '{self.agent_id}': {error_msg}"
                            )

                        elif state == "aborted":
                            stop_reason = "aborted"
                            success = False
                            break

                    elif event.event_type == EventType.AGENT:
                        stream = payload.get("stream", "")
                        data = payload.get("data") or {}

                        if stream == "assistant":
                            # Streaming text delta from agent
                            delta = data.get("delta") or data.get("text") or ""
                            if delta:
                                content_parts.append(delta)
                            await cb.on_stream_event(self.agent_id, event)

                        elif stream == "thinking":
                            thinking_chunk = data.get("text") or data.get("delta") or ""
                            if thinking_chunk:
                                thinking_parts.append(thinking_chunk)
                            await cb.on_stream_event(self.agent_id, event)

                        elif stream == "tool":
                            phase = data.get("phase", "")
                            if phase == "call":
                                tool_name = data.get("tool") or data.get("name") or ""
                                tool_input = data.get("input") or ""
                                if isinstance(tool_input, dict):
                                    tool_input = json.dumps(tool_input)
                                _pending_tool = {
                                    "tool": tool_name,
                                    "input": tool_input,
                                    "t0": time.monotonic(),
                                }
                                await cb.on_tool_call(self.agent_id, tool_name, tool_input)
                            elif phase == "result":
                                tool_output = data.get("output") or data.get("result") or ""
                                if isinstance(tool_output, dict):
                                    tool_output = json.dumps(tool_output)
                                if _pending_tool is not None:
                                    duration = int(
                                        (time.monotonic() - _pending_tool["t0"]) * 1000
                                    )
                                    tool_calls.append(
                                        ToolCall(
                                            tool=_pending_tool["tool"],
                                            input=_pending_tool["input"],
                                            output=tool_output,
                                            duration_ms=duration,
                                        )
                                    )
                                    await cb.on_tool_result(
                                        self.agent_id,
                                        _pending_tool["tool"],
                                        tool_output,
                                        duration,
                                    )
                                    _pending_tool = None
                            await cb.on_stream_event(self.agent_id, event)

                        elif stream == "file":
                            gf = GeneratedFile(
                                name=data.get("name") or data.get("fileName") or "",
                                path=data.get("path") or "",
                                size_bytes=data.get("sizeBytes") or data.get("size") or 0,
                                mime_type=(
                                    data.get("mimeType")
                                    or data.get("mime_type")
                                    or "application/octet-stream"
                                ),
                            )
                            files.append(gf)
                            await cb.on_file_generated(self.agent_id, gf)
                            await cb.on_stream_event(self.agent_id, event)

                        elif stream == "lifecycle":
                            phase = data.get("phase", "")
                            if phase == "error":
                                error_msg = data.get("error") or "Agent execution error"
                                raise AgentExecutionError(
                                    f"Agent '{self.agent_id}': {error_msg}"
                                )
                            # phase == "end" is handled by the "chat" final event

                    # ---- Mock / SDK-level event types (backward compat) ----

                    elif event.event_type == EventType.CONTENT:
                        raw_content = payload.get("content") or payload.get("text") or ""
                        text, blocks, thinking = _parse_content(raw_content)
                        if text:
                            content_parts.append(text)
                        content_blocks.extend(blocks)
                        thinking_parts.extend(thinking)
                        await cb.on_stream_event(self.agent_id, event)

                    elif event.event_type == EventType.THINKING:
                        thinking_chunk = (
                            payload.get("thinking")
                            or payload.get("content")
                            or ""
                        )
                        thinking_parts.append(thinking_chunk)
                        await cb.on_stream_event(self.agent_id, event)

                    elif event.event_type == EventType.TOOL_CALL:
                        tool_name = payload.get("tool") or payload.get("name") or ""
                        tool_input = payload.get("input") or ""
                        if isinstance(tool_input, dict):
                            tool_input = json.dumps(tool_input)
                        _pending_tool = {
                            "tool": tool_name,
                            "input": tool_input,
                            "t0": time.monotonic(),
                        }
                        await cb.on_tool_call(self.agent_id, tool_name, tool_input)
                        await cb.on_stream_event(self.agent_id, event)

                    elif event.event_type == EventType.TOOL_RESULT:
                        tool_output = payload.get("output") or payload.get("result") or ""
                        if isinstance(tool_output, dict):
                            tool_output = json.dumps(tool_output)
                        if _pending_tool is not None:
                            duration = int(
                                (time.monotonic() - _pending_tool["t0"]) * 1000
                            )
                            tool_calls.append(
                                ToolCall(
                                    tool=_pending_tool["tool"],
                                    input=_pending_tool["input"],
                                    output=tool_output,
                                    duration_ms=duration,
                                )
                            )
                            await cb.on_tool_result(
                                self.agent_id,
                                _pending_tool["tool"],
                                tool_output,
                                duration,
                            )
                            _pending_tool = None
                        await cb.on_stream_event(self.agent_id, event)

                    elif event.event_type == EventType.FILE_GENERATED:
                        gf = GeneratedFile(
                            name=payload.get("name") or payload.get("fileName") or "",
                            path=payload.get("path") or "",
                            size_bytes=payload.get("sizeBytes") or payload.get("size") or 0,
                            mime_type=(
                                payload.get("mimeType")
                                or payload.get("mime_type")
                                or "application/octet-stream"
                            ),
                        )
                        files.append(gf)
                        await cb.on_file_generated(self.agent_id, gf)
                        await cb.on_stream_event(self.agent_id, event)

                    elif event.event_type == EventType.DONE:
                        raw_final = payload.get("content") or payload.get("text") or ""
                        text, blocks, thinking = _parse_content(raw_final)
                        if text:
                            content_parts.append(text)
                        content_blocks.extend(blocks)
                        thinking_parts.extend(thinking)
                        usage_data = (
                            payload.get("usage")
                            or payload.get("tokenUsage")
                            or {}
                        )
                        if usage_data:
                            token_usage = TokenUsage.from_gateway(usage_data)
                        state = payload.get("state") or payload.get("status") or ""
                        if state == "aborted":
                            stop_reason = "aborted"
                            success = False
                        else:
                            stop_reason = payload.get("stopReason") or "complete"
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
            success=success,
            content="".join(content_parts),
            content_blocks=content_blocks,
            thinking="".join(thinking_parts) or None,
            tool_calls=tool_calls,
            files=files,
            token_usage=token_usage,
            stop_reason=stop_reason,
            error_message=error_message,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )

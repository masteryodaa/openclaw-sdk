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
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
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
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def subscribe(
        self, event_types: list[str] | None = None
    ) -> AsyncIterator[StreamEvent]: ...

    # ------------------------------------------------------------------ #
    # Chat facade
    # ------------------------------------------------------------------ #

    async def chat_history(
        self, session_key: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch conversation history for a session.

        Gateway method: ``chat.history``
        """
        result = await self.call(
            "chat.history", {"sessionKey": session_key, "limit": limit}
        )
        messages: list[dict[str, Any]] = result.get("messages", [])
        return messages

    async def chat_abort(self, session_key: str) -> dict[str, Any]:
        """Abort the current run in a session.

        Gateway method: ``chat.abort``
        Verified param: ``{sessionKey}``
        """
        return await self.call("chat.abort", {"sessionKey": session_key})

    async def chat_inject(
        self, session_key: str, message: str
    ) -> dict[str, Any]:
        """Inject a synthetic message into the conversation history.

        Gateway method: ``chat.inject``
        Verified params: ``{sessionKey, message}``
        """
        return await self.call(
            "chat.inject",
            {"sessionKey": session_key, "message": message},
        )

    # ------------------------------------------------------------------ #
    # Agent run facade
    # ------------------------------------------------------------------ #

    async def agent_wait(
        self, run_id: str, *, timeout: float | None = None
    ) -> dict[str, Any]:
        """Wait for an agent run to complete.

        Gateway method: ``agent.wait``
        Verified param: ``{runId}``
        """
        return await self.call("agent.wait", {"runId": run_id}, timeout=timeout)

    # ------------------------------------------------------------------ #
    # Sessions admin facade
    # ------------------------------------------------------------------ #

    async def sessions_list(self) -> list[dict[str, Any]]:
        """List all active sessions.

        Gateway method: ``sessions.list``
        """
        result = await self.call("sessions.list", {})
        sessions: list[dict[str, Any]] = result.get("sessions", [])
        return sessions

    async def sessions_preview(self, keys: list[str]) -> dict[str, Any]:
        """Return a preview of one or more sessions.

        Gateway method: ``sessions.preview``
        Verified params: ``{keys: string[]}``
        """
        return await self.call("sessions.preview", {"keys": keys})

    async def sessions_resolve(self, key: str) -> dict[str, Any]:
        """Resolve a session key to its full descriptor.

        Gateway method: ``sessions.resolve``
        Verified param: ``{key}``
        """
        return await self.call("sessions.resolve", {"key": key})

    async def sessions_patch(
        self, key: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply a partial update to a session.

        Gateway method: ``sessions.patch``
        Verified params: ``{key, ...patch}``
        """
        return await self.call(
            "sessions.patch", {"key": key, **patch}
        )

    async def sessions_reset(self, key: str) -> dict[str, Any]:
        """Reset (clear) a session's conversation history.

        Gateway method: ``sessions.reset``
        Verified param: ``{key}``
        """
        return await self.call("sessions.reset", {"key": key})

    async def sessions_delete(self, key: str) -> dict[str, Any]:
        """Delete a session permanently.

        Gateway method: ``sessions.delete``
        Verified param: ``{key}``
        """
        return await self.call("sessions.delete", {"key": key})

    async def sessions_compact(self, key: str) -> dict[str, Any]:
        """Compact a session (summarise history to reduce token usage).

        Gateway method: ``sessions.compact``
        Verified param: ``{key}``
        """
        return await self.call("sessions.compact", {"key": key})

    # ------------------------------------------------------------------ #
    # Config facade
    # ------------------------------------------------------------------ #

    async def config_get(self) -> dict[str, Any]:
        """Fetch the full runtime configuration.

        Gateway method: ``config.get``
        """
        return await self.call("config.get", {})

    async def config_schema(self) -> dict[str, Any]:
        """Fetch the JSON Schema for the runtime configuration.

        Gateway method: ``config.schema``
        """
        return await self.call("config.schema", {})

    async def config_set(self, raw: str) -> dict[str, Any]:
        """Replace the entire runtime configuration.

        Gateway method: ``config.set``
        Verified param: ``{raw}`` — full config file contents as a JSON string.
        """
        return await self.call("config.set", {"raw": raw})

    async def config_patch(
        self, raw: str, base_hash: str | None = None
    ) -> dict[str, Any]:
        """Write a new config with optional optimistic concurrency control.

        Gateway method: ``config.patch``
        Verified params: ``{raw, baseHash?}`` — compare-and-swap on the config file.
        Call :meth:`config_get` first to obtain the current ``hash``.
        """
        params: dict[str, Any] = {"raw": raw}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self.call("config.patch", params)

    async def config_apply(
        self, raw: str, base_hash: str | None = None
    ) -> dict[str, Any]:
        """Apply a new config with optional optimistic concurrency control.

        Gateway method: ``config.apply``
        Params: ``{raw, baseHash?}``
        Call :meth:`config_get` first to obtain the current ``hash``.
        """
        params: dict[str, Any] = {"raw": raw}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self.call("config.apply", params)

    # ------------------------------------------------------------------ #
    # Approvals facade
    # ------------------------------------------------------------------ #
    #
    # NOTE: ``approvals.list`` does NOT exist as a gateway RPC method
    # (verified 2026-02-21).  Pending approvals are delivered as push
    # events (``approval.requested``) via ``subscribe()``.
    #
    # However, ``exec.approval.resolve`` DOES exist as an RPC method
    # (verified 2026-02-21).  Use it to approve or deny a pending
    # execution request after receiving the push event.
    #

    async def resolve_approval(
        self,
        request_id: str,
        decision: str,
    ) -> dict[str, Any]:
        """Approve or deny a pending execution request.

        Gateway method: ``exec.approval.resolve``
        Verified params: ``{id, decision}``

        Workflow: subscribe for ``approval.requested`` events to learn about
        pending approvals, then call this method to resolve them.
        """
        return await self.call(
            "exec.approval.resolve",
            {"id": request_id, "decision": decision},
        )

    # ------------------------------------------------------------------ #
    # Node / presence facade
    # ------------------------------------------------------------------ #

    async def system_presence(self) -> dict[str, Any]:
        """Return the gateway's system-presence status.

        Gateway method: ``system-presence``
        """
        return await self.call("system-presence", {})

    async def node_list(self) -> list[dict[str, Any]]:
        """List all registered nodes.

        Gateway method: ``node.list``
        """
        result = await self.call("node.list", {})
        nodes: list[dict[str, Any]] = result.get("nodes", [])
        return nodes

    async def node_describe(self, node_id: str) -> dict[str, Any]:
        """Fetch details for a specific node.

        Gateway method: ``node.describe`` (unverified — may not exist).
        """
        return await self.call("node.describe", {"id": node_id})

    async def node_invoke(
        self,
        node_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke an action on a specific node.

        Gateway method: ``node.invoke`` (unverified — may not exist).
        """
        params: dict[str, Any] = {"id": node_id, "action": action}
        if payload is not None:
            params["payload"] = payload
        return await self.call("node.invoke", params)

    # ------------------------------------------------------------------ #
    # Ops facade
    # ------------------------------------------------------------------ #

    async def logs_tail(self) -> dict[str, Any]:
        """Fetch recent log lines.

        Gateway method: ``logs.tail``
        Verified params: ``{}`` — no parameters accepted.
        Returns ``{file, cursor, size, lines: [...]}``
        """
        return await self.call("logs.tail", {})

    async def usage_summary(self) -> dict[str, Any]:
        """Return token-usage statistics from session metadata.

        NOTE: ``usage.summary`` does not exist as a gateway RPC method
        (verified 2026-02-21).  Usage data is embedded in each session
        object (``inputTokens``, ``outputTokens``, ``totalTokens``).
        This method aggregates it from ``sessions.list``.
        """
        result = await self.call("sessions.list", {})
        sessions: list[dict[str, Any]] = result.get("sessions", [])
        total_input = sum(s.get("inputTokens", 0) for s in sessions)
        total_output = sum(s.get("outputTokens", 0) for s in sessions)
        total_tokens = sum(s.get("totalTokens", 0) for s in sessions)
        return {
            "totalInputTokens": total_input,
            "totalOutputTokens": total_output,
            "totalTokens": total_tokens,
            "sessionCount": len(sessions),
        }

    # ------------------------------------------------------------------ #
    # Device management facade
    # ------------------------------------------------------------------ #

    async def device_token_rotate(
        self, device_id: str, role: str
    ) -> dict[str, Any]:
        """Rotate a device's auth token.

        Gateway method: ``device.token.rotate``
        Verified params: ``{deviceId, role}``
        """
        return await self.call(
            "device.token.rotate", {"deviceId": device_id, "role": role}
        )

    async def device_token_revoke(
        self, device_id: str, role: str
    ) -> dict[str, Any]:
        """Revoke a device's auth token.

        Gateway method: ``device.token.revoke``
        Verified params: ``{deviceId, role}``
        """
        return await self.call(
            "device.token.revoke", {"deviceId": device_id, "role": role}
        )

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "Gateway":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

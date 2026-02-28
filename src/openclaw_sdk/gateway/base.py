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

    async def chat_inject(self, session_key: str, message: str) -> dict[str, Any]:
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

    async def sessions_patch(self, key: str, patch: dict[str, Any]) -> dict[str, Any]:
        """Apply a partial update to a session.

        Gateway method: ``sessions.patch``
        Verified params: ``{key, ...patch}``
        """
        return await self.call("sessions.patch", {"key": key, **patch})

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

    async def exec_approval_request(
        self,
        command: str,
        *,
        timeout_ms: int | None = None,
        agent_id: str | None = None,
        session_key: str | None = None,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        """Request approval for a command execution. Blocks until resolved.

        Gateway method: ``exec.approval.request``
        Returns ``{id, decision, createdAtMs, expiresAtMs}``.
        Decision: ``"allow-once"`` | ``"allow-always"`` | ``"deny"`` | null (expired).
        """
        params: dict[str, Any] = {"command": command}
        if timeout_ms is not None:
            params["timeoutMs"] = timeout_ms
        if agent_id is not None:
            params["agentId"] = agent_id
        if session_key is not None:
            params["sessionKey"] = session_key
        if node_id is not None:
            params["nodeId"] = node_id
        return await self.call("exec.approval.request", params)

    async def exec_approval_wait_decision(self, approval_id: str) -> dict[str, Any]:
        """Wait for an approval decision. Blocks until resolved.

        Gateway method: ``exec.approval.waitDecision``
        Returns ``{id, decision, createdAtMs, expiresAtMs}``.
        """
        return await self.call("exec.approval.waitDecision", {"id": approval_id})

    async def exec_approvals_get(self) -> dict[str, Any]:
        """Get approval settings/config.

        Gateway method: ``exec.approvals.get``
        Returns ``{path, exists, hash, file: {version, socket, defaults, agents}}``.
        """
        return await self.call("exec.approvals.get", {})

    async def exec_approvals_set(
        self, file: dict[str, Any], base_hash: str | None = None
    ) -> dict[str, Any]:
        """Set approval settings with optimistic concurrency.

        Gateway method: ``exec.approvals.set``
        Params: ``{file: {version, ...}, baseHash?}``
        """
        params: dict[str, Any] = {"file": file}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self.call("exec.approvals.set", params)

    async def exec_approvals_node_get(self, node_id: str) -> dict[str, Any]:
        """Get node-level approval settings. Proxied to node.

        Gateway method: ``exec.approvals.node.get``
        Unavailable if node is not connected.
        """
        return await self.call("exec.approvals.node.get", {"nodeId": node_id})

    async def exec_approvals_node_set(
        self,
        node_id: str,
        file: dict[str, Any],
        base_hash: str | None = None,
    ) -> dict[str, Any]:
        """Set node-level approval settings. Proxied to node.

        Gateway method: ``exec.approvals.node.set``
        Params: ``{nodeId, file: {version, ...}, baseHash?}``
        """
        params: dict[str, Any] = {"nodeId": node_id, "file": file}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self.call("exec.approvals.node.set", params)

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

    async def node_rename(self, node_id: str, display_name: str) -> dict[str, Any]:
        """Rename a node.

        Gateway method: ``node.rename``
        """
        return await self.call(
            "node.rename", {"nodeId": node_id, "displayName": display_name}
        )

    async def node_invoke_result(self, **params: Any) -> dict[str, Any]:
        """Submit an invoke result back to the gateway.

        Gateway method: ``node.invoke.result``

        Note:
            Role-restricted — requires ``node`` role.
        """
        return await self.call("node.invoke.result", params)

    async def node_event(self, **params: Any) -> dict[str, Any]:
        """Emit a node event.

        Gateway method: ``node.event``

        Note:
            Role-restricted — requires ``node`` role.
        """
        return await self.call("node.event", params)

    async def node_pair_request(self, node_id: str) -> dict[str, Any]:
        """Request node pairing.

        Gateway method: ``node.pair.request``
        """
        return await self.call("node.pair.request", {"nodeId": node_id})

    async def node_pair_list(self) -> dict[str, Any]:
        """List pending and paired nodes.

        Gateway method: ``node.pair.list``

        Returns:
            Dict with ``pending`` and ``paired`` arrays.
        """
        return await self.call("node.pair.list", {})

    async def node_pair_approve(self, request_id: str) -> dict[str, Any]:
        """Approve a node pairing request.

        Gateway method: ``node.pair.approve``
        """
        return await self.call("node.pair.approve", {"requestId": request_id})

    async def node_pair_reject(self, request_id: str) -> dict[str, Any]:
        """Reject a node pairing request.

        Gateway method: ``node.pair.reject``
        """
        return await self.call("node.pair.reject", {"requestId": request_id})

    async def node_pair_verify(self, node_id: str, token: str) -> dict[str, Any]:
        """Verify a node pairing.

        Gateway method: ``node.pair.verify``
        """
        return await self.call("node.pair.verify", {"nodeId": node_id, "token": token})

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
    # Usage facade
    # ------------------------------------------------------------------ #

    async def usage_status(self) -> dict[str, Any]:
        """Get provider usage status (quotas, limits, plans).

        Gateway method: ``usage.status``
        Returns ``{updatedAt, providers: [{provider, displayName, windows, plan}]}``
        """
        return await self.call("usage.status", {})

    async def usage_cost(self) -> dict[str, Any]:
        """Get detailed cost breakdown by day.

        Gateway method: ``usage.cost``
        Returns ``{updatedAt, days, daily: [...], totals: {...}}``
        """
        return await self.call("usage.cost", {})

    async def sessions_usage(self) -> dict[str, Any]:
        """Get per-session usage analytics.

        Gateway method: ``sessions.usage``
        Returns ``{updatedAt, startDate, endDate, sessions: [{key, usage: {...}}]}``
        """
        return await self.call("sessions.usage", {})

    # ------------------------------------------------------------------ #
    # Device management facade
    # ------------------------------------------------------------------ #

    async def device_token_rotate(self, device_id: str, role: str) -> dict[str, Any]:
        """Rotate a device's auth token.

        Gateway method: ``device.token.rotate``
        Verified params: ``{deviceId, role}``
        """
        return await self.call(
            "device.token.rotate", {"deviceId": device_id, "role": role}
        )

    async def device_token_revoke(self, device_id: str, role: str) -> dict[str, Any]:
        """Revoke a device's auth token.

        Gateway method: ``device.token.revoke``
        Verified params: ``{deviceId, role}``
        """
        return await self.call(
            "device.token.revoke", {"deviceId": device_id, "role": role}
        )

    async def device_pair_list(self) -> dict[str, Any]:
        """List pending and paired devices.

        Gateway method: ``device.pair.list``
        Returns ``{pending: [...], paired: [...]}``
        """
        return await self.call("device.pair.list", {})

    async def device_pair_approve(self, request_id: str) -> dict[str, Any]:
        """Approve a device pairing request.

        Gateway method: ``device.pair.approve``
        Verified params: ``{requestId}``
        """
        return await self.call("device.pair.approve", {"requestId": request_id})

    async def device_pair_reject(self, request_id: str) -> dict[str, Any]:
        """Reject a device pairing request.

        Gateway method: ``device.pair.reject``
        Verified params: ``{requestId}``
        """
        return await self.call("device.pair.reject", {"requestId": request_id})

    async def device_pair_remove(self, device_id: str) -> dict[str, Any]:
        """Remove a paired device.

        Gateway method: ``device.pair.remove``
        Verified params: ``{deviceId}``
        """
        return await self.call("device.pair.remove", {"deviceId": device_id})

    # ------------------------------------------------------------------ #
    # Discovery facade
    # ------------------------------------------------------------------ #

    async def models_list(self) -> dict[str, Any]:
        """List all available models across providers.

        Gateway method: ``models.list``

        Returns:
            Dict with ``models`` array — each entry has ``id``, ``name``,
            ``provider``, ``contextWindow``, ``reasoning``, and ``input``.
        """
        return await self.call("models.list", {})

    async def tools_catalog(self) -> dict[str, Any]:
        """Get the full tool catalog with profiles and groups.

        Gateway method: ``tools.catalog``

        Returns:
            Dict with ``agentId``, ``profiles`` (list of profile descriptors),
            and ``groups`` (list of tool groups with their tools).
        """
        return await self.call("tools.catalog", {})

    async def system_status(self) -> dict[str, Any]:
        """Get gateway system status.

        Gateway method: ``status``

        Returns:
            Dict with ``linkChannel``, ``heartbeat``, ``channelSummary``,
            ``queuedSystemEvents``, and ``sessions`` summary.
        """
        return await self.call("status", {})

    async def doctor_memory_status(self) -> dict[str, Any]:
        """Get memory/embedding health status.

        Gateway method: ``doctor.memory.status``

        Returns:
            Dict with ``agentId``, ``provider``, and ``embedding``
            (containing ``ok`` and optional ``error``).
        """
        return await self.call("doctor.memory.status", {})

    # ------------------------------------------------------------------ #
    # Skills facade
    # ------------------------------------------------------------------ #

    async def skills_status(self) -> dict[str, Any]:
        """Get skills status and installed skill list.

        Gateway method: ``skills.status``

        Returns:
            Dict with ``workspaceDir``, ``managedSkillsDir``, and ``skills``
            array containing skill descriptors.
        """
        return await self.call("skills.status", {})

    async def skills_bins(self) -> dict[str, Any]:
        """Get skills binary information.

        Gateway method: ``skills.bins``

        Note:
            Role-restricted — may return unauthorized for ``operator`` role.
        """
        return await self.call("skills.bins", {})

    async def skills_install(self, name: str, install_id: str) -> dict[str, Any]:
        """Install a skill.

        Gateway method: ``skills.install``

        Args:
            name: The skill name to install.
            install_id: Unique installation identifier.
        """
        return await self.call(
            "skills.install", {"name": name, "installId": install_id}
        )

    async def skills_update(self, skill_key: str) -> dict[str, Any]:
        """Update a skill.

        Gateway method: ``skills.update``

        Args:
            skill_key: The skill key identifying the skill to update.
        """
        return await self.call("skills.update", {"skillKey": skill_key})

    # ------------------------------------------------------------------ #
    # Agents facade
    # ------------------------------------------------------------------ #

    async def agents_list(self) -> dict[str, Any]:
        """List all agents. Gateway method: ``agents.list``"""
        return await self.call("agents.list", {})

    async def agents_create(
        self, name: str, workspace: str | None = None
    ) -> dict[str, Any]:
        """Create a new agent. Gateway method: ``agents.create``"""
        params: dict[str, Any] = {"name": name}
        if workspace is not None:
            params["workspace"] = workspace
        return await self.call("agents.create", params)

    async def agents_update(self, agent_id: str, **patch: Any) -> dict[str, Any]:
        """Update an agent. Gateway method: ``agents.update``"""
        return await self.call("agents.update", {"agentId": agent_id, **patch})

    async def agents_delete(self, agent_id: str) -> dict[str, Any]:
        """Delete an agent. Gateway method: ``agents.delete``"""
        return await self.call("agents.delete", {"agentId": agent_id})

    async def agents_files_list(self, agent_id: str) -> dict[str, Any]:
        """List agent workspace files. Gateway method: ``agents.files.list``"""
        return await self.call("agents.files.list", {"agentId": agent_id})

    async def agents_files_get(self, agent_id: str, name: str) -> dict[str, Any]:
        """Get agent file content. Gateway method: ``agents.files.get``"""
        return await self.call("agents.files.get", {"agentId": agent_id, "name": name})

    async def agents_files_set(
        self, agent_id: str, name: str, content: str
    ) -> dict[str, Any]:
        """Set agent file content. Gateway method: ``agents.files.set``"""
        return await self.call(
            "agents.files.set",
            {"agentId": agent_id, "name": name, "content": content},
        )

    async def agent_identity_get(self) -> dict[str, Any]:
        """Get agent identity. Gateway method: ``agent.identity.get``"""
        return await self.call("agent.identity.get", {})

    # ------------------------------------------------------------------ #
    # TTS facade
    # ------------------------------------------------------------------ #

    async def tts_enable(self) -> dict[str, Any]:
        """Enable text-to-speech.

        Gateway method: ``tts.enable``

        Returns:
            ``{enabled: true}``
        """
        return await self.call("tts.enable", {})

    async def tts_disable(self) -> dict[str, Any]:
        """Disable text-to-speech.

        Gateway method: ``tts.disable``

        Returns:
            ``{enabled: false}``
        """
        return await self.call("tts.disable", {})

    async def tts_convert(self, text: str) -> dict[str, Any]:
        """Convert text to speech audio.

        Gateway method: ``tts.convert``
        Verified params: ``{text}``
        """
        return await self.call("tts.convert", {"text": text})

    async def tts_set_provider(self, provider: str) -> dict[str, Any]:
        """Set TTS provider.

        Gateway method: ``tts.setProvider``
        Verified params: ``{provider}`` — ``"openai"`` | ``"elevenlabs"`` | ``"edge"``
        """
        return await self.call("tts.setProvider", {"provider": provider})

    async def tts_status(self) -> dict[str, Any]:
        """Get TTS status.

        Gateway method: ``tts.status``
        """
        return await self.call("tts.status", {})

    async def tts_providers(self) -> dict[str, Any]:
        """List available TTS providers.

        Gateway method: ``tts.providers``
        """
        return await self.call("tts.providers", {})

    # ------------------------------------------------------------------ #
    # Wizard facade
    # ------------------------------------------------------------------ #

    async def wizard_start(self) -> dict[str, Any]:
        """Start a wizard session.

        Gateway method: ``wizard.start``
        """
        return await self.call("wizard.start", {})

    async def wizard_next(self, session_id: str) -> dict[str, Any]:
        """Advance to the next wizard step.

        Gateway method: ``wizard.next``
        Verified params: ``{sessionId}``
        """
        return await self.call("wizard.next", {"sessionId": session_id})

    async def wizard_cancel(self, session_id: str) -> dict[str, Any]:
        """Cancel a wizard session.

        Gateway method: ``wizard.cancel``
        Verified params: ``{sessionId}``
        """
        return await self.call("wizard.cancel", {"sessionId": session_id})

    async def wizard_status(self, session_id: str) -> dict[str, Any]:
        """Get wizard session state.

        Gateway method: ``wizard.status``
        Verified params: ``{sessionId}``
        """
        return await self.call("wizard.status", {"sessionId": session_id})

    # ------------------------------------------------------------------ #
    # Voice wake facade
    # ------------------------------------------------------------------ #

    async def voicewake_get(self) -> dict[str, Any]:
        """Get voice wake triggers.

        Gateway method: ``voicewake.get``

        Returns:
            ``{triggers: string[]}``
        """
        return await self.call("voicewake.get", {})

    async def voicewake_set(self, triggers: list[str]) -> dict[str, Any]:
        """Set voice wake triggers.

        Gateway method: ``voicewake.set``
        Verified params: ``{triggers: string[]}``
        """
        return await self.call("voicewake.set", {"triggers": triggers})

    # ------------------------------------------------------------------ #
    # System misc facade
    # ------------------------------------------------------------------ #

    async def system_event(self, text: str) -> dict[str, Any]:
        """Emit a system event.

        Gateway method: ``system-event``
        Verified params: ``{text}``
        """
        return await self.call("system-event", {"text": text})

    async def send_message(self, to: str, idempotency_key: str) -> dict[str, Any]:
        """Send a message.

        Gateway method: ``send``
        Verified params: ``{to, idempotencyKey}``
        """
        return await self.call("send", {"to": to, "idempotencyKey": idempotency_key})

    async def browser_request(self, method: str, path: str) -> dict[str, Any]:
        """Proxy a browser request.

        Gateway method: ``browser.request``
        Verified params: ``{method, path}``
        """
        return await self.call("browser.request", {"method": method, "path": path})

    async def last_heartbeat(self) -> dict[str, Any]:
        """Get last heartbeat info.

        Gateway method: ``last-heartbeat``

        Returns:
            ``{ts, status, reason, durationMs}``
        """
        return await self.call("last-heartbeat", {})

    async def set_heartbeats(self, enabled: bool) -> dict[str, Any]:
        """Enable or disable heartbeats.

        Gateway method: ``set-heartbeats``
        Verified params: ``{enabled: bool}``
        """
        return await self.call("set-heartbeats", {"enabled": enabled})

    async def update_run(self) -> dict[str, Any]:
        """Run a system update.

        Gateway method: ``update.run``

        Returns:
            ``{ok, result: {status, mode, ...}, restart, sentinel}``
        """
        return await self.call("update.run", {})

    async def secrets_reload(self) -> dict[str, Any]:
        """Reload secrets from disk.

        Gateway method: ``secrets.reload``

        Returns:
            ``{ok, warningCount}``
        """
        return await self.call("secrets.reload", {})

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "Gateway":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

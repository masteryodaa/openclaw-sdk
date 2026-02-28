"""ConfigManager — thin wrapper around the gateway ``config.*`` namespace.

All ``config.set``, ``config.patch``, and ``config.apply`` methods use
the **raw config string** format: ``{raw: "<full JSON>", baseHash?: "<hash>"}``.
Call :meth:`ConfigManager.get` first to obtain the current config and its hash
for optimistic concurrency control (compare-and-swap).
"""

from __future__ import annotations

import json
from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


# Known LLM providers and their common models.
# Provider names match OpenClaw's config format.
KNOWN_PROVIDERS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "o3",
        "o4-mini",
    ],
    "google": [
        "gemini-3-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ],
    "google-antigravity": [
        "gemini-3-flash",
        "gemini-3-pro-low",
        "gemini-3-pro-high",
        "gemini-3.1-pro-high",
        "claude-sonnet-4-5",
        "claude-sonnet-4-5-thinking",
        "claude-opus-4-6-thinking",
    ],
    "google-vertex": [
        "gemini-3-flash",
        "gemini-2.5-pro",
    ],
    "openrouter": [
        "anthropic/claude-sonnet-4-6",
        "openai/gpt-4.1",
        "google/gemini-3-flash",
    ],
    "ollama": [
        "llama3.3",
        "mistral",
        "codellama",
        "deepseek-r1",
    ],
}


class ConfigManager:
    """Manage the OpenClaw runtime configuration via the gateway.

    All methods delegate to ``config.*`` gateway RPC calls.

    Usage::

        async with OpenClawClient.connect() as client:
            cfg = await client.config_mgr.get()
            raw = cfg["raw"]            # current config as JSON string
            base_hash = cfg.get("hash") # for CAS
            # … modify raw …
            await client.config_mgr.set(new_raw)
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def get(self) -> dict[str, Any]:
        """Fetch the full current runtime configuration.

        Gateway method: ``config.get``

        Returns:
            ``{path, exists, raw, parsed}`` — ``raw`` is the config file
            contents as a JSON string, ``parsed`` is the deserialized dict.
        """
        return await self._gateway.call("config.get", {})

    async def schema(self) -> dict[str, Any]:
        """Fetch the JSON Schema for the runtime configuration.

        Gateway method: ``config.schema``

        Returns:
            ``{schema: {$schema, type, properties, …}}``
        """
        return await self._gateway.call("config.schema", {})

    async def set(self, raw: str) -> dict[str, Any]:
        """Replace the entire runtime configuration.

        Gateway method: ``config.set``
        Verified params: ``{raw}`` — full config file as a JSON string.

        Args:
            raw: The complete configuration as a JSON string.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call("config.set", {"raw": raw})

    async def patch(
        self,
        raw: str,
        base_hash: str | None = None,
    ) -> dict[str, Any]:
        """Write a new config with optional optimistic concurrency control.

        Gateway method: ``config.patch``
        Verified params: ``{raw, baseHash?}`` — compare-and-swap on the
        config file.  Call :meth:`get` first to obtain the current hash.

        Args:
            raw: The full configuration as a JSON string.
            base_hash: Optional ETag / base hash for compare-and-swap.

        Returns:
            Gateway response dict.
        """
        params: dict[str, Any] = {"raw": raw}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self._gateway.call("config.patch", params)

    async def apply(
        self,
        raw: str,
        base_hash: str | None = None,
    ) -> dict[str, Any]:
        """Apply a new config with optional optimistic concurrency control.

        Gateway method: ``config.apply``
        Params: ``{raw, baseHash?}``

        Args:
            raw: The full configuration as a JSON string.
            base_hash: Optional ETag / base hash for compare-and-swap.

        Returns:
            Gateway response dict.
        """
        params: dict[str, Any] = {"raw": raw}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self._gateway.call("config.apply", params)

    # ------------------------------------------------------------------ #
    # Discovery — live model & tool queries
    # ------------------------------------------------------------------ #

    async def discover_models(self) -> dict[str, Any]:
        """Discover available models from the live gateway.

        Gateway method: ``models.list``

        Returns the full ``models.list`` response with all providers and models.
        """
        return await self._gateway.call("models.list", {})

    async def discover_tools(self) -> dict[str, Any]:
        """Discover available tools from the live gateway.

        Gateway method: ``tools.catalog``

        Returns the full ``tools.catalog`` response with profiles and tool groups.
        """
        return await self._gateway.call("tools.catalog", {})

    # ------------------------------------------------------------------ #
    # High-level helpers — model & provider switching
    # ------------------------------------------------------------------ #

    async def get_parsed(self) -> tuple[dict[str, Any], str | None]:
        """Fetch the current config as a parsed dict + its hash.

        Returns:
            ``(config_dict, hash)`` — the hash may be ``None``.
        """
        result = await self.get()
        raw = result.get("raw", "{}")
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        base_hash = result.get("hash")
        return parsed, base_hash

    async def get_agent_model(self, agent_id: str) -> dict[str, Any]:
        """Get the current model/provider for a specific agent.

        Handles both flat string and ``{primary: "provider/model"}`` formats
        used by OpenClaw configs.

        Returns:
            ``{agent_id, provider, model, model_full, api_key_set}``
        """
        config, _ = await self.get_parsed()
        agents = config.get("agents", {})
        agent_cfg = agents.get(agent_id, {})

        # Extract model string from object or flat value
        raw_model = agent_cfg.get("model", agent_cfg.get("llm_model", "unknown"))
        if isinstance(raw_model, dict):
            model_full = raw_model.get("primary", "unknown")
        else:
            model_full = str(raw_model) if raw_model else "unknown"

        # Detect provider from model string (e.g. "google-antigravity/gemini-3-flash")
        explicit_provider = agent_cfg.get("modelProvider", agent_cfg.get("llm_provider"))
        if explicit_provider:
            provider = explicit_provider
        elif "/" in model_full:
            provider = model_full.rsplit("/", 1)[0]
        else:
            provider = "unknown"

        # Extract short model name (after provider prefix)
        model_short = model_full.split("/", 1)[1] if "/" in model_full else model_full

        return {
            "agent_id": agent_id,
            "provider": provider,
            "model": model_short,
            "model_full": model_full,
            "api_key_set": bool(agent_cfg.get("llm_api_key") or agent_cfg.get("apiKey")),
        }

    async def list_agents(self) -> list[str]:
        """List all configured agent IDs.

        Parses the current config and returns agent identifiers from
        the ``agents`` section.

        Returns:
            List of agent ID strings.
        """
        config, _ = await self.get_parsed()
        return list(config.get("agents", {}).keys())

    async def set_agent_model(
        self,
        agent_id: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Switch the model and/or provider for a specific agent.

        Uses compare-and-swap to safely update the config.
        Writes model in OpenClaw's ``{primary: "provider/model"}`` format.

        Args:
            agent_id: The agent to update.
            provider: New LLM provider (e.g. ``"openai"``, ``"google-antigravity"``).
            model: New model name (e.g. ``"gpt-4o"``, ``"gemini-3-flash"``).
                Can be a short name or full ``provider/model`` string.
            api_key: Optional API key for the new provider.

        Returns:
            Gateway response dict.
        """
        config, base_hash = await self.get_parsed()
        agents = config.setdefault("agents", {})
        agent_cfg = agents.setdefault(agent_id, {})

        # Resolve the effective provider from existing config
        existing_model = agent_cfg.get("model", {})
        if isinstance(existing_model, dict):
            existing_primary = existing_model.get("primary", "")
        else:
            existing_primary = str(existing_model) if existing_model else ""
        existing_provider = existing_primary.split("/", 1)[0] if "/" in existing_primary else ""

        effective_provider = provider or existing_provider

        if model is not None:
            # Build the full "provider/model" string if not already prefixed
            if "/" in model:
                model_full = model
            elif effective_provider:
                model_full = f"{effective_provider}/{model}"
            else:
                model_full = model

            # Write in OpenClaw's {primary: "provider/model"} format
            if isinstance(existing_model, dict):
                existing_model["primary"] = model_full
            else:
                agent_cfg["model"] = {"primary": model_full}
        elif provider is not None and existing_primary:
            # Provider changed but model not specified — update provider prefix
            old_model_name = (
                existing_primary.split("/", 1)[1] if "/" in existing_primary else existing_primary
            )
            model_full = f"{provider}/{old_model_name}"
            if isinstance(existing_model, dict):
                existing_model["primary"] = model_full
            else:
                agent_cfg["model"] = {"primary": model_full}

        if api_key is not None:
            agent_cfg["apiKey"] = api_key

        return await self.patch(json.dumps(config, indent=2), base_hash=base_hash)

    @staticmethod
    def available_providers() -> list[str]:
        """Return a list of known LLM provider names."""
        return list(KNOWN_PROVIDERS.keys())

    @staticmethod
    def available_models(provider: str | None = None) -> dict[str, list[str]]:
        """Return known models, optionally filtered by provider.

        Args:
            provider: If given, return only models for that provider.

        Returns:
            ``{provider: [model, ...], ...}``
        """
        if provider:
            models = KNOWN_PROVIDERS.get(provider, [])
            return {provider: models}
        return dict(KNOWN_PROVIDERS)

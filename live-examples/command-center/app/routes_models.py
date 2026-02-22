"""Model & provider management endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.config.manager import KNOWN_PROVIDERS

from . import gateway

router = APIRouter(prefix="/api/models", tags=["models"])


class SetModelBody(BaseModel):
    agent_id: str
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None


@router.get("/providers")
async def list_providers():
    """List known LLM providers and their models."""
    return {"providers": KNOWN_PROVIDERS}


@router.get("/agent/{agent_id}")
async def get_agent_model(agent_id: str):
    """Get current model/provider for a specific agent."""
    client = await gateway.get_client()
    result = await client.config_mgr.get_agent_model(agent_id)
    return result


@router.get("/all")
async def get_all_agent_models():
    """Get model/provider for all agents from the config."""
    client = await gateway.get_client()
    config, _ = await client.config_mgr.get_parsed()
    agents = config.get("agents", {})
    result = []
    for agent_id, agent_cfg in agents.items():
        # Extract model string from object or flat value
        raw_model = agent_cfg.get("model", agent_cfg.get("llm_model", "unknown"))
        if isinstance(raw_model, dict):
            model_full = raw_model.get("primary", "unknown")
        else:
            model_full = str(raw_model) if raw_model else "unknown"

        # Auto-detect provider from model string prefix
        explicit_provider = agent_cfg.get("modelProvider", agent_cfg.get("llm_provider"))
        if explicit_provider:
            provider = explicit_provider
        elif "/" in model_full:
            provider = model_full.rsplit("/", 1)[0]
        else:
            provider = "unknown"

        model_short = model_full.split("/", 1)[1] if "/" in model_full else model_full

        result.append({
            "agent_id": agent_id,
            "provider": provider,
            "model": model_short,
            "model_full": model_full,
            "api_key_set": bool(agent_cfg.get("llm_api_key") or agent_cfg.get("apiKey")),
        })
    return {"agents": result}


@router.post("/set")
async def set_agent_model(body: SetModelBody):
    """Switch model and/or provider for a specific agent."""
    client = await gateway.get_client()
    result = await client.config_mgr.set_agent_model(
        body.agent_id,
        provider=body.provider,
        model=body.model,
        api_key=body.api_key,
    )
    return {"success": True, "result": result}

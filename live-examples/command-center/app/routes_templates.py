"""Agent Templates endpoints — browse and create agents from templates."""

from __future__ import annotations

from fastapi import APIRouter

from openclaw_sdk.templates.registry import TEMPLATES, get_template, list_templates

from . import gateway

router = APIRouter(prefix="/api/templates", tags=["templates"])


# -- Endpoints --


@router.get("")
async def get_templates():
    """List all available agent templates."""
    templates = list_templates()
    details = []
    for name in templates:
        tmpl = TEMPLATES[name]
        details.append({
            "name": name,
            "system_prompt": tmpl.get("system_prompt", ""),
            "tool_policy": str(tmpl.get("tool_policy", "")),
            "channels": tmpl.get("channels", []),
            "permission_mode": tmpl.get("permission_mode", "auto"),
            "enable_memory": tmpl.get("enable_memory", False),
        })
    return {"templates": details}


@router.get("/{name}")
async def get_template_detail(name: str):
    """Get details for a specific template."""
    try:
        config = get_template(name)
        return {
            "name": name,
            "agent_id": config.agent_id,
            "system_prompt": config.system_prompt,
            "tool_policy": str(config.tool_policy) if config.tool_policy else None,
        }
    except KeyError as exc:
        return {"error": str(exc)}


@router.post("/{name}/create")
async def create_agent_from_template(name: str, agent_id: str):
    """Create a new agent from a template."""
    try:
        client = await gateway.get_client()
        agent = await client.create_agent_from_template(name, agent_id)
        return {
            "created": True,
            "agent_id": agent.agent_id,
            "template": name,
        }
    except KeyError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}

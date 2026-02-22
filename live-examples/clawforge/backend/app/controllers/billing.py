"""Billing controller — cost tracking and aggregation."""

from __future__ import annotations

from app.helpers import database


async def get_summary() -> dict:
    """Get overall billing summary across all projects."""
    projects = await database.list_projects()
    total_cost = sum(p.get("total_cost_usd", 0) for p in projects)
    total_tokens = sum(p.get("total_tokens", 0) for p in projects)

    project_billing = []
    for p in projects:
        messages = await database.get_messages(p["id"])
        project_billing.append({
            "project_id": p["id"],
            "project_name": p["name"],
            "total_cost_usd": p.get("total_cost_usd", 0),
            "total_tokens": p.get("total_tokens", 0),
            "message_count": len(messages),
        })

    return {
        "total_cost_usd": total_cost,
        "total_tokens": total_tokens,
        "project_count": len(projects),
        "projects": project_billing,
    }


async def get_project_costs(project_id: str) -> dict | None:
    """Get cost breakdown for a single project."""
    project = await database.get_project(project_id)
    if not project:
        return None

    messages = await database.get_messages(project_id)
    message_costs = []
    for m in messages:
        if m.get("token_usage") or m.get("cost_usd"):
            message_costs.append({
                "message_id": m["id"],
                "role": m["role"],
                "token_usage": m.get("token_usage"),
                "cost_usd": m.get("cost_usd", 0),
                "created_at": m["created_at"],
            })

    return {
        "project_id": project_id,
        "project_name": project["name"],
        "total_cost_usd": project.get("total_cost_usd", 0),
        "total_tokens": project.get("total_tokens", 0),
        "message_count": len(messages),
        "cost_breakdown": message_costs,
    }

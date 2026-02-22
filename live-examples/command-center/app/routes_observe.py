"""Observability endpoints — cost tracking, tracing, prompt versioning."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.prompts.versioning import PromptStore
from openclaw_sdk.tracking.cost import CostTracker, DEFAULT_PRICING
from openclaw_sdk.tracing.tracer import Tracer

from . import gateway

router = APIRouter(prefix="/api/observe", tags=["observability"])

# Shared singleton instances (per-server lifetime)
_cost_tracker = CostTracker()
_tracer = Tracer()
_prompt_store = PromptStore()


# ── Request models ──


class PromptSaveBody(BaseModel):
    name: str
    content: str
    metadata: dict[str, Any] = {}
    tags: list[str] = []


class PromptDiffBody(BaseModel):
    name: str
    version_a: int
    version_b: int


# ── Cost Tracking ──


@router.get("/costs")
async def get_costs(agent_id: str | None = None, user_id: str | None = None):
    """Get cost summary, optionally filtered by agent or user."""
    summary = _cost_tracker.get_summary(agent_id=agent_id, user_id=user_id)
    return {
        "total_queries": summary.total_queries,
        "total_cost_usd": round(summary.total_cost_usd, 6),
        "total_input_tokens": summary.total_input_tokens,
        "total_output_tokens": summary.total_output_tokens,
        "avg_cost_per_query": round(summary.avg_cost_per_query_usd, 6),
        "avg_latency_ms": round(summary.avg_latency_ms, 1),
        "by_agent": {k: round(v, 6) for k, v in summary.by_agent.items()},
        "by_model": {k: round(v, 6) for k, v in summary.by_model.items()},
    }


@router.get("/costs/daily")
async def get_daily_costs(days: int = 30):
    """Get daily cost breakdown."""
    daily = _cost_tracker.get_daily_costs(days=days)
    return {"daily": {k: round(v, 6) for k, v in daily.items()}}


@router.get("/costs/entries")
async def get_cost_entries(limit: int = 50):
    """Get recent cost entries."""
    entries = _cost_tracker._entries[-limit:]
    return {
        "entries": [
            {
                "timestamp": e.timestamp.isoformat(),
                "agent_id": e.agent_id,
                "model": e.model,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "cost_usd": round(e.estimated_cost_usd, 6),
                "latency_ms": e.latency_ms,
                "query": e.query[:100] if e.query else "",
            }
            for e in reversed(entries)
        ]
    }


@router.get("/costs/pricing")
async def get_pricing():
    """Get the current pricing table."""
    return {"pricing": DEFAULT_PRICING}


@router.delete("/costs")
async def clear_costs():
    """Clear all recorded cost entries."""
    _cost_tracker._entries.clear()
    return {"cleared": True}


# ── Tracing ──


@router.get("/traces")
async def get_traces():
    """Get all recorded traces."""
    traces = _tracer.export_json()
    return {"traces": traces, "count": len(traces)}


@router.delete("/traces")
async def clear_traces():
    """Clear all traces."""
    _tracer._spans.clear()
    return {"cleared": True}


# ── Prompt Versioning ──


@router.get("/prompts")
async def list_prompts():
    """List all prompt names."""
    names = _prompt_store.list_prompts()
    return {"prompts": names}


@router.get("/prompts/{name}")
async def get_prompt(name: str, version: int | None = None):
    """Get a specific prompt (latest or by version)."""
    try:
        pv = _prompt_store.get(name, version=version)
        return {
            "name": name,
            "version": pv.version,
            "content": pv.content,
            "metadata": pv.metadata,
            "tags": pv.tags,
            "created_at": pv.created_at.isoformat() if pv.created_at else None,
        }
    except KeyError as exc:
        return {"error": str(exc)}


@router.get("/prompts/{name}/versions")
async def list_prompt_versions(name: str):
    """List all versions of a prompt."""
    try:
        versions = _prompt_store.list_versions(name)
        return {
            "name": name,
            "versions": [
                {
                    "version": v.version,
                    "content": v.content[:100] + "..." if len(v.content) > 100 else v.content,
                    "tags": v.tags,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in versions
            ],
        }
    except KeyError:
        return {"name": name, "versions": []}


@router.post("/prompts")
async def save_prompt(body: PromptSaveBody):
    """Save a new version of a prompt."""
    pv = _prompt_store.save(
        name=body.name,
        content=body.content,
        metadata=body.metadata,
        tags=body.tags,
    )
    return {
        "name": body.name,
        "version": pv.version,
        "created_at": pv.created_at.isoformat() if pv.created_at else None,
    }


@router.post("/prompts/{name}/rollback")
async def rollback_prompt(name: str, version: int):
    """Rollback a prompt to a specific version."""
    try:
        pv = _prompt_store.rollback(name, version)
        return {"name": name, "version": pv.version, "content": pv.content}
    except (KeyError, IndexError) as exc:
        return {"error": str(exc)}


@router.post("/prompts/diff")
async def diff_prompts(body: PromptDiffBody):
    """Diff two versions of a prompt."""
    try:
        result = _prompt_store.diff(body.name, body.version_a, body.version_b)
        return result
    except (KeyError, IndexError) as exc:
        return {"error": str(exc)}


# ── Expose singletons for chat integration ──


def get_cost_tracker() -> CostTracker:
    """Get the shared CostTracker instance."""
    return _cost_tracker


def get_tracer() -> Tracer:
    """Get the shared Tracer instance."""
    return _tracer

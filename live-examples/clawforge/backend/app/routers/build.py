"""Build endpoints — streaming multi-agent pipeline."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.controllers import build as build_controller
from app.helpers import gateway
from app.models.build import BuildRequest

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/build", tags=["build"])


@router.post("/stream")
async def build_stream(body: BuildRequest):
    """Stream build execution via SSE."""
    log.info(
        "POST /api/build/stream project=%s mode=%s agent=%s",
        body.project_id[:8], body.mode, body.agent_id,
    )
    client = await gateway.get_client()
    return EventSourceResponse(
        build_controller.stream_build(
            client,
            body.project_id,
            mode=body.mode,
            agent_id=body.agent_id,
            max_steps=body.max_steps,
            max_cost_usd=body.max_cost_usd,
        )
    )

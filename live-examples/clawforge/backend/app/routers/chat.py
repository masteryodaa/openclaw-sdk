"""Chat endpoints — blocking and streaming."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.controllers import chat as chat_controller
from app.helpers import gateway
from app.models.chat import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(body: ChatRequest):
    """Send a message and wait for the full response."""
    client = await gateway.get_client()
    try:
        return await chat_controller.execute_chat(
            client,
            body.project_id,
            body.message,
            agent_id=body.agent_id,
            session_name=body.session_name,
            thinking=body.thinking,
            timeout_seconds=body.timeout_seconds,
        )
    except Exception as exc:
        gateway.reset()
        raise HTTPException(500, str(exc)) from exc


@router.post("/stream")
async def chat_stream(body: ChatRequest):
    """Stream chat via Server-Sent Events."""
    client = await gateway.get_client()
    return EventSourceResponse(
        chat_controller.stream_chat(
            client,
            body.project_id,
            body.message,
            agent_id=body.agent_id,
            session_name=body.session_name,
            thinking=body.thinking,
            timeout_seconds=body.timeout_seconds,
        )
    )

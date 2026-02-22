"""Chat endpoints — blocking and streaming."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.controllers import chat as chat_controller
from app.helpers import gateway
from app.models.chat import ChatRequest

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(body: ChatRequest):
    """Send a message and wait for the full response."""
    log.info(
        "POST /api/chat project=%s agent=%s msg_len=%d",
        body.project_id[:8], body.agent_id, len(body.message),
    )
    client = await gateway.get_client()
    try:
        result = await chat_controller.execute_chat(
            client,
            body.project_id,
            body.message,
            agent_id=body.agent_id,
            session_name=body.session_name,
            thinking=body.thinking,
            timeout_seconds=body.timeout_seconds,
        )
        log.info("POST /api/chat complete success=%s", result.get("success"))
        return result
    except Exception as exc:
        log.error("POST /api/chat error: %s", exc, exc_info=True)
        gateway.reset()
        raise HTTPException(500, str(exc)) from exc


@router.post("/stream")
async def chat_stream(body: ChatRequest):
    """Stream chat via Server-Sent Events."""
    log.info(
        "POST /api/chat/stream project=%s agent=%s msg_len=%d",
        body.project_id[:8], body.agent_id, len(body.message),
    )
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


@router.get("/session-status/{project_id}")
async def session_status(project_id: str, agent_id: str = "main"):
    """Poll the agent session for real-time tool activity."""
    log.debug("GET /api/chat/session-status/%s", project_id[:8])
    client = await gateway.get_client()
    session_key = f"agent:{agent_id}:clawforge-{project_id}"
    try:
        result = await client.gateway.call(
            "sessions.preview", {"keys": [session_key]}
        )
        previews = result.get("previews") or []
        if not previews:
            return {"items": [], "tools": [], "files": []}

        items = previews[0].get("items", [])
        # Extract tool calls and file writes
        tools = []
        files = []
        for item in items:
            if item.get("role") == "tool":
                text = item.get("text", "")
                if text.startswith("call "):
                    tool_name = text[5:].strip()
                    tools.append({"tool": tool_name, "phase": "call"})
                elif "wrote" in text.lower() and "bytes to" in text.lower():
                    # Parse: "Successfully wrote 10800 bytes to shoe-store/modern-landing.html"
                    import re
                    m = re.search(r"wrote\s+(\d+)\s+bytes\s+to\s+(.+)", text, re.I)
                    if m:
                        files.append({
                            "path": m.group(2).strip(),
                            "size": int(m.group(1)),
                        })
                    tools.append({"tool": "write", "phase": "result", "output": text})
                else:
                    tools.append({"tool": "unknown", "phase": "result", "output": text})

        return {"tools": tools, "files": files}
    except Exception as exc:
        log.warning("session-status error: %s", exc)
        return {"tools": [], "files": [], "error": str(exc)}

"""Chat endpoints — blocking and streaming."""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from openclaw_sdk import (
    AgentExecutionError,
    Attachment,
    EventType,
    ExecutionOptions,
    GatewayError,
)

from . import gateway

router = APIRouter(prefix="/api/chat", tags=["chat"])


class AttachmentBody(BaseModel):
    """Inline attachment — base64-encoded file content from the browser."""

    file_name: str
    mime_type: str
    content_base64: str


class ChatBody(BaseModel):
    agent_id: str
    message: str
    session_name: str = "main"
    thinking: bool = False
    timeout_seconds: int = 300
    deliver: bool | None = None
    attachments: list[AttachmentBody] = []


# ---- Blocking endpoint ----


@router.post("")
async def chat(body: ChatBody):
    """Send a message and wait for the full response."""
    client = await gateway.get_client()
    agent = client.get_agent(body.agent_id, body.session_name)

    sdk_attachments = _build_attachments(body.attachments)
    options = ExecutionOptions(
        thinking=body.thinking,
        timeout_seconds=body.timeout_seconds,
        deliver=body.deliver,
        attachments=sdk_attachments,
    )

    try:
        result = await agent.execute(body.message, options=options)
    except AgentExecutionError as exc:
        msg = str(exc)
        if "disconnect" in msg.lower() or "closed" in msg.lower():
            gateway.reset()
            msg = ("Gateway connection lost — the attachment may exceed the "
                   "gateway's WebSocket frame limit (~380 KB). "
                   "Try a smaller file or send without attachments.")
        raise HTTPException(500, msg) from exc
    except Exception as exc:
        gateway.reset()
        raise HTTPException(500, str(exc)) from exc

    content = result.content

    # If empty and no error_message, poll session for the actual response
    if not content and not result.error_message:
        content = await _poll_session_response(client, agent)

    return {
        "success": result.success and bool(content),
        "content": content or result.error_message or "(No response)",
        "thinking": result.thinking,
        "tool_calls": [t.model_dump() for t in result.tool_calls],
        "files": [f.model_dump() for f in result.files],
        "token_usage": result.token_usage.model_dump() if result.token_usage else None,
        "stop_reason": result.stop_reason,
        "error_message": result.error_message,
        "latency_ms": result.latency_ms,
    }


async def _poll_session_response(client, agent) -> str:
    """Try to read the last assistant message from session preview."""
    try:
        preview = await client.gateway.call(
            "sessions.preview", {"keys": [agent.session_key]}
        )
        items = (preview.get("previews") or [{}])[0].get("items", [])
        for item in reversed(items):
            if item.get("role") == "assistant":
                return item.get("text", "")
    except Exception:
        pass
    return ""


# ---- Streaming endpoint (SSE) ----


@router.post("/stream")
async def chat_stream(body: ChatBody):
    """Stream chat via Server-Sent Events."""
    client = await gateway.get_client()
    agent = client.get_agent(body.agent_id, body.session_name)

    sdk_attachments = _build_attachments(body.attachments)
    options = ExecutionOptions(
        thinking=body.thinking,
        timeout_seconds=body.timeout_seconds,
        deliver=body.deliver,
        attachments=sdk_attachments,
    )

    return EventSourceResponse(_stream_events(client, agent, body.message, options))


async def _stream_events(client, agent, message: str, options) -> AsyncIterator[dict[str, str]]:
    """Yield SSE dicts from gateway push events."""
    try:
        params = agent._build_send_params(message, options, None)
        subscriber = await client.gateway.subscribe(
            event_types=["agent", "chat", "content", "done", "error",
                         "thinking", "tool_call", "tool_result", "file_generated"]
        )
        send_result = await client.gateway.call("chat.send", params)
        run_id = send_result.get("runId", "")
        got_content = False

        yield {"event": "run_start", "data": json.dumps({"runId": run_id})}

        async for event in subscriber:
            payload = event.data.get("payload") or {}
            # Skip events from other runs
            eid = payload.get("runId", "")
            if run_id and eid and eid != run_id:
                continue

            sse = _map_event(event.event_type, payload)
            if sse is None:
                continue

            if sse["event"] == "content":
                got_content = True

            yield sse
            if sse["event"] in ("done", "error"):
                break

        # If we got a "done" but no content was streamed, check for errors
        if not got_content:
            content = await _poll_session_response(client, agent)
            if content:
                yield {"event": "content", "data": json.dumps({"text": content})}
            else:
                yield {"event": "error", "data": json.dumps({
                    "message": "Agent completed with no response — "
                               "the LLM may be rate-limited or unavailable"
                })}

    except GatewayError as exc:
        gateway.reset()  # force reconnect on next request
        msg = str(exc)
        if "disconnect" in msg.lower() or "closed" in msg.lower():
            msg = ("Gateway connection lost — the attachment may exceed the "
                   "gateway's WebSocket frame limit (~380 KB). "
                   "Try a smaller file or send without attachments.")
        yield {"event": "error", "data": json.dumps({"message": msg})}
    except Exception as exc:
        gateway.reset()  # force reconnect on next request
        msg = str(exc)
        if "disconnect" in msg.lower() or "closed" in msg.lower():
            msg = ("Gateway connection lost — the attachment may exceed the "
                   "gateway's WebSocket frame limit (~380 KB). "
                   "Try a smaller file or send without attachments.")
        yield {"event": "error", "data": json.dumps({"message": msg})}


def _map_event(event_type: EventType, payload: dict) -> dict[str, str] | None:
    """Map a gateway event to an SSE dict, or None to skip."""

    # Real gateway: "chat" events — used for final/error/aborted states only.
    # Content deltas come via "agent" events to avoid duplication.
    if event_type == EventType.CHAT:
        state = payload.get("state", "")
        msg = payload.get("message") or {}

        if state == "delta":
            # Skip — content is already streamed via "agent" events.
            # Using chat deltas too would duplicate every chunk.
            return None

        if state == "final":
            # Detect empty final (LLM error not propagated by gateway)
            if "message" not in payload:
                return {"event": "error", "data": json.dumps({
                    "message": "Agent completed with no response — "
                               "the LLM may be rate-limited or unavailable"
                })}
            usage = msg.get("usage") or msg.get("tokenUsage") or {}
            return {"event": "done", "data": json.dumps({
                "stopReason": msg.get("stopReason", "complete"),
                "usage": usage,
            })}

        if state == "error":
            return _sse("error", message=msg.get("error") or "Agent error")

        if state == "aborted":
            return {"event": "done", "data": json.dumps({"stopReason": "aborted"})}

    # Real gateway: "agent" stream events — primary source of streaming data
    if event_type == EventType.AGENT:
        stream = payload.get("stream", "")
        data = payload.get("data") or {}

        if stream == "assistant":
            delta = data.get("delta") or data.get("text") or ""
            return _sse("content", text=delta) if delta else None

        if stream == "thinking":
            t = data.get("text") or data.get("delta") or ""
            return _sse("thinking", text=t) if t else None

        if stream == "tool":
            phase = data.get("phase", "")
            if phase == "call":
                return {"event": "tool_call", "data": json.dumps({
                    "tool": data.get("tool") or data.get("name") or "",
                    "input": data.get("input") or "",
                })}
            if phase == "result":
                return {"event": "tool_result", "data": json.dumps({
                    "output": data.get("output") or data.get("result") or "",
                })}

        if stream == "file":
            return {"event": "file_generated", "data": json.dumps({
                "name": data.get("name") or data.get("fileName") or "",
                "path": data.get("path") or "",
                "size": data.get("sizeBytes") or data.get("size") or 0,
                "mimeType": data.get("mimeType") or "",
            })}

    # MockGateway / SDK-level events
    if event_type == EventType.CONTENT:
        text = payload.get("content") or payload.get("text") or ""
        return _sse("content", text=text) if text else None

    if event_type == EventType.THINKING:
        text = payload.get("thinking") or payload.get("content") or ""
        return _sse("thinking", text=text) if text else None

    if event_type == EventType.DONE:
        usage = payload.get("usage") or payload.get("tokenUsage") or {}
        return {"event": "done", "data": json.dumps({
            "stopReason": payload.get("stopReason", "complete"),
            "usage": usage,
        })}

    if event_type == EventType.ERROR:
        return _sse("error", message=payload.get("message") or "Error")

    return None


def _sse(event: str, **kw) -> dict[str, str]:
    return {"event": event, "data": json.dumps(kw)}


def _build_attachments(items: list[AttachmentBody]) -> list[Attachment]:
    """Convert browser-supplied inline attachments to SDK Attachment objects."""
    result: list[Attachment] = []
    for att in items:
        result.append(Attachment(
            file_path=att.file_name,
            mime_type=att.mime_type,
            name=att.file_name,
            content_base64=att.content_base64,
        ))
    return result

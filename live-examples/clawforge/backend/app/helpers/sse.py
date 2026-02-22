"""SSE event mapping helpers for gateway -> browser streaming."""

from __future__ import annotations

import json

from openclaw_sdk import EventType


def map_event(event_type: EventType, payload: dict) -> dict[str, str] | None:
    """Map a gateway event to an SSE dict, or None to skip."""

    if event_type == EventType.CHAT:
        state = payload.get("state", "")
        msg = payload.get("message") or {}

        if state == "delta":
            return None

        if state == "final":
            if "message" not in payload:
                return _sse("error", message="Agent completed with no response")
            usage = msg.get("usage") or msg.get("tokenUsage") or {}
            return {"event": "done", "data": json.dumps({
                "stopReason": msg.get("stopReason", "complete"),
                "usage": usage,
            })}

        if state == "error":
            return _sse("error", message=msg.get("error") or "Agent error")

        if state == "aborted":
            return {"event": "done", "data": json.dumps({"stopReason": "aborted"})}

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


def _sse(event: str, **kw: object) -> dict[str, str]:
    return {"event": event, "data": json.dumps(kw)}

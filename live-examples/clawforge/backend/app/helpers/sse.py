"""SSE event mapping helpers for gateway -> browser streaming."""

from __future__ import annotations

import json
import logging

from openclaw_sdk import EventType

log = logging.getLogger(__name__)


def map_event(event_type: EventType, payload: dict) -> dict[str, str] | None:
    """Map a gateway event to an SSE dict, or None to skip."""

    if event_type == EventType.CHAT:
        state = payload.get("state", "")
        msg = payload.get("message") or {}

        if state == "delta":
            return None

        if state == "final":
            if "message" not in payload:
                log.warning("CHAT final with no message payload")
                return _sse("error", message="Agent completed with no response")
            usage = msg.get("usage") or msg.get("tokenUsage") or {}
            log.debug("CHAT final stopReason=%s", msg.get("stopReason", "complete"))
            return {"event": "done", "data": json.dumps({
                "stopReason": msg.get("stopReason", "complete"),
                "usage": usage,
            })}

        if state == "error":
            log.error("CHAT error: %s", msg.get("error") or "Agent error")
            return _sse("error", message=msg.get("error") or "Agent error")

        if state == "aborted":
            log.warning("CHAT aborted")
            return {"event": "done", "data": json.dumps({"stopReason": "aborted"})}

    if event_type == EventType.AGENT:
        stream = payload.get("stream", "")
        data = payload.get("data") or {}

        if stream == "assistant":
            delta = data.get("delta") or data.get("text") or ""
            if delta:
                log.debug("AGENT assistant delta len=%d", len(delta))
            return _sse("content", text=delta) if delta else None

        if stream == "thinking":
            t = data.get("text") or data.get("delta") or ""
            if t:
                log.debug("AGENT thinking delta len=%d", len(t))
            return _sse("thinking", text=t) if t else None

        if stream == "tool":
            phase = data.get("phase", "")
            if phase == "call":
                tool_name = data.get("tool") or data.get("name") or ""
                log.info("AGENT tool_call tool=%s", tool_name)
                return {"event": "tool_call", "data": json.dumps({
                    "tool": tool_name,
                    "input": data.get("input") or "",
                })}
            if phase == "result":
                log.debug("AGENT tool_result received")
                return {"event": "tool_result", "data": json.dumps({
                    "output": data.get("output") or data.get("result") or "",
                })}

        if stream == "file":
            fname = data.get("name") or data.get("fileName") or ""
            log.info("AGENT file_generated name=%s", fname)
            return {"event": "file_generated", "data": json.dumps({
                "name": fname,
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
        log.info("DONE event stopReason=%s", payload.get("stopReason", "complete"))
        usage = payload.get("usage") or payload.get("tokenUsage") or {}
        return {"event": "done", "data": json.dumps({
            "stopReason": payload.get("stopReason", "complete"),
            "usage": usage,
        })}

    if event_type == EventType.ERROR:
        log.error("ERROR event: %s", payload.get("message") or "Error")
        return _sse("error", message=payload.get("message") or "Error")

    log.debug("Unmapped event_type=%s (skipped)", event_type)
    return None


def _sse(event: str, **kw: object) -> dict[str, str]:
    return {"event": event, "data": json.dumps(kw)}

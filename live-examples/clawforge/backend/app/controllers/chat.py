"""Chat controller — agent execution with guardrails and streaming."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from openclaw_sdk import (
    AgentExecutionError,
    ExecutionOptions,
    GatewayError,
    OpenClawClient,
)

from app.helpers import database, gateway
from app.helpers.sse import map_event

log = logging.getLogger(__name__)


async def execute_chat(
    client: OpenClawClient,
    project_id: str,
    message: str,
    agent_id: str = "main",
    session_name: str | None = None,
    thinking: bool = False,
    timeout_seconds: int = 300,
) -> dict:
    """Execute a chat message and return the full response."""
    log.info(
        "execute_chat project=%s agent=%s thinking=%s msg_len=%d",
        project_id[:8], agent_id, thinking, len(message),
    )
    # Save user message
    await database.add_message(project_id, "user", message)

    sess = session_name or f"clawforge-{project_id}"
    agent = client.get_agent(agent_id, sess)
    log.debug("Agent session_key=%s", agent.session_key)
    options = ExecutionOptions(
        thinking=thinking,
        timeout_seconds=timeout_seconds,
    )

    try:
        log.info("Executing agent.execute()...")
        result = await agent.execute(message, options=options)
        log.info(
            "agent.execute() done success=%s latency=%sms stop=%s",
            result.success, result.latency_ms, result.stop_reason,
        )
    except AgentExecutionError as exc:
        msg = str(exc)
        log.error("AgentExecutionError: %s", msg)
        if "disconnect" in msg.lower() or "closed" in msg.lower():
            gateway.reset()
        raise

    content = result.content
    if not content and not result.error_message:
        log.warning("Empty content — polling session preview for response")
        # Try polling session for actual response
        try:
            preview = await client.gateway.call(
                "sessions.preview", {"keys": [agent.session_key]}
            )
            items = (preview.get("previews") or [{}])[0].get("items", [])
            for item in reversed(items):
                if item.get("role") == "assistant":
                    content = item.get("text", "")
                    log.info("Recovered content from session preview len=%d", len(content))
                    break
        except Exception as exc:
            log.warning("Session preview fallback failed: %s", exc)

    # Save assistant response
    token_usage = result.token_usage.model_dump() if result.token_usage else None
    tool_calls = (
        [t.model_dump() for t in result.tool_calls] if result.tool_calls else None
    )
    files = [f.model_dump() for f in result.files] if result.files else None

    log.debug(
        "Saving assistant response len=%d tool_calls=%d files=%d",
        len(content or ""), len(tool_calls or []), len(files or []),
    )
    saved = await database.add_message(
        project_id,
        "assistant",
        content or result.error_message or "(No response)",
        thinking=result.thinking,
        tool_calls=tool_calls,
        files=files,
        token_usage=token_usage,
    )

    # Update project cost
    if token_usage:
        total_tokens = token_usage.get("total_tokens", 0) or token_usage.get(
            "totalTokens", 0
        )
        if total_tokens:
            log.debug("Updating project cost: +%d tokens", total_tokens)
            project = await database.get_project(project_id)
            if project:
                await database.update_project(
                    project_id,
                    total_tokens=project["total_tokens"] + total_tokens,
                )

    log.info("execute_chat complete project=%s success=%s", project_id[:8], result.success)
    return {
        "success": result.success and bool(content),
        "content": content or result.error_message or "(No response)",
        "thinking": result.thinking,
        "tool_calls": tool_calls or [],
        "files": files or [],
        "token_usage": token_usage,
        "stop_reason": result.stop_reason,
        "error_message": result.error_message,
        "latency_ms": result.latency_ms,
        "message_id": saved["id"],
    }


async def stream_chat(
    client: OpenClawClient,
    project_id: str,
    message: str,
    agent_id: str = "main",
    session_name: str | None = None,
    thinking: bool = False,
    timeout_seconds: int = 300,
) -> AsyncIterator[dict[str, str]]:
    """Stream chat via SSE — yields event dicts for EventSourceResponse."""
    log.info(
        "stream_chat project=%s agent=%s thinking=%s msg_len=%d",
        project_id[:8], agent_id, thinking, len(message),
    )
    # Save user message
    await database.add_message(project_id, "user", message)

    sess = session_name or f"clawforge-{project_id}"
    agent = client.get_agent(agent_id, sess)
    log.debug("Agent session_key=%s", agent.session_key)
    options = ExecutionOptions(
        thinking=thinking,
        timeout_seconds=timeout_seconds,
    )

    try:
        params = agent._build_send_params(message, options, None)
        log.debug("Subscribing to event types...")
        subscriber = await client.gateway.subscribe(
            event_types=[
                "agent",
                "chat",
                "content",
                "done",
                "error",
                "thinking",
                "tool_call",
                "tool_result",
                "file_generated",
            ]
        )
        log.info("Sending chat.send...")
        send_result = await client.gateway.call("chat.send", params)
        run_id = send_result.get("runId", "")
        log.info("chat.send returned runId=%s", run_id)
        full_content = ""
        full_thinking = ""

        yield {"event": "run_start", "data": json.dumps({"runId": run_id})}

        event_count = 0
        async for event in subscriber:
            payload = event.data.get("payload") or {}
            eid = payload.get("runId", "")
            if run_id and eid and eid != run_id:
                continue

            sse = map_event(event.event_type, payload)
            if sse is None:
                continue

            event_count += 1

            # Accumulate content for saving
            if sse["event"] == "content":
                data = json.loads(sse["data"])
                full_content += data.get("text", "")
            elif sse["event"] == "thinking":
                data = json.loads(sse["data"])
                full_thinking += data.get("text", "")

            yield sse

            if sse["event"] in ("done", "error"):
                log.info(
                    "Stream ended event=%s total_events=%d content_len=%d",
                    sse["event"], event_count, len(full_content),
                )
                break

        # Save assistant response after stream completes
        if full_content:
            log.debug("Saving streamed response len=%d", len(full_content))
            await database.add_message(
                project_id,
                "assistant",
                full_content,
                thinking=full_thinking or None,
            )

    except (GatewayError, Exception) as exc:
        log.error("stream_chat error: %s", exc, exc_info=True)
        gateway.reset()
        msg = str(exc)
        if "disconnect" in msg.lower() or "closed" in msg.lower():
            msg = "Gateway connection lost — try again."
        yield {"event": "error", "data": json.dumps({"message": msg})}

# RUN: python examples/09_callbacks.py
"""Callbacks — custom AuditCallbackHandler + LoggingCallbackHandler via CompositeCallbackHandler."""

import asyncio
from dataclasses import dataclass
from typing import Any

from openclaw_sdk import OpenClawClient, ClientConfig, EventType
from openclaw_sdk.callbacks.handler import (
    CallbackHandler,
    CompositeCallbackHandler,
    LoggingCallbackHandler,
)
from openclaw_sdk.core.types import ExecutionResult, StreamEvent, GeneratedFile, TokenUsage
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# Custom audit callback
# ---------------------------------------------------------------------------

@dataclass
class AuditEvent:
    event: str
    agent_id: str
    detail: Any = None


class AuditCallbackHandler(CallbackHandler):
    """Records every callback event to an in-memory audit log."""

    def __init__(self) -> None:
        self.log: list[AuditEvent] = []

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        self.log.append(AuditEvent("execution_start", agent_id, {"query": query}))

    async def on_llm_start(self, agent_id: str, prompt: str, model: str) -> None:
        self.log.append(AuditEvent("llm_start", agent_id, {"model": model}))

    async def on_llm_end(
        self, agent_id: str, response: str, token_usage: TokenUsage, duration_ms: int
    ) -> None:
        self.log.append(
            AuditEvent(
                "llm_end",
                agent_id,
                {"tokens_in": token_usage.input, "tokens_out": token_usage.output},
            )
        )

    async def on_tool_call(self, agent_id: str, tool_name: str, tool_input: str) -> None:
        self.log.append(AuditEvent("tool_call", agent_id, {"tool": tool_name}))

    async def on_tool_result(
        self, agent_id: str, tool_name: str, result: str, duration_ms: int
    ) -> None:
        self.log.append(AuditEvent("tool_result", agent_id, {"tool": tool_name}))

    async def on_file_generated(self, agent_id: str, file: GeneratedFile) -> None:
        self.log.append(AuditEvent("file_generated", agent_id, {"file": file.name}))

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        self.log.append(
            AuditEvent("execution_end", agent_id, {"success": result.success})
        )

    async def on_error(self, agent_id: str, error: Exception) -> None:
        self.log.append(AuditEvent("error", agent_id, {"error": str(error)}))

    async def on_stream_event(self, agent_id: str, event: StreamEvent) -> None:
        self.log.append(AuditEvent("stream_event", agent_id, {"type": event.event_type}))


async def main() -> None:
    mock = MockGateway()
    await mock.connect()

    mock.register("chat.send", {"runId": "r1", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r1", "content": "Audit trail captured!"}},
        )
    )

    # Compose audit handler + logging handler
    audit = AuditCallbackHandler()
    composite = CompositeCallbackHandler([audit, LoggingCallbackHandler()])

    client = OpenClawClient(config=ClientConfig(), gateway=mock, callbacks=[composite])
    agent = client.get_agent("audited-agent")

    result = await agent.execute("Perform an audited action")

    print(f"Result: {result.content}\n")
    print("Audit log:")
    for i, entry in enumerate(audit.log, 1):
        print(f"  {i:2}. [{entry.event:18s}] agent={entry.agent_id}  detail={entry.detail}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

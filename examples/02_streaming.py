# RUN: python examples/02_streaming.py
"""Streaming — use execute_stream to receive incremental events from the agent."""

import asyncio

from openclaw_sdk import OpenClawClient, ClientConfig, EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway


async def main() -> None:
    # 1. Set up MockGateway with streaming events
    mock = MockGateway()
    await mock.connect()

    mock.register("chat.send", {"runId": "r1", "status": "started"})

    # Pre-emit 3 CONTENT chunks followed by a DONE event
    chunks = ["Once upon a time ", "in a land far away, ", "an agent learned to stream."]
    for chunk in chunks:
        mock.emit_event(
            StreamEvent(
                event_type=EventType.CONTENT,
                data={"payload": {"runId": "r1", "content": chunk}},
            )
        )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r1"}},
        )
    )

    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = client.get_agent("storyteller")

    print("Streaming response:")
    print("-" * 40)

    # execute_stream returns an async iterator of StreamEvent objects
    stream = await agent.execute_stream("write a story")
    async for event in stream:
        if event.event_type == EventType.CONTENT:
            chunk = event.data.get("payload", {}).get("content", "")
            print(chunk, end="", flush=True)
        elif event.event_type == EventType.DONE:
            print("\n" + "-" * 40)
            print("Stream complete.")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

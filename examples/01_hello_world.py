# RUN: python examples/01_hello_world.py
"""Hello World — connect via MockGateway, get an agent, execute a query."""

import asyncio

from openclaw_sdk import OpenClawClient, ClientConfig, EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway


async def main() -> None:
    # 1. Create and connect a MockGateway
    mock = MockGateway()
    await mock.connect()

    # 2. Register the gateway method the agent will call
    mock.register("chat.send", {"runId": "r1", "status": "started"})

    # 3. Pre-emit the DONE event that the agent will wait for
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r1", "content": "Hello from OpenClaw!"}},
        )
    )

    # 4. Build the client directly (no live OpenClaw needed)
    client = OpenClawClient(config=ClientConfig(), gateway=mock)

    # 5. Get an agent and execute a query
    agent = client.get_agent("greeter")
    result = await agent.execute("Say hello")

    print(f"Success : {result.success}")
    print(f"Content : {result.content}")
    print(f"Latency : {result.latency_ms} ms")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

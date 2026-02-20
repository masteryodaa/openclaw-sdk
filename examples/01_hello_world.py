# RUN: python examples/01_hello_world.py
"""Hello World — connect via MockGateway, get an agent, execute a query.

Demonstrates: basic connection, agent.execute(), agent.get_status(),
client.list_agents(), and client.create_agent().
"""

import asyncio

from openclaw_sdk import OpenClawClient, ClientConfig, AgentConfig, EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway


async def main() -> None:
    # 1. Create and connect a MockGateway
    mock = MockGateway()
    await mock.connect()

    # 2. Register mock responses for agent operations
    mock.register("chat.send", {"runId": "r1", "status": "started"})
    mock.register("sessions.resolve", {"status": "idle"})
    mock.register("sessions.list", {
        "count": 1,
        "sessions": [{"key": "agent:greeter:main", "status": "idle"}],
    })
    mock.register("config.get", {"raw": "{}", "exists": True, "path": "/mock"})
    mock.register("config.set", {"ok": True})

    # 3. Pre-emit the DONE event that the agent will wait for
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r1", "content": "Hello from OpenClaw!"}},
        )
    )

    # 4. Build the client directly (no live OpenClaw needed)
    client = OpenClawClient(config=ClientConfig(), gateway=mock)

    # 5. Create an agent via the client (writes to gateway config)
    agent = await client.create_agent(AgentConfig(
        agent_id="greeter",
        system_prompt="You are a friendly greeter.",
    ))

    # 6. Check agent status before executing
    status = await agent.get_status()
    print(f"Agent status: {status}")

    # 7. List all known agents
    agents = await client.list_agents()
    print(f"Known agents: {[a.agent_id for a in agents]}")

    # 8. Execute a query
    result = await agent.execute("Say hello")
    print(f"\nSuccess : {result.success}")
    print(f"Content : {result.content}")
    print(f"Latency : {result.latency_ms} ms")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

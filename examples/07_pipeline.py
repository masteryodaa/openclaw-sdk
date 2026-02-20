# RUN: python examples/07_pipeline.py
"""Pipeline — chain three agents: researcher -> writer -> reviewer."""

import asyncio

from openclaw_sdk import OpenClawClient, ClientConfig, EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.pipeline.pipeline import Pipeline


def _done(content: str) -> StreamEvent:
    return StreamEvent(
        event_type=EventType.DONE,
        data={"payload": {"runId": "run1", "content": content}},
    )


async def main() -> None:
    mock = MockGateway()
    await mock.connect()

    # Register chat.send — returns the same runId for every call
    mock.register("chat.send", {"runId": "run1", "status": "started"})

    # Pre-emit all three DONE events upfront.
    # Each agent.execute() call subscribes and drains one DONE event in order.
    mock.emit_event(_done(
        "AI in 2025: models reached AGI-level reasoning, "
        "multimodal capabilities surged, inference costs dropped 10x."
    ))
    mock.emit_event(_done(
        "The Year AI Grew Up: In 2025 artificial intelligence "
        "transformed from a tool into a collaborator."
    ))
    mock.emit_event(_done(
        "Review: Compelling article. Strong thesis, clear structure. "
        "Recommend publication with minor edits."
    ))

    client = OpenClawClient(config=ClientConfig(), gateway=mock)

    pipeline = (
        Pipeline(client)
        .add_step("research", "researcher", "Research this topic: {topic}")
        .add_step("write",    "writer",     "Write an article about: {research}")
        .add_step("review",   "reviewer",   "Review this article: {write}")
    )

    print("Running pipeline: researcher -> writer -> reviewer")
    print("Topic: AI in 2025\n")

    result = await pipeline.run(topic="AI in 2025")

    print(f"Pipeline success : {result.success}")
    print(f"Total latency    : {result.total_latency_ms} ms")
    print(f"Steps completed  : {list(result.steps.keys())}\n")

    for step_name, step_result in result.steps.items():
        print(f"[{step_name}]")
        print(f"  {step_result.content}\n")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

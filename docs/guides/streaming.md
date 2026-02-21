# Streaming

Streaming lets you receive agent output incrementally as it is generated, rather than waiting for the entire response. This is essential for building responsive UIs, CLI tools, and any application where perceived latency matters.

## How Streaming Works

Call `agent.execute_stream()` instead of `agent.execute()`. It returns an async iterator that yields `StreamEvent` objects as the agent produces output. Each event has an `event_type` (an `EventType` enum value) and a `data` dictionary with the event payload.

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        async for event in agent.execute_stream("Write a short poem about the sea"):
            print(f"[{event.event_type}] {event.data}")

asyncio.run(main())
```

## Event Types

The `EventType` enum defines all possible events you can receive during streaming:

| Event Type | Description | Key `data` Fields |
|---|---|---|
| `CONTENT` | A chunk of the agent's text response | `text` |
| `THINKING` | A chunk of the agent's chain-of-thought reasoning | `text` |
| `TOOL_CALL` | The agent is invoking a tool | `name`, `input` |
| `TOOL_RESULT` | A tool has returned its result | `name`, `output`, `duration_ms` |
| `FILE_GENERATED` | The agent produced a file | `path`, `mime_type` |
| `DONE` | Execution is complete | `result` (full `ExecutionResult`) |
| `ERROR` | An error occurred | `error`, `message` |

!!! note
    The `DONE` event always arrives last and contains the complete `ExecutionResult`, identical to what `execute()` would have returned. You can use it to get final token counts and metadata.

## Processing Events

A typical pattern is to switch on `event_type` and handle each case:

```python
import asyncio
from openclaw_sdk import OpenClawClient, EventType

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        async for event in agent.execute_stream("Explain quantum entanglement"):
            match event.event_type:
                case EventType.CONTENT:
                    print(event.data["text"], end="", flush=True)

                case EventType.THINKING:
                    pass  # Optionally display reasoning

                case EventType.TOOL_CALL:
                    print(f"\n> Calling tool: {event.data['name']}")

                case EventType.TOOL_RESULT:
                    duration = event.data.get("duration_ms", 0)
                    print(f"> Tool returned in {duration:.0f}ms")

                case EventType.FILE_GENERATED:
                    print(f"\n> File generated: {event.data['path']}")

                case EventType.DONE:
                    result = event.data["result"]
                    print(f"\n\nDone. Tokens: {result.token_usage.total}")

                case EventType.ERROR:
                    print(f"\nError: {event.data['message']}")

        print()  # Final newline

asyncio.run(main())
```

## Building a Real-Time CLI

Here is a complete example that streams agent output to the terminal with visual indicators for tool calls and thinking:

```python
import asyncio
import sys
from openclaw_sdk import OpenClawClient, ExecutionOptions, EventType

async def cli_chat():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent", session_name="cli-session")

        while True:
            query = input("\nYou: ").strip()
            if not query or query.lower() in ("exit", "quit"):
                break

            print("Agent: ", end="", flush=True)
            token_total = 0

            async for event in agent.execute_stream(query):
                match event.event_type:
                    case EventType.CONTENT:
                        sys.stdout.write(event.data["text"])
                        sys.stdout.flush()

                    case EventType.THINKING:
                        sys.stdout.write(f"\033[2m{event.data['text']}\033[0m")
                        sys.stdout.flush()

                    case EventType.TOOL_CALL:
                        name = event.data["name"]
                        sys.stdout.write(f"\n  [{name}] ")
                        sys.stdout.flush()

                    case EventType.TOOL_RESULT:
                        duration = event.data.get("duration_ms", 0)
                        sys.stdout.write(f"done ({duration:.0f}ms)\n")
                        sys.stdout.flush()

                    case EventType.DONE:
                        result = event.data["result"]
                        token_total = result.token_usage.total

                    case EventType.ERROR:
                        print(f"\nError: {event.data['message']}")

            print(f"\n  [{token_total} tokens]")

asyncio.run(cli_chat())
```

## Streaming with Options

You can pass `ExecutionOptions` to `execute_stream()` just like you would to `execute()`. This lets you enable thinking mode, set timeouts, and attach images — all while streaming.

```python
import asyncio
from openclaw_sdk import OpenClawClient, ExecutionOptions, Attachment, EventType

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        options = ExecutionOptions(
            timeout_seconds=60,
            thinking=True,
            attachments=[Attachment.from_path("diagram.png")],
        )

        thinking_chunks = []
        content_chunks = []

        async for event in agent.execute_stream(
            "Analyze this architecture diagram and suggest improvements",
            options=options,
        ):
            match event.event_type:
                case EventType.THINKING:
                    thinking_chunks.append(event.data["text"])
                case EventType.CONTENT:
                    content_chunks.append(event.data["text"])
                    print(event.data["text"], end="", flush=True)
                case EventType.DONE:
                    pass

        print("\n")
        print(f"Thinking ({len(thinking_chunks)} chunks):")
        print("".join(thinking_chunks)[:200] + "...")

asyncio.run(main())
```

!!! tip
    When `thinking=True`, you will receive `THINKING` events before `CONTENT` events. The thinking text shows the agent's reasoning process and can be useful for debugging or transparency features.

## Error Handling

Errors during streaming are delivered as `ERROR` events. The stream will end after an error event (no `DONE` event follows). Always handle the error case to avoid silently dropping failures.

```python
import asyncio
from openclaw_sdk import OpenClawClient, EventType

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        try:
            async for event in agent.execute_stream("Do something"):
                if event.event_type == EventType.ERROR:
                    raise RuntimeError(
                        f"Agent error: {event.data.get('message', 'unknown')}"
                    )
                if event.event_type == EventType.CONTENT:
                    print(event.data["text"], end="")
        except RuntimeError as e:
            print(f"\nFailed: {e}")

asyncio.run(main())
```

!!! warning
    Always consume the entire stream. Breaking out of the `async for` loop early without proper cleanup may leave the underlying WebSocket subscription in an inconsistent state.

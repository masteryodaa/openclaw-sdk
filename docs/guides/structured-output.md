# Structured Output

Structured output lets you parse an agent's free-form text response into a typed Pydantic model. Instead of manually extracting data from natural language, you define a schema and the SDK handles prompting the agent for JSON, parsing the response, and retrying on failure.

## How It Works

Under the hood, `StructuredOutput` does three things:

1. **Schema injection** — Appends the Pydantic model's JSON schema to your query, instructing the agent to respond with valid JSON.
2. **Parsing** — Extracts JSON from the agent's response and validates it against your model.
3. **Retry** — If parsing fails (malformed JSON, missing fields), it re-sends the query with the error message, giving the agent a chance to correct its output. This repeats up to `max_retries` times.

## Basic Usage

Define a Pydantic model, then call `agent.execute_structured()`:

```python
import asyncio
from pydantic import BaseModel
from openclaw_sdk import OpenClawClient

class Sentiment(BaseModel):
    label: str       # "positive", "negative", or "neutral"
    confidence: float # 0.0 to 1.0
    reasoning: str

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        result = await agent.execute_structured(
            "Analyze the sentiment of: 'This product exceeded my expectations!'",
            Sentiment,
        )

        print(f"Label: {result.label}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Reasoning: {result.reasoning}")

asyncio.run(main())
```

!!! tip
    `agent.execute_structured(query, Model)` is a shorthand for `StructuredOutput.execute(agent, query, Model)`. Both are equivalent.

## Using StructuredOutput Directly

For more control, use the `StructuredOutput` class directly. This lets you set `max_retries` and is useful when you do not have an `Agent` instance but do have an agent-like object.

```python
import asyncio
from pydantic import BaseModel
from openclaw_sdk import OpenClawClient
from openclaw_sdk.output.structured import StructuredOutput

class ExtractedEntity(BaseModel):
    name: str
    entity_type: str  # "person", "org", "location"
    context: str

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        entity = await StructuredOutput.execute(
            agent,
            "Extract the main entity from: 'Tim Cook announced new products at Apple Park.'",
            ExtractedEntity,
            max_retries=3,
        )

        print(f"{entity.name} ({entity.entity_type}): {entity.context}")

asyncio.run(main())
```

## Complex Nested Models

Pydantic models can be arbitrarily nested. The JSON schema sent to the agent reflects the full structure, and the SDK validates all nested fields on parsing.

```python
import asyncio
from pydantic import BaseModel, Field
from openclaw_sdk import OpenClawClient

class Address(BaseModel):
    street: str
    city: str
    country: str
    postal_code: str

class ContactInfo(BaseModel):
    email: str
    phone: str | None = None

class CompanyProfile(BaseModel):
    name: str
    industry: str
    founded_year: int = Field(ge=1800, le=2030)
    headquarters: Address
    contacts: list[ContactInfo]
    key_products: list[str]
    employee_count: int | None = None

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        profile = await agent.execute_structured(
            "Create a company profile for Anthropic.",
            CompanyProfile,
        )

        print(f"Company: {profile.name}")
        print(f"Industry: {profile.industry}")
        print(f"HQ: {profile.headquarters.city}, {profile.headquarters.country}")
        print(f"Products: {', '.join(profile.key_products)}")
        for contact in profile.contacts:
            print(f"Contact: {contact.email}")

asyncio.run(main())
```

## Lists and Enums

You can use `list` types and Python enums to constrain agent output:

```python
import asyncio
from enum import Enum
from pydantic import BaseModel
from openclaw_sdk import OpenClawClient

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionItem(BaseModel):
    title: str
    assignee: str
    priority: Priority
    due_date: str  # ISO 8601

class MeetingNotes(BaseModel):
    summary: str
    action_items: list[ActionItem]
    attendees: list[str]
    next_meeting: str | None = None

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        notes = await agent.execute_structured(
            "Parse these meeting notes: 'Alice and Bob discussed the Q4 launch. "
            "Alice will finalize the spec by Friday (high priority). "
            "Bob will update the dashboard by next Wednesday (medium priority). "
            "Next sync is Monday at 2pm.'",
            MeetingNotes,
        )

        print(f"Summary: {notes.summary}")
        for item in notes.action_items:
            print(f"  [{item.priority.value}] {item.title} -> {item.assignee} (due {item.due_date})")

asyncio.run(main())
```

## Error Handling

When the agent's response cannot be parsed into the target model after all retries are exhausted, an `OutputParsingError` is raised. Always handle this in production code.

```python
import asyncio
from pydantic import BaseModel
from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.exceptions import OutputParsingError

class StrictData(BaseModel):
    value: int
    unit: str

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("my-agent")

        try:
            data = await agent.execute_structured(
                "What is the speed of light?",
                StrictData,
            )
            print(f"{data.value} {data.unit}")
        except OutputParsingError as e:
            print(f"Failed to parse structured output: {e}")
            print(f"Raw response: {e.raw_content}")

asyncio.run(main())
```

!!! warning
    Structured output relies on the agent following the JSON schema instructions. Agents with weaker models or heavily constrained system prompts may fail more often. Increase `max_retries` if you see frequent parsing failures.

!!! note
    The default `max_retries` is 2, meaning the SDK will attempt up to 3 total calls (1 initial + 2 retries). Each retry includes the previous error in the prompt to help the agent self-correct.

## Best Practices

- **Keep models focused.** Smaller, well-documented models parse more reliably than large, deeply nested ones.
- **Use `Field(description=...)`.** The description is included in the JSON schema sent to the agent, which improves accuracy.
- **Set sensible defaults.** Use `Optional` fields with defaults for data the agent might not always provide.
- **Validate with Pydantic constraints.** Use `Field(ge=, le=, min_length=, max_length=)` to catch bad values at parse time rather than downstream.

# RUN: python examples/08_structured_output.py
"""Structured output — parse agent response into a typed Pydantic model.

Demonstrates: agent.execute_structured() (MD7 method), StructuredOutput.parse(),
and StructuredOutput.schema_prompt().
"""

import asyncio

from pydantic import BaseModel

from openclaw_sdk import OpenClawClient, ClientConfig, EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.output.structured import StructuredOutput


# ---------------------------------------------------------------------------
# Define the output schema
# ---------------------------------------------------------------------------

class SalesReport(BaseModel):
    total: float
    units: int
    notes: str


async def main() -> None:
    # Set up MockGateway that returns JSON matching our schema
    mock = MockGateway()
    await mock.connect()
    mock.register("chat.send", {"runId": "r1", "status": "started"})

    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {
                "runId": "r1",
                "content": '{"total": 1234.56, "units": 42, "notes": "Q4 strong — holiday spike"}',
            }},
        )
    )

    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = client.get_agent("sales-analyst")

    # Show the schema prompt that gets appended to the query
    print("Schema prompt suffix (excerpt):")
    suffix = StructuredOutput.schema_prompt(SalesReport)
    print(f"  {suffix.strip().splitlines()[0]}")
    print()

    # --- Use agent.execute_structured() — the MD7 convenience method ---
    # Internally calls StructuredOutput.execute(): appends schema prompt,
    # sends query, parses response into a typed Pydantic model.
    report: SalesReport = await agent.execute_structured(
        "Generate a sales report for Q4",
        output_model=SalesReport,
    )

    print("Parsed SalesReport via agent.execute_structured():")
    print(f"  Total revenue : ${report.total:,.2f}")
    print(f"  Units sold    : {report.units}")
    print(f"  Notes         : {report.notes}")

    # Demonstrate direct parsing from a fenced JSON block
    raw_json = '```json\n{"total": 999.0, "units": 10, "notes": "test"}\n```'
    parsed = StructuredOutput.parse(raw_json, SalesReport)
    print(f"\nDirect parse from fenced JSON block:")
    print(f"  Total={parsed.total}, Units={parsed.units}, Notes={parsed.notes!r}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

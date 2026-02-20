# RUN: python examples/08_structured_output.py
"""Structured output — parse agent response into a typed Pydantic model."""

import asyncio

from pydantic import BaseModel

from openclaw_sdk.core.types import ExecutionResult
from openclaw_sdk.output.structured import StructuredOutput


# ---------------------------------------------------------------------------
# Define the output schema
# ---------------------------------------------------------------------------

class SalesReport(BaseModel):
    total: float
    units: int
    notes: str


# ---------------------------------------------------------------------------
# Mock agent — returns a JSON string without needing a real gateway
# ---------------------------------------------------------------------------

class MockAgent:
    """Minimal agent-like object for demo purposes."""

    agent_id = "sales-analyst"

    async def execute(self, query: str) -> ExecutionResult:
        # In a real scenario the LLM would produce this JSON.
        return ExecutionResult(
            success=True,
            content='{"total": 1234.56, "units": 42, "notes": "Q4 strong — holiday spike"}',
        )


async def main() -> None:
    agent = MockAgent()

    print("Executing structured output query...")
    print(f"  Schema prompt suffix (excerpt):")
    suffix = StructuredOutput.schema_prompt(SalesReport)
    # Print just the first line of the schema prompt for brevity
    print(f"  {suffix.strip().splitlines()[0]}")
    print()

    # StructuredOutput.execute appends the schema prompt and parses the result
    report: SalesReport = await StructuredOutput.execute(
        agent,
        "Generate a sales report for Q4",
        SalesReport,
    )

    print("Parsed SalesReport:")
    print(f"  Total revenue : ${report.total:,.2f}")
    print(f"  Units sold    : {report.units}")
    print(f"  Notes         : {report.notes}")

    # Demonstrate direct parsing too
    raw_json = '```json\n{"total": 999.0, "units": 10, "notes": "test"}\n```'
    parsed = StructuredOutput.parse(raw_json, SalesReport)
    print(f"\nDirect parse from fenced JSON block:")
    print(f"  Total={parsed.total}, Units={parsed.units}, Notes={parsed.notes!r}")


if __name__ == "__main__":
    asyncio.run(main())

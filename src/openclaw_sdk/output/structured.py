from __future__ import annotations

import json
import re
from typing import Protocol, Type, TypeVar

from pydantic import BaseModel

from openclaw_sdk.core.exceptions import OutputParsingError
from openclaw_sdk.core.types import ExecutionResult

T = TypeVar("T", bound=BaseModel)


class _AgentLike(Protocol):
    """Structural protocol for any object that can execute a query and return an ExecutionResult."""

    async def execute(self, query: str) -> ExecutionResult: ...


class StructuredOutput:
    """Utilities for extracting structured (Pydantic) data from LLM responses."""

    @staticmethod
    def schema_prompt(model: Type[T]) -> str:
        """Return a prompt suffix instructing the LLM to reply with JSON matching the model schema."""
        schema = model.model_json_schema()
        return (
            f"\n\nRespond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```"
        )

    @staticmethod
    def parse(response: str, model: Type[T]) -> T:
        """Extract the first JSON block from *response* and validate it against *model*.

        Search order:
        1. A fenced `` ```json ... ``` `` block.
        2. A bare ``{...}`` JSON object.

        Raises:
            OutputParsingError: If no valid JSON is found or Pydantic validation fails.
        """
        # 1. Try fenced ```json...``` block
        match = re.search(r"```json\s*([\s\S]*?)```", response)
        if match:
            json_str = match.group(1).strip()
        else:
            # 2. Try bare JSON object
            bare_match = re.search(r"\{[\s\S]*\}", response)
            if bare_match:
                json_str = bare_match.group(0)
            else:
                raise OutputParsingError(
                    f"No JSON found in response: {response[:200]}"
                )

        try:
            data = json.loads(json_str)
            return model.model_validate(data)
        except (json.JSONDecodeError, Exception) as exc:
            raise OutputParsingError(
                f"Failed to parse response as {model.__name__}: {exc}"
            ) from exc

    @staticmethod
    async def execute(
        agent: _AgentLike,
        query: str,
        output_model: Type[T],
        max_retries: int = 2,
    ) -> T:
        """Run *query* against *agent*, appending the JSON schema prompt, then parse the result.

        Retries up to *max_retries* additional times on ``OutputParsingError``.

        Args:
            agent: Any object with ``async execute(query: str) -> ExecutionResult``.
            query: The user query to send.
            output_model: The Pydantic model class to validate the response against.
            max_retries: Number of additional attempts after the first failure (default 2).

        Returns:
            A validated instance of *output_model*.

        Raises:
            OutputParsingError: After all attempts are exhausted.
        """
        full_query = query + StructuredOutput.schema_prompt(output_model)
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            result = await agent.execute(full_query)
            try:
                return StructuredOutput.parse(result.content, output_model)
            except OutputParsingError as exc:
                last_error = exc
                if attempt < max_retries:
                    continue  # retry

        raise last_error or OutputParsingError("All retries exhausted")

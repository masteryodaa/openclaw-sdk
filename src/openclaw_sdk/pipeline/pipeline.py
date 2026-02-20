from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pydantic import BaseModel

from openclaw_sdk.core.exceptions import PipelineError
from openclaw_sdk.core.types import ExecutionResult, GeneratedFile

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


class PipelineStep(BaseModel):
    name: str
    agent_id: str
    prompt_template: str
    output_key: str = "content"


class PipelineResult(BaseModel):
    success: bool
    steps: dict[str, ExecutionResult]
    final_result: ExecutionResult
    total_latency_ms: int
    all_files: list[GeneratedFile]


class Pipeline:
    """Execute a sequence of agent calls where each step can use outputs from prior steps.

    Args:
        client: An OpenClawClient (or duck-typed equivalent) that exposes
                ``get_agent(agent_id)`` returning an object with
                ``async execute(prompt) -> ExecutionResult``.
    """

    def __init__(self, client: OpenClawClient) -> None:
        self._client = client
        self._steps: list[PipelineStep] = []

    def add_step(
        self,
        name: str,
        agent_id: str,
        prompt: str,
        output_key: str = "content",
    ) -> "Pipeline":
        """Add a pipeline step and return self for method chaining."""
        self._steps.append(
            PipelineStep(
                name=name,
                agent_id=agent_id,
                prompt_template=prompt,
                output_key=output_key,
            )
        )
        return self

    async def run(self, **initial_variables: str) -> PipelineResult:
        """Execute all steps in sequence.

        ``{variable_name}`` placeholders in prompt templates are replaced with:
        - values from ``initial_variables`` (keyword arguments passed to this method), or
        - the output of the step whose name matches ``variable_name``.

        Execution stops on the first failure and ``PipelineResult.success`` is
        set to ``False``.

        Raises:
            PipelineError: If no steps have been added.
        """
        if not self._steps:
            raise PipelineError("Pipeline has no steps. Add steps with add_step() before running.")

        variables: dict[str, str] = dict(initial_variables)
        step_results: dict[str, ExecutionResult] = {}
        start_ms = _now_ms()
        all_files: list[GeneratedFile] = []
        last_result: ExecutionResult | None = None

        for step in self._steps:
            try:
                prompt = step.prompt_template.format(**variables)
            except KeyError as exc:
                missing_var = str(exc).strip("'")
                failed_result = ExecutionResult(
                    success=False,
                    content=f"Missing variable {missing_var!r} for step {step.name!r}",
                )
                step_results[step.name] = failed_result
                return PipelineResult(
                    success=False,
                    steps=step_results,
                    final_result=failed_result,
                    total_latency_ms=_now_ms() - start_ms,
                    all_files=all_files,
                )

            agent = self._client.get_agent(step.agent_id)
            result: ExecutionResult = await agent.execute(prompt)
            step_results[step.name] = result
            last_result = result

            # Collect generated files from this step
            all_files.extend(result.files)

            if not result.success:
                return PipelineResult(
                    success=False,
                    steps=step_results,
                    final_result=result,
                    total_latency_ms=_now_ms() - start_ms,
                    all_files=all_files,
                )

            # Make this step's output available as a variable for subsequent steps
            output_value = getattr(result, step.output_key, result.content)
            variables[step.name] = str(output_value)

        # At least one step was executed (guaranteed by the empty-check above)
        assert last_result is not None  # for mypy
        return PipelineResult(
            success=True,
            steps=step_results,
            final_result=last_result,
            total_latency_ms=_now_ms() - start_ms,
            all_files=all_files,
        )

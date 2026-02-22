from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Union

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

    def __repr__(self) -> str:
        return f"Pipeline(steps={len(self._steps)})"

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


# =========================================================================== #
# Conditional Pipeline — internal step types
# =========================================================================== #


@dataclass
class _SequentialStep:
    """A single agent call (same semantics as the linear Pipeline)."""

    name: str
    agent_id: str
    prompt_template: str
    output_key: str = "content"


@dataclass
class _BranchStep:
    """Routes to one of two steps based on a condition evaluated on a prior result."""

    after_step: str
    condition: Callable[[ExecutionResult], bool]
    if_true: _SequentialStep
    if_false: _SequentialStep


@dataclass
class _ParallelStep:
    """Runs multiple steps concurrently via ``asyncio.gather``."""

    steps: list[_SequentialStep] = field(default_factory=list)


@dataclass
class _FallbackStep:
    """Tries *primary*; on any exception, runs *fallback* instead."""

    primary: _SequentialStep
    fallback: _SequentialStep


# Union of all step types handled by ConditionalPipeline.run()
_Step = Union[_SequentialStep, _BranchStep, _ParallelStep, _FallbackStep]


class ConditionalPipeline:
    """Pipeline with branching, parallel execution, and error fallbacks.

    Extends the linear :class:`Pipeline` concept with three new step types:

    * **Branch** — evaluate a condition on a prior step's result and route to
      one of two agent calls.
    * **Parallel** — run multiple agent calls concurrently.
    * **Fallback** — try a primary agent call; if it raises, run a fallback.

    All builder methods return *self* for fluent chaining.

    Example::

        pipeline = ConditionalPipeline(client)
        pipeline.add_step("classify", "classifier", "Is this a complaint? {input}")
        pipeline.add_branch(
            "classify",
            condition=lambda result: "complaint" in result.content.lower(),
            if_true=("handle_complaint", "support-agent", "Handle: {input}"),
            if_false=("answer_question", "faq-bot", "Answer: {input}"),
        )
        result = await pipeline.run(input="I want a refund")
    """

    def __init__(self, client: OpenClawClient) -> None:
        self._client = client
        self._steps: list[_Step] = []

    # ------------------------------------------------------------------ #
    # Builder API
    # ------------------------------------------------------------------ #

    def add_step(
        self,
        name: str,
        agent_id: str,
        prompt_template: str,
        *,
        output_key: str = "content",
    ) -> ConditionalPipeline:
        """Add a sequential step (same as linear Pipeline).

        Args:
            name: Unique name for this step (used as a variable in later templates).
            agent_id: The agent to call.
            prompt_template: Prompt with ``{variable}`` placeholders.
            output_key: Attribute of :class:`ExecutionResult` to expose as a variable
                        (default ``"content"``).

        Returns:
            *self* for method chaining.
        """
        self._steps.append(
            _SequentialStep(
                name=name,
                agent_id=agent_id,
                prompt_template=prompt_template,
                output_key=output_key,
            )
        )
        return self

    def add_branch(
        self,
        after_step: str,
        condition: Callable[[ExecutionResult], bool],
        if_true: tuple[str, str, str],
        if_false: tuple[str, str, str],
    ) -> ConditionalPipeline:
        """Add a conditional branch after a named step.

        The *condition* callable receives the :class:`ExecutionResult` of
        *after_step* and must return ``True`` or ``False``.

        Args:
            after_step: Name of a previously-added step whose result is tested.
            condition: ``(ExecutionResult) -> bool`` predicate.
            if_true: ``(name, agent_id, prompt_template)`` executed when condition is truthy.
            if_false: ``(name, agent_id, prompt_template)`` executed when condition is falsy.

        Returns:
            *self* for method chaining.
        """
        self._steps.append(
            _BranchStep(
                after_step=after_step,
                condition=condition,
                if_true=_SequentialStep(
                    name=if_true[0],
                    agent_id=if_true[1],
                    prompt_template=if_true[2],
                ),
                if_false=_SequentialStep(
                    name=if_false[0],
                    agent_id=if_false[1],
                    prompt_template=if_false[2],
                ),
            )
        )
        return self

    def add_parallel(
        self,
        steps: list[tuple[str, str, str]],
    ) -> ConditionalPipeline:
        """Add steps that run concurrently via ``asyncio.gather``.

        Args:
            steps: List of ``(name, agent_id, prompt_template)`` tuples.

        Returns:
            *self* for method chaining.
        """
        parallel_steps = [
            _SequentialStep(name=s[0], agent_id=s[1], prompt_template=s[2])
            for s in steps
        ]
        self._steps.append(_ParallelStep(steps=parallel_steps))
        return self

    def add_fallback(
        self,
        name: str,
        agent_id: str,
        prompt_template: str,
        *,
        fallback_agent_id: str,
        fallback_prompt: str,
    ) -> ConditionalPipeline:
        """Add a step with a fallback if it fails.

        If the primary step raises any exception, the fallback step is executed
        instead and the pipeline continues.

        Args:
            name: Unique step name.
            agent_id: Primary agent to try.
            prompt_template: Primary prompt.
            fallback_agent_id: Fallback agent to use on failure.
            fallback_prompt: Fallback prompt template.

        Returns:
            *self* for method chaining.
        """
        self._steps.append(
            _FallbackStep(
                primary=_SequentialStep(
                    name=name,
                    agent_id=agent_id,
                    prompt_template=prompt_template,
                ),
                fallback=_SequentialStep(
                    name=f"{name}_fallback",
                    agent_id=fallback_agent_id,
                    prompt_template=fallback_prompt,
                ),
            )
        )
        return self

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    async def _execute_sequential(
        self,
        step: _SequentialStep,
        variables: dict[str, str],
    ) -> ExecutionResult:
        """Execute a single sequential step, formatting its prompt with *variables*."""
        prompt = step.prompt_template.format(**variables)
        agent = self._client.get_agent(step.agent_id)
        return await agent.execute(prompt)

    async def run(self, **initial_variables: str) -> PipelineResult:
        """Execute the conditional pipeline.

        Iterates through all registered steps in order:

        * **_SequentialStep** — execute and store the result.
        * **_BranchStep** — evaluate the condition on the referenced step's result;
          execute the matching branch.
        * **_ParallelStep** — run all sub-steps concurrently with ``asyncio.gather``.
        * **_FallbackStep** — try the primary step; on exception, run the fallback.

        All step results are available as ``{step_name}`` variables for subsequent
        prompt templates.

        Raises:
            PipelineError: If no steps have been added.
        """
        if not self._steps:
            raise PipelineError(
                "ConditionalPipeline has no steps. "
                "Add steps with add_step() / add_branch() / add_parallel() / add_fallback() before running."
            )

        variables: dict[str, str] = dict(initial_variables)
        step_results: dict[str, ExecutionResult] = {}
        start_ms = _now_ms()
        all_files: list[GeneratedFile] = []
        last_result: ExecutionResult | None = None

        for step in self._steps:
            if isinstance(step, _SequentialStep):
                try:
                    result = await self._execute_sequential(step, variables)
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

                step_results[step.name] = result
                last_result = result
                all_files.extend(result.files)

                if not result.success:
                    return PipelineResult(
                        success=False,
                        steps=step_results,
                        final_result=result,
                        total_latency_ms=_now_ms() - start_ms,
                        all_files=all_files,
                    )

                output_value = getattr(result, step.output_key, result.content)
                variables[step.name] = str(output_value)

            elif isinstance(step, _BranchStep):
                # Look up the referenced step's result.
                ref_result = step_results.get(step.after_step)
                if ref_result is None:
                    failed_result = ExecutionResult(
                        success=False,
                        content=(
                            f"Branch references step {step.after_step!r} "
                            f"which has not been executed yet"
                        ),
                    )
                    return PipelineResult(
                        success=False,
                        steps=step_results,
                        final_result=failed_result,
                        total_latency_ms=_now_ms() - start_ms,
                        all_files=all_files,
                    )

                chosen = step.if_true if step.condition(ref_result) else step.if_false

                try:
                    result = await self._execute_sequential(chosen, variables)
                except KeyError as exc:
                    missing_var = str(exc).strip("'")
                    failed_result = ExecutionResult(
                        success=False,
                        content=f"Missing variable {missing_var!r} for step {chosen.name!r}",
                    )
                    step_results[chosen.name] = failed_result
                    return PipelineResult(
                        success=False,
                        steps=step_results,
                        final_result=failed_result,
                        total_latency_ms=_now_ms() - start_ms,
                        all_files=all_files,
                    )

                step_results[chosen.name] = result
                last_result = result
                all_files.extend(result.files)

                if not result.success:
                    return PipelineResult(
                        success=False,
                        steps=step_results,
                        final_result=result,
                        total_latency_ms=_now_ms() - start_ms,
                        all_files=all_files,
                    )

                output_value = getattr(result, chosen.output_key, result.content)
                variables[chosen.name] = str(output_value)

            elif isinstance(step, _ParallelStep):
                # Run all parallel sub-steps concurrently.
                async def _run_parallel_step(
                    s: _SequentialStep, vars_snapshot: dict[str, str]
                ) -> tuple[_SequentialStep, ExecutionResult]:
                    res = await self._execute_sequential(s, vars_snapshot)
                    return s, res

                # Take a snapshot of variables so parallel steps all see the same state.
                vars_snapshot = dict(variables)
                tasks = [
                    _run_parallel_step(s, vars_snapshot) for s in step.steps
                ]
                parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

                for item in parallel_results:
                    if isinstance(item, BaseException):
                        failed_result = ExecutionResult(
                            success=False,
                            content=f"Parallel step failed: {item}",
                        )
                        return PipelineResult(
                            success=False,
                            steps=step_results,
                            final_result=failed_result,
                            total_latency_ms=_now_ms() - start_ms,
                            all_files=all_files,
                        )

                    sub_step, sub_result = item
                    step_results[sub_step.name] = sub_result
                    last_result = sub_result
                    all_files.extend(sub_result.files)
                    output_value = getattr(sub_result, sub_step.output_key, sub_result.content)
                    variables[sub_step.name] = str(output_value)

                # Check if any parallel step failed (non-exception failure).
                for sub_step_def in step.steps:
                    sub_res = step_results.get(sub_step_def.name)
                    if sub_res is not None and not sub_res.success:
                        return PipelineResult(
                            success=False,
                            steps=step_results,
                            final_result=sub_res,
                            total_latency_ms=_now_ms() - start_ms,
                            all_files=all_files,
                        )

            elif isinstance(step, _FallbackStep):
                primary = step.primary
                fallback = step.fallback

                try:
                    result = await self._execute_sequential(primary, variables)
                    if not result.success:
                        raise PipelineError(
                            f"Primary step {primary.name!r} returned success=False"
                        )
                    step_results[primary.name] = result
                    last_result = result
                    all_files.extend(result.files)
                    output_value = getattr(result, primary.output_key, result.content)
                    variables[primary.name] = str(output_value)
                except Exception:
                    # Primary failed — run the fallback.
                    try:
                        fb_result = await self._execute_sequential(fallback, variables)
                    except KeyError as exc:
                        missing_var = str(exc).strip("'")
                        failed_result = ExecutionResult(
                            success=False,
                            content=f"Missing variable {missing_var!r} for fallback step {fallback.name!r}",
                        )
                        step_results[fallback.name] = failed_result
                        return PipelineResult(
                            success=False,
                            steps=step_results,
                            final_result=failed_result,
                            total_latency_ms=_now_ms() - start_ms,
                            all_files=all_files,
                        )

                    step_results[fallback.name] = fb_result
                    last_result = fb_result
                    all_files.extend(fb_result.files)

                    if not fb_result.success:
                        return PipelineResult(
                            success=False,
                            steps=step_results,
                            final_result=fb_result,
                            total_latency_ms=_now_ms() - start_ms,
                            all_files=all_files,
                        )

                    output_value = getattr(fb_result, fallback.output_key, fb_result.content)
                    # Store under the primary name so downstream templates can reference it.
                    variables[primary.name] = str(output_value)
                    variables[fallback.name] = str(output_value)

        # At least one step was executed (guaranteed by the empty-check above).
        assert last_result is not None  # for mypy
        return PipelineResult(
            success=True,
            steps=step_results,
            final_result=last_result,
            total_latency_ms=_now_ms() - start_ms,
            all_files=all_files,
        )

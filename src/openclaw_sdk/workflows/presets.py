"""Pre-built workflow configurations for common patterns."""
from __future__ import annotations

from openclaw_sdk.workflows.engine import Workflow
from openclaw_sdk.workflows.models import StepType, WorkflowStep


def review_workflow(
    reviewer_agent_id: str,
    author_agent_id: str,
) -> Workflow:
    """Create a code/document review workflow.

    Steps:
        1. **review** (AGENT): The reviewer agent reviews the content.
        2. **check_pass** (CONDITION): Checks if ``review_passed`` is
           ``True`` in the context.
        3. **revise** (AGENT): On failure, the author agent revises based
           on the review feedback.

    Args:
        reviewer_agent_id: Agent ID for the reviewer.
        author_agent_id: Agent ID for the author/reviser.

    Returns:
        A configured :class:`Workflow`.
    """
    return Workflow(
        name="review",
        steps=[
            WorkflowStep(
                name="review",
                step_type=StepType.AGENT,
                config={
                    "agent_id": reviewer_agent_id,
                    "query": "Review the following: {document}",
                },
                next_on_success="check_pass",
            ),
            WorkflowStep(
                name="check_pass",
                step_type=StepType.CONDITION,
                config={
                    "key": "review_passed",
                    "operator": "eq",
                    "value": True,
                },
                next_on_failure="revise",
            ),
            WorkflowStep(
                name="revise",
                step_type=StepType.AGENT,
                config={
                    "agent_id": author_agent_id,
                    "query": "Revise based on feedback: {review}",
                },
            ),
        ],
    )


def research_workflow(
    researcher_agent_id: str,
    summarizer_agent_id: str,
) -> Workflow:
    """Create a research-and-summarize workflow.

    Steps:
        1. **research** (AGENT): The researcher agent gathers information.
        2. **extract** (TRANSFORM): Extracts findings from the research
           result into a ``findings`` context key.
        3. **summarize** (AGENT): The summarizer agent creates a summary.

    Args:
        researcher_agent_id: Agent ID for the researcher.
        summarizer_agent_id: Agent ID for the summarizer.

    Returns:
        A configured :class:`Workflow`.
    """
    return Workflow(
        name="research",
        steps=[
            WorkflowStep(
                name="research",
                step_type=StepType.AGENT,
                config={
                    "agent_id": researcher_agent_id,
                    "query": "Research the following topic: {topic}",
                },
            ),
            WorkflowStep(
                name="extract",
                step_type=StepType.TRANSFORM,
                config={
                    "mapping": {"research": "findings"},
                },
            ),
            WorkflowStep(
                name="summarize",
                step_type=StepType.AGENT,
                config={
                    "agent_id": summarizer_agent_id,
                    "query": "Summarize these findings: {findings}",
                },
            ),
        ],
    )


def support_workflow(
    triage_agent_id: str,
    support_agent_id: str,
) -> Workflow:
    """Create a customer support triage workflow.

    Steps:
        1. **triage** (AGENT): The triage agent classifies the issue.
        2. **check_priority** (CONDITION): Checks if ``priority`` in the
           context equals ``"high"``.
        3. **detailed_support** (AGENT): On high priority, the support
           agent provides detailed assistance.

    Args:
        triage_agent_id: Agent ID for the triage agent.
        support_agent_id: Agent ID for the detailed support agent.

    Returns:
        A configured :class:`Workflow`.
    """
    return Workflow(
        name="support",
        steps=[
            WorkflowStep(
                name="triage",
                step_type=StepType.AGENT,
                config={
                    "agent_id": triage_agent_id,
                    "query": "Triage this support request: {request}",
                },
            ),
            WorkflowStep(
                name="check_priority",
                step_type=StepType.CONDITION,
                config={
                    "key": "priority",
                    "operator": "eq",
                    "value": "high",
                },
                next_on_failure="detailed_support",
            ),
            WorkflowStep(
                name="detailed_support",
                step_type=StepType.AGENT,
                config={
                    "agent_id": support_agent_id,
                    "query": "Provide detailed support for: {triage}",
                },
            ),
        ],
    )

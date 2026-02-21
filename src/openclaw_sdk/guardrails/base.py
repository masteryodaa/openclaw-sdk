"""Base classes for the guardrails system."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class GuardrailResult(BaseModel):
    """Result of a guardrail check.

    Attributes:
        passed: Whether the check passed (True) or was blocked/failed (False).
        guardrail_name: Name of the guardrail that produced this result.
        message: Human-readable explanation of the result.
        modified_text: If the guardrail rewrites content (e.g. PII redaction),
                       contains the modified version. ``None`` when unmodified.
    """

    passed: bool
    guardrail_name: str
    message: str = ""
    modified_text: str | None = None


class Guardrail(ABC):
    """Abstract base class for input/output guardrails.

    Subclasses must implement :meth:`check_input` and :meth:`check_output`.
    """

    @property
    def name(self) -> str:
        """Return the guardrail name (defaults to the class name)."""
        return type(self).__name__

    @abstractmethod
    async def check_input(self, query: str) -> GuardrailResult:
        """Check the input query **before** agent execution.

        Returns a :class:`GuardrailResult` indicating whether execution should
        proceed.
        """
        ...

    @abstractmethod
    async def check_output(self, response: str) -> GuardrailResult:
        """Check the output response **after** agent execution.

        Returns a :class:`GuardrailResult` indicating whether the response is
        acceptable.
        """
        ...

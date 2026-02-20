"""Trace span -- a single unit of work in an execution trace."""

from __future__ import annotations

import time
import uuid
from typing import Any


class Span:
    """Represents a single unit of work in a hierarchical execution trace.

    Spans form a tree: each has a ``span_id`` and an optional ``parent_id``
    linking it to its parent span.
    """

    def __init__(
        self,
        name: str,
        agent_id: str | None = None,
        parent_id: str | None = None,
    ) -> None:
        self.span_id: str = uuid.uuid4().hex[:16]
        self.parent_id: str | None = parent_id
        self.name: str = name
        self.agent_id: str | None = agent_id
        self.attributes: dict[str, Any] = {}
        self.start_time: float = time.monotonic()
        self.end_time: float | None = None
        self.status: str = "ok"
        self.error: str | None = None

    @property
    def duration_ms(self) -> int | None:
        """Return elapsed milliseconds, or ``None`` if not yet ended."""
        if self.end_time is None:
            return None
        return int((self.end_time - self.start_time) * 1000)

    def set_attribute(self, key: str, value: Any) -> None:
        """Attach an arbitrary key/value attribute to this span."""
        self.attributes[key] = value

    def set_error(self, error: str) -> None:
        """Mark this span as failed with the given error message."""
        self.status = "error"
        self.error = error

    def end(self) -> None:
        """Record the end time (idempotent -- only the first call takes effect)."""
        if self.end_time is None:
            self.end_time = time.monotonic()

    def to_dict(self) -> dict[str, Any]:
        """Serialise the span to a plain dictionary."""
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "agent_id": self.agent_id,
            "status": self.status,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "attributes": dict(self.attributes),
        }

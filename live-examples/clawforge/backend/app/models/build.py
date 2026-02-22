"""Build-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


class BuildRequest(BaseModel):
    project_id: str
    mode: str = "pipeline"  # pipeline | workflow | goalloop
    agent_id: str = "main"
    max_steps: int = 5
    max_cost_usd: float = 2.0


class BuildStepEvent(BaseModel):
    step: str
    status: str  # started | content | complete | error
    content: str = ""
    metadata: dict | None = None

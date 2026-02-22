"""Project-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = ""
    description: str
    template: str | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    template: str | None = None
    created_at: str
    updated_at: str
    total_cost_usd: float = 0
    total_tokens: int = 0
    plan_json: dict | None = None
    messages: list[dict] | None = None
    files: list[dict] | None = None


class FilePlan(BaseModel):
    name: str
    path: str
    description: str


class ProjectPlan(BaseModel):
    """Structured plan for a project build."""
    overview: str
    steps: list[str]
    files: list[FilePlan] = []

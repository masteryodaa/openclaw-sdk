"""Billing-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


class ProjectBilling(BaseModel):
    project_id: str
    project_name: str
    total_cost_usd: float
    total_tokens: int
    message_count: int


class BillingSummary(BaseModel):
    total_cost_usd: float
    total_tokens: int
    project_count: int
    projects: list[ProjectBilling]

"""Billing endpoints — cost tracking."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.controllers import billing as billing_controller

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/summary")
async def billing_summary():
    """Get overall billing summary."""
    return await billing_controller.get_summary()


@router.get("/project/{project_id}")
async def project_billing(project_id: str):
    """Get cost breakdown for a project."""
    result = await billing_controller.get_project_costs(project_id)
    if not result:
        raise HTTPException(404, "Project not found")
    return result

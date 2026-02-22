"""Billing endpoints — cost tracking."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.controllers import billing as billing_controller

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/summary")
async def billing_summary():
    """Get overall billing summary."""
    log.info("GET /api/billing/summary")
    return await billing_controller.get_summary()


@router.get("/project/{project_id}")
async def project_billing(project_id: str):
    """Get cost breakdown for a project."""
    log.info("GET /api/billing/project/%s", project_id[:8])
    result = await billing_controller.get_project_costs(project_id)
    if not result:
        log.warning("Project %s not found for billing", project_id[:8])
        raise HTTPException(404, "Project not found")
    return result

"""Template endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.controllers import templates as templates_controller

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


class CreateFromTemplateRequest(BaseModel):
    template_id: str
    name: str = ""


@router.get("")
async def list_templates():
    """List all available templates."""
    log.info("GET /api/templates")
    return templates_controller.list_templates()


@router.post("/create")
async def create_from_template(body: CreateFromTemplateRequest):
    """Create a project from a template."""
    log.info("POST /api/templates/create template=%s name=%r", body.template_id, body.name)
    result = await templates_controller.create_from_template(body.template_id, body.name)
    if not result:
        log.warning("Template %r not found", body.template_id)
        raise HTTPException(404, f"Template '{body.template_id}' not found")
    return result

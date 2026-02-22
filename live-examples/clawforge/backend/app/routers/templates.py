"""Template endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.controllers import templates as templates_controller

router = APIRouter(prefix="/api/templates", tags=["templates"])


class CreateFromTemplateRequest(BaseModel):
    template_id: str
    name: str = ""


@router.get("")
async def list_templates():
    """List all available templates."""
    return templates_controller.list_templates()


@router.post("/create")
async def create_from_template(body: CreateFromTemplateRequest):
    """Create a project from a template."""
    result = await templates_controller.create_from_template(body.template_id, body.name)
    if not result:
        raise HTTPException(404, f"Template '{body.template_id}' not found")
    return result

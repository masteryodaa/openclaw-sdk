"""Project CRUD endpoints (thin router -- delegates to database helpers)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.helpers import database
from app.models.projects import CreateProjectRequest, UpdateProjectRequest

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects():
    """List all projects, newest first."""
    return await database.list_projects()


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest):
    """Create a new project."""
    name = body.name or body.description[:60]
    return await database.create_project(name, body.description, body.template)


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project with messages and files."""
    project = await database.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    project["messages"] = await database.get_messages(project_id)
    project["files"] = await database.get_files(project_id)
    return project


@router.patch("/{project_id}")
async def update_project(project_id: str, body: UpdateProjectRequest):
    """Update project fields."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = await database.update_project(project_id, **updates)
    if not result:
        raise HTTPException(404, "Project not found")
    return result


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project and all its data."""
    deleted = await database.delete_project(project_id)
    if not deleted:
        raise HTTPException(404, "Project not found")
    return {"deleted": True}

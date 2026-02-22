"""Project CRUD endpoints (thin router -- delegates to database helpers)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.helpers import database
from app.models.projects import CreateProjectRequest, UpdateProjectRequest

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects():
    """List all projects, newest first."""
    log.info("GET /api/projects")
    projects = await database.list_projects()
    log.debug("Returning %d projects", len(projects))
    return projects


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest):
    """Create a new project."""
    name = body.name or body.description[:60]
    log.info("POST /api/projects name=%r template=%s", name, body.template)
    result = await database.create_project(name, body.description, body.template)
    log.info("Created project id=%s", result["id"][:8])
    return result


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project with messages and files."""
    log.info("GET /api/projects/%s", project_id[:8])
    project = await database.get_project(project_id)
    if not project:
        log.warning("Project %s not found", project_id[:8])
        raise HTTPException(404, "Project not found")
    project["messages"] = await database.get_messages(project_id)
    project["files"] = await database.get_files(project_id)
    log.debug(
        "Project %s: %d messages, %d files",
        project_id[:8], len(project["messages"]), len(project["files"]),
    )
    return project


@router.patch("/{project_id}")
async def update_project(project_id: str, body: UpdateProjectRequest):
    """Update project fields."""
    updates = body.model_dump(exclude_none=True)
    log.info("PATCH /api/projects/%s fields=%s", project_id[:8], list(updates.keys()))
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = await database.update_project(project_id, **updates)
    if not result:
        log.warning("Project %s not found for update", project_id[:8])
        raise HTTPException(404, "Project not found")
    return result


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project and all its data."""
    log.info("DELETE /api/projects/%s", project_id[:8])
    deleted = await database.delete_project(project_id)
    if not deleted:
        log.warning("Project %s not found for delete", project_id[:8])
        raise HTTPException(404, "Project not found")
    log.info("Project %s deleted", project_id[:8])
    return {"deleted": True}

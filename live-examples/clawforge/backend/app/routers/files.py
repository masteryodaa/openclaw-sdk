"""File endpoints — generated project files."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.helpers import database

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{project_id}")
async def list_files(project_id: str):
    """List generated files for a project."""
    return await database.get_files(project_id)


@router.get("/{project_id}/{path:path}")
async def get_file(project_id: str, path: str):
    """Get a specific file's content."""
    files = await database.get_files(project_id)
    for f in files:
        if f["path"] == path or f["name"] == path:
            return f
    raise HTTPException(404, "File not found")

"""File endpoints — generated project files."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.helpers import database

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{project_id}")
async def list_files(project_id: str):
    """List generated files for a project."""
    log.info("GET /api/files/%s", project_id[:8])
    files = await database.get_files(project_id)
    log.debug("Found %d files for project %s", len(files), project_id[:8])
    return files


@router.get("/{project_id}/{path:path}")
async def get_file(project_id: str, path: str):
    """Get a specific file's content."""
    log.info("GET /api/files/%s/%s", project_id[:8], path)
    files = await database.get_files(project_id)
    for f in files:
        if f["path"] == path or f["name"] == path:
            log.debug("Found file %s", path)
            return f
    log.warning("File %s not found in project %s", path, project_id[:8])
    raise HTTPException(404, "File not found")

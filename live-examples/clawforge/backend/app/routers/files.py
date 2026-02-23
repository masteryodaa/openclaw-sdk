"""File endpoints — generated project files + OpenClaw workspace files."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.helpers import database

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])

# OpenClaw stores agent workspace files here
OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"


# --- Workspace routes MUST come before /{project_id} catch-all ---

@router.post("/workspace-record/{project_id}")
async def save_workspace_record(project_id: str, path: str = Query(...)):
    """Read a workspace file and persist it as a generated_file DB record.

    Idempotent — returns existing record if already saved for this project+path.
    """
    log.info("POST /api/files/workspace-record/%s path=%s", project_id[:8], path)
    safe = Path(path)
    if ".." in safe.parts:
        raise HTTPException(400, "Invalid path")

    full = OPENCLAW_WORKSPACE / safe
    if not full.exists() or not full.is_file():
        raise HTTPException(404, "File not found in workspace")

    if full.stat().st_size > 5_000_000:
        raise HTTPException(413, "File too large")

    try:
        content = full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "Binary file — cannot serve as text")

    # Idempotent: return existing record if already saved
    existing = await database.get_files(project_id)
    for f in existing:
        if f["path"] == path:
            log.debug("Workspace record already exists for %s", path)
            return f

    ext = full.suffix.lower()
    mime = "text/html" if ext in (".html", ".htm") else "text/plain"
    name = full.name

    saved = await database.add_file(project_id, name, path, content, len(content), mime)
    log.info("Saved workspace record %s (%d bytes)", path, len(content))
    return saved


@router.get("/workspace/{path:path}")
async def read_workspace_file(path: str):
    """Read a file from OpenClaw's agent workspace directory."""
    log.info("GET /api/files/workspace/%s", path)
    # Sanitize path to prevent traversal
    safe = Path(path)
    if ".." in safe.parts:
        raise HTTPException(400, "Invalid path")

    full = OPENCLAW_WORKSPACE / safe
    if not full.exists() or not full.is_file():
        log.warning("Workspace file not found: %s", full)
        raise HTTPException(404, "File not found in workspace")

    # Only serve text-like files
    size = full.stat().st_size
    if size > 5_000_000:  # 5MB cap
        raise HTTPException(413, "File too large")

    try:
        content = full.read_text(encoding="utf-8")
        log.info("Served workspace file %s (%d bytes)", path, len(content))

        # Determine content type
        ext = full.suffix.lower()
        if ext in (".html", ".htm"):
            return PlainTextResponse(content, media_type="text/html")
        return PlainTextResponse(content)
    except UnicodeDecodeError:
        raise HTTPException(415, "Binary file — cannot serve as text")


# --- Project file routes ---

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

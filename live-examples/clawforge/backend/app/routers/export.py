"""Export endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.controllers import export as export_controller
from app.models.export import ExportGitHubRequest

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/github")
async def export_github(body: ExportGitHubRequest):
    """Export project files to GitHub."""
    log.info("POST /api/export/github project=%s repo=%s", body.project_id[:8], body.repo_name)
    try:
        result = await export_controller.export_to_github(
            body.project_id,
            body.repo_name,
            body.github_token,
            body.description,
        )
        log.info("Export result: success=%s", result.get("success"))
        return result
    except ValueError as exc:
        log.error("Export error: %s", exc)
        raise HTTPException(404, str(exc)) from exc

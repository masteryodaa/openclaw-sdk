"""Export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.controllers import export as export_controller
from app.models.export import ExportGitHubRequest

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/github")
async def export_github(body: ExportGitHubRequest):
    """Export project files to GitHub."""
    try:
        return await export_controller.export_to_github(
            body.project_id,
            body.repo_name,
            body.github_token,
            body.description,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

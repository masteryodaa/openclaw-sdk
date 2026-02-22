"""File serving endpoint — serves agent-generated files (screenshots, documents)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/files", tags=["files"])

# Allowed base directories for serving files (security boundary)
ALLOWED_ROOTS = [
    Path.home() / ".openclaw" / "workspace",
    Path.home() / ".openclaw" / "downloads",
]


def _is_safe_path(path: Path) -> bool:
    """Verify the resolved path is within allowed roots."""
    resolved = path.resolve()
    return any(
        str(resolved).startswith(str(root.resolve()))
        for root in ALLOWED_ROOTS
        if root.exists()
    )


@router.get("")
async def serve_file(path: str = Query(..., description="Absolute file path")):
    """Serve a file from the agent workspace.

    Only files within ``~/.openclaw/workspace`` or ``~/.openclaw/downloads``
    are served (security boundary).
    """
    file_path = Path(path)

    if not file_path.is_absolute():
        raise HTTPException(400, "Path must be absolute")

    if not _is_safe_path(file_path):
        raise HTTPException(
            403,
            f"Access denied — file must be within {ALLOWED_ROOTS}",
        )

    if not file_path.exists():
        raise HTTPException(404, f"File not found: {path}")

    if not file_path.is_file():
        raise HTTPException(400, "Path is not a file")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=str(file_path),
        media_type=mime_type or "application/octet-stream",
        filename=file_path.name,
    )


@router.get("/list")
async def list_workspace_files(limit: int = 50):
    """List recent files in the agent workspace."""
    workspace = Path.home() / ".openclaw" / "workspace"
    if not workspace.exists():
        return {"files": []}

    files = sorted(workspace.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    return {
        "files": [
            {
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "mime_type": mimetypes.guess_type(str(f))[0] or "application/octet-stream",
            }
            for f in files[:limit]
            if f.is_file()
        ]
    }

"""File endpoints — generated project files + OpenClaw workspace files.

File content retrieval strategy:
1. Try ``files.get`` gateway RPC via the SDK (works for both local and remote gateways).
2. Fall back to reading from local filesystem (for local-only setups where the gateway
   and backend are co-located on the same machine).

This dual-path approach lets ClawForge work as a remote gateway showcase while staying
backward-compatible with the common local-gateway setup.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.helpers import database, gateway

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])

# OpenClaw stores agent workspace files here (local fallback path)
OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"


async def _read_via_sdk(project_id: str, path: str) -> str:
    """Read a workspace file via the SDK's ``files.get`` gateway RPC.

    Returns the file content as a UTF-8 string.
    Raises on any gateway or decode error so callers can fall back to local I/O.
    """
    client = await gateway.get_client()
    # Session key follows the same convention as the chat controller
    session_key = f"agent:main:clawforge-{project_id}"
    result = await client.gateway.call(
        "files.get", {"sessionKey": session_key, "path": path}
    )
    raw = result.get("content", "")
    if result.get("encoding") == "base64":
        return base64.b64decode(raw).decode("utf-8", errors="replace")
    return raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")


def _read_local(path: str) -> str:
    """Read a workspace file from the local filesystem (co-located gateway fallback)."""
    safe = Path(path)
    full = OPENCLAW_WORKSPACE / safe
    if not full.exists() or not full.is_file():
        raise FileNotFoundError(f"Not found: {full}")
    if full.stat().st_size > 5_000_000:
        raise ValueError("File too large (>5MB)")
    return full.read_text(encoding="utf-8")


# --- Workspace routes MUST come before /{project_id} catch-all ---

@router.post("/workspace-record/{project_id}")
async def save_workspace_record(project_id: str, path: str = Query(...)):
    """Read a workspace file and persist it as a generated_file DB record (upsert).

    Tries the SDK gateway RPC (``files.get``) first so this works with remote gateways.
    Falls back to reading from the local filesystem when the SDK call is unavailable.
    Always reflects the current agent-written state — re-calling updates the DB record.
    """
    log.info("POST /api/files/workspace-record/%s path=%s", project_id[:8], path)
    if ".." in Path(path).parts:
        raise HTTPException(400, "Invalid path")

    # 1. Try SDK (remote-gateway compatible)
    content: str | None = None
    try:
        content = await _read_via_sdk(project_id, path)
        log.info("workspace-record: read %s via SDK (%d bytes)", path, len(content))
    except Exception as sdk_exc:
        log.warning(
            "workspace-record: files.get SDK unavailable (%s), trying local filesystem",
            sdk_exc,
        )

    # 2. Fall back to local filesystem
    if content is None:
        try:
            content = _read_local(path)
            log.info("workspace-record: read %s from local filesystem (%d bytes)", path, len(content))
        except FileNotFoundError:
            raise HTTPException(404, "File not found in workspace")
        except ValueError as exc:
            raise HTTPException(413, str(exc))
        except UnicodeDecodeError:
            raise HTTPException(415, "Binary file — cannot serve as text")

    ext = Path(path).suffix.lower()
    mime = "text/html" if ext in (".html", ".htm") else "text/plain"
    name = Path(path).name

    # Upsert: update existing record if present (agent may have re-written the file),
    # otherwise insert a new record.
    existing = await database.get_files(project_id)
    for f in existing:
        if f["path"] == path:
            if f["content"] == content:
                log.debug("Workspace record unchanged for %s", path)
                return f
            updated = await database.update_file(project_id, path, content, len(content))
            log.info("Updated workspace record %s (%d bytes)", path, len(content))
            return updated

    saved = await database.add_file(project_id, name, path, content, len(content), mime)
    log.info("Saved workspace record %s (%d bytes)", path, len(content))
    return saved


@router.get("/workspace/{path:path}")
async def read_workspace_file(path: str, project_id: str = Query(default="")):
    """Read a file from OpenClaw's agent workspace directory.

    When ``project_id`` is provided the SDK gateway RPC (``files.get``) is tried first,
    enabling remote-gateway support. Falls back to local filesystem in both cases.
    """
    log.info("GET /api/files/workspace/%s project_id=%s", path, project_id or "(none)")
    if ".." in Path(path).parts:
        raise HTTPException(400, "Invalid path")

    content: str | None = None

    # 1. Try SDK when project_id is known (remote-gateway compatible)
    if project_id:
        try:
            content = await _read_via_sdk(project_id, path)
            log.info("workspace/: read %s via SDK (%d bytes)", path, len(content))
        except Exception as sdk_exc:
            log.warning(
                "workspace/: files.get SDK unavailable (%s), trying local filesystem",
                sdk_exc,
            )

    # 2. Fall back to local filesystem
    if content is None:
        try:
            content = _read_local(path)
            log.info("workspace/: read %s from local filesystem (%d bytes)", path, len(content))
        except FileNotFoundError:
            raise HTTPException(404, "File not found in workspace")
        except ValueError as exc:
            raise HTTPException(413, str(exc))
        except UnicodeDecodeError:
            raise HTTPException(415, "Binary file — cannot serve as text")

    ext = Path(path).suffix.lower()
    if ext in (".html", ".htm"):
        return PlainTextResponse(content, media_type="text/html")
    return PlainTextResponse(content)


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

"""Workspace static file server — serves OpenClaw agent workspace files over HTTP.

Why this exists:
  - Agent may create React/Vue/Vite apps that need a real HTTP base URL (not srcdoc)
  - srcdoc iframes have no base URL so relative paths like ./assets/main.js break
  - Remote gateways: dev server on localhost:5173 is unreachable from user's browser
  - Solution: serve workspace files through the ClawForge backend, which IS reachable

Route: GET /workspace-site/{project_id}/{path}
  -> tries SDK files.get RPC first (remote-gateway compatible)
  -> falls back to ~/.openclaw/workspace/{path} for co-located gateways

Security: path traversal check (no ".." components).
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.helpers import gateway

log = logging.getLogger(__name__)

router = APIRouter(tags=["workspace-site"])

WORKSPACE = Path.home() / ".openclaw" / "workspace"

# MIME types for common web assets
_MIME_MAP = {
    ".html": "text/html; charset=utf-8",
    ".htm":  "text/html; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".mjs":  "application/javascript; charset=utf-8",
    ".ts":   "application/javascript; charset=utf-8",
    ".jsx":  "application/javascript; charset=utf-8",
    ".tsx":  "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg":  "image/svg+xml",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".webp": "image/webp",
    ".ico":  "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf":  "font/ttf",
    ".txt":  "text/plain; charset=utf-8",
}


@router.get("/workspace-site/{project_id}/{path:path}")
async def serve_workspace_file(project_id: str, path: str):
    """Serve a file from the OpenClaw agent workspace directory.

    Tries the SDK ``files.get`` gateway RPC first (works for remote gateways).
    Falls back to reading from the local filesystem when the SDK call is unavailable.

    This is the key enabler for framework apps (React/Vite/etc):
    - Files are served with a real HTTP base URL
    - The iframe uses src= (not srcdoc) so relative paths work
    - Works for remote gateways — user's browser only needs to reach ClawForge
    """
    # Security: reject path traversal attempts
    safe = Path(path)
    if ".." in safe.parts:
        raise HTTPException(400, "Invalid path")

    ext = safe.suffix.lower()
    mime = _MIME_MAP.get(ext) or mimetypes.guess_type(str(safe))[0] or "application/octet-stream"
    log.debug("workspace-site request: project=%s path=%s mime=%s", project_id[:8], path, mime)

    content_bytes: bytes | None = None

    # 1. Try SDK gateway RPC (remote-gateway compatible)
    try:
        client = await gateway.get_client()
        session_key = f"agent:main:clawforge-{project_id}"
        result = await client.gateway.call(
            "files.get", {"sessionKey": session_key, "path": path}
        )
        raw = result.get("content", "")
        if result.get("encoding") == "base64":
            content_bytes = base64.b64decode(raw)
        else:
            content_bytes = raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)
        log.info("workspace-site: served %s via SDK (%d bytes)", path, len(content_bytes))
    except Exception as sdk_exc:
        log.warning(
            "workspace-site: files.get SDK unavailable (%s), trying local filesystem",
            sdk_exc,
        )

    # 2. Fall back to local filesystem
    if content_bytes is None:
        full = WORKSPACE / safe
        log.debug("workspace-site local fallback: %s → %s", path, full)

        if not full.exists():
            raise HTTPException(404, f"Not found: {path}")
        if not full.is_file():
            raise HTTPException(404, f"Not a file: {path}")
        if full.stat().st_size > 20_000_000:  # 20MB cap
            raise HTTPException(413, "File too large")

        is_text = (
            mime.startswith("text/")
            or "javascript" in mime
            or "json" in mime
            or "svg" in mime
        )
        try:
            if is_text:
                content_bytes = full.read_text(encoding="utf-8", errors="replace").encode("utf-8")
            else:
                content_bytes = full.read_bytes()
        except Exception as exc:
            log.error("Failed to read workspace file %s: %s", full, exc)
            raise HTTPException(500, "Could not read file") from exc

        log.info(
            "workspace-site: served %s from local filesystem (%d bytes, %s)",
            path, len(content_bytes), mime,
        )

    # Allow iframes to run scripts; set permissive headers for local dev
    return Response(
        content=content_bytes,
        media_type=mime.split(";")[0].strip(),  # FastAPI sets charset separately
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
            # Remove X-Frame-Options so iframe embedding works
            "X-Frame-Options": "ALLOWALL",
        },
    )

"""Build endpoints — streaming multi-agent pipeline + npm workspace builds."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.controllers import build as build_controller
from app.helpers import gateway
from app.models.build import BuildRequest

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/build", tags=["build"])

WORKSPACE = Path.home() / ".openclaw" / "workspace"


class NpmBuildRequest(BaseModel):
    """Request to build a npm/Vite/CRA project in the workspace."""
    directory: str  # e.g. "erp-dashboard" — relative to workspace root


@router.post("/workspace-npm")
async def build_workspace_npm(body: NpmBuildRequest):
    """Run npm install + build inside a workspace directory.

    Handles React/Vite/CRA apps created by agents. Uses --base=./ for Vite
    so asset paths are relative and work when served from /workspace-site/.

    Returns the path to the built index.html (e.g. "erp-dashboard/dist/index.html").
    """
    # Security
    safe = Path(body.directory)
    if ".." in safe.parts or safe.is_absolute():
        raise HTTPException(400, "Invalid directory")

    app_dir = WORKSPACE / safe
    if not app_dir.exists() or not app_dir.is_dir():
        raise HTTPException(404, f"Directory not found in workspace: {body.directory}")

    package_json = app_dir / "package.json"
    if not package_json.exists():
        raise HTTPException(400, "No package.json found — not a Node.js project")

    log.info("npm build start: %s", app_dir)

    # Detect build system and choose appropriate build command
    is_vite = (app_dir / "vite.config.ts").exists() or (app_dir / "vite.config.js").exists()

    try:
        # Step 1: npm install
        log.info("Running npm install in %s...", app_dir)
        proc = await asyncio.create_subprocess_exec(
            "npm", "install", "--prefer-offline", "--no-audit",
            cwd=str(app_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        if proc.returncode != 0:
            out = stderr.decode("utf-8", errors="replace")
            log.error("npm install failed: %s", out[:500])
            raise HTTPException(500, f"npm install failed: {out[:300]}")
        log.info("npm install done")

        # Step 2: build (with --base=./ for Vite so asset paths are relative)
        if is_vite:
            build_cmd = ["npx", "vite", "build", "--base=./"]
        else:
            # CRA / generic — relative base via PUBLIC_URL
            build_cmd = ["npm", "run", "build"]

        env_override = {"PUBLIC_URL": "."} if not is_vite else {}
        import os
        env = {**os.environ, **env_override}

        log.info("Running build cmd: %s in %s", build_cmd, app_dir)
        proc = await asyncio.create_subprocess_exec(
            *build_cmd,
            cwd=str(app_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        build_output = stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            log.error("Build failed: %s", build_output[:500])
            raise HTTPException(500, f"Build failed: {build_output[:400]}")

        log.info("Build succeeded for %s", app_dir)

    except asyncio.TimeoutError as exc:
        raise HTTPException(504, "Build timed out (> 5 min)") from exc

    # Find built index.html
    dist_candidates = ["dist", "build", "out", ".output/public"]
    index_path: str | None = None
    for candidate in dist_candidates:
        candidate_index = app_dir / candidate / "index.html"
        if candidate_index.exists():
            # Return path relative to workspace root for use in /workspace-site/
            index_path = str(Path(body.directory) / candidate / "index.html").replace("\\", "/")
            break

    if not index_path:
        raise HTTPException(500, "Build succeeded but no index.html found in dist/build/out")

    log.info("Build complete. index at workspace-site/%s", index_path)
    return {
        "success": True,
        "index_path": index_path,          # e.g. "erp-dashboard/dist/index.html"
        "preview_url": f"/workspace-site/{index_path}",
        "output": build_output[-1000:],     # last 1KB of build output
    }


@router.post("/stream")
async def build_stream(body: BuildRequest):
    """Stream build execution via SSE."""
    log.info(
        "POST /api/build/stream project=%s mode=%s agent=%s",
        body.project_id[:8], body.mode, body.agent_id,
    )
    client = await gateway.get_client()
    return EventSourceResponse(
        build_controller.stream_build(
            client,
            body.project_id,
            mode=body.mode,
            agent_id=body.agent_id,
            max_steps=body.max_steps,
            max_cost_usd=body.max_cost_usd,
        )
    )

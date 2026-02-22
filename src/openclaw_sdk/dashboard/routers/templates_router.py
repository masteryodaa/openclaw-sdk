"""Template endpoints — list and inspect agent templates."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["templates"])


@router.get("/api/templates")
async def list_templates(request: Request) -> JSONResponse:
    """List available template names."""
    from openclaw_sdk.templates.registry import list_templates as _list

    return JSONResponse(content=_list())


@router.get("/api/templates/{name}")
async def get_template(name: str, request: Request) -> JSONResponse:
    """Get template details by name."""
    from openclaw_sdk.templates.registry import get_template as _get

    try:
        config = _get(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONResponse(content=config.model_dump(mode="json"))

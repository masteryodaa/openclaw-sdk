"""Connector listing endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["connectors"])


@router.get("/api/connectors")
async def list_connectors(request: Request) -> JSONResponse:
    """List available connector classes."""
    from openclaw_sdk.connectors import __all__ as connector_names

    # Filter to only actual connector class names (ending with "Connector").
    classes = [n for n in connector_names if n.endswith("Connector")]
    return JSONResponse(content=classes)

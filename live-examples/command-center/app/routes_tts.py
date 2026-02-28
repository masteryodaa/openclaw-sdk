"""TTS endpoints — text-to-speech management."""

from __future__ import annotations

from fastapi import APIRouter

from . import gateway

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/status")
async def tts_status():
    """Get TTS status (enabled, provider, voice)."""
    client = await gateway.get_client()
    return await client.tts.status()


@router.get("/providers")
async def tts_providers():
    """List available TTS providers."""
    client = await gateway.get_client()
    return await client.tts.providers()


@router.post("/enable")
async def tts_enable():
    """Enable text-to-speech."""
    client = await gateway.get_client()
    return await client.tts.enable()


@router.post("/disable")
async def tts_disable():
    """Disable text-to-speech."""
    client = await gateway.get_client()
    return await client.tts.disable()


@router.post("/provider/{provider}")
async def tts_set_provider(provider: str):
    """Set TTS provider (edge, openai, elevenlabs)."""
    client = await gateway.get_client()
    return await client.tts.set_provider(provider)


@router.post("/convert")
async def tts_convert(text: str):
    """Convert text to speech audio."""
    client = await gateway.get_client()
    return await client.tts.convert(text)

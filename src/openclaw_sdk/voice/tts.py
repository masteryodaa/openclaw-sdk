"""Text-to-speech provider abstractions and concrete implementations.

Provides :class:`TTSProvider` (abstract base) and ready-to-use wrappers for
OpenAI TTS and ElevenLabs APIs.  All providers use :mod:`httpx` for async
HTTP calls.
"""
from __future__ import annotations

import abc

import httpx
import structlog

logger = structlog.get_logger(__name__)


class TTSProvider(abc.ABC):
    """Abstract base class for text-to-speech providers."""

    @abc.abstractmethod
    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> bytes:
        """Synthesize *text* into audio bytes.

        Args:
            text: The text to convert to speech.
            voice: Optional voice override (provider-specific).

        Returns:
            Raw audio bytes (format depends on the provider).

        Raises:
            httpx.HTTPStatusError: On non-2xx API responses.
        """


class OpenAITTS(TTSProvider):
    """OpenAI text-to-speech provider.

    Calls the ``/audio/speech`` endpoint with a JSON body.

    Args:
        api_key: OpenAI API key.
        model: TTS model name (default ``"tts-1"``).
        voice: Default voice (default ``"alloy"``).
        base_url: API base URL (default ``"https://api.openai.com/v1"``).
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "tts-1",
        voice: str = "alloy",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._base_url = base_url.rstrip("/")

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> bytes:
        """Synthesize text using the OpenAI TTS API.

        Posts JSON to ``/audio/speech`` and returns the raw audio bytes.

        Args:
            text: Text to synthesize.
            voice: Voice override; uses the default from ``__init__`` if ``None``.

        Returns:
            Raw audio bytes (MP3 by default).
        """
        url = f"{self._base_url}/audio/speech"
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": text,
            "voice": voice or self._voice,
        }

        logger.debug(
            "openai_tts_request",
            url=url,
            model=self._model,
            voice=voice or self._voice,
            text_length=len(text),
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            audio_bytes = response.content

        logger.debug("openai_tts_response", audio_size=len(audio_bytes))
        return audio_bytes


class ElevenLabsTTS(TTSProvider):
    """ElevenLabs text-to-speech provider.

    Calls the ``/text-to-speech/{voice_id}`` endpoint with a JSON body.

    Args:
        api_key: ElevenLabs API key.
        voice_id: Default voice ID (default ``"21m00Tcm4TlvDq8ikWAM"`` — Rachel).
        model_id: Model identifier (default ``"eleven_monolingual_v1"``).
        base_url: API base URL (default ``"https://api.elevenlabs.io/v1"``).
    """

    def __init__(
        self,
        api_key: str,
        *,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_monolingual_v1",
        base_url: str = "https://api.elevenlabs.io/v1",
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self._base_url = base_url.rstrip("/")

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> bytes:
        """Synthesize text using the ElevenLabs API.

        Posts JSON to ``/text-to-speech/{voice_id}`` and returns audio bytes.

        Args:
            text: Text to synthesize.
            voice: Voice ID override; uses the default ``voice_id`` if ``None``.

        Returns:
            Raw audio bytes (MP3 by default).
        """
        vid = voice or self._voice_id
        url = f"{self._base_url}/text-to-speech/{vid}"
        headers: dict[str, str] = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self._model_id,
        }

        logger.debug(
            "elevenlabs_tts_request",
            url=url,
            voice_id=vid,
            model_id=self._model_id,
            text_length=len(text),
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            audio_bytes = response.content

        logger.debug("elevenlabs_tts_response", audio_size=len(audio_bytes))
        return audio_bytes

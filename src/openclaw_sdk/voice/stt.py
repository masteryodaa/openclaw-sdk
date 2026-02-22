"""Speech-to-text provider abstractions and concrete implementations.

Provides :class:`STTProvider` (abstract base) and ready-to-use wrappers for
OpenAI Whisper and Deepgram Nova APIs.  All providers use :mod:`httpx` for
async HTTP calls.
"""
from __future__ import annotations

import abc
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class STTProvider(abc.ABC):
    """Abstract base class for speech-to-text providers."""

    @abc.abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
    ) -> str:
        """Transcribe *audio_bytes* to text.

        Args:
            audio_bytes: Raw audio data (e.g. WAV, MP3, OGG).
            language: Optional BCP-47 language hint (e.g. ``"en"``).

        Returns:
            The transcribed text.

        Raises:
            httpx.HTTPStatusError: On non-2xx API responses.
        """


class WhisperSTT(STTProvider):
    """OpenAI Whisper speech-to-text provider.

    Calls the ``/audio/transcriptions`` endpoint with multipart form data.

    Args:
        api_key: OpenAI API key.
        model: Whisper model name (default ``"whisper-1"``).
        base_url: API base URL (default ``"https://api.openai.com/v1"``).
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "whisper-1",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
    ) -> str:
        """Transcribe audio using the OpenAI Whisper API.

        Posts multipart form data to ``/audio/transcriptions``.

        Args:
            audio_bytes: Raw audio data.
            language: Optional language hint.

        Returns:
            Transcribed text string.
        """
        url = f"{self._base_url}/audio/transcriptions"
        headers: dict[str, str] = {"Authorization": f"Bearer {self._api_key}"}

        data: dict[str, Any] = {"model": self._model}
        if language is not None:
            data["language"] = language

        files: dict[str, tuple[str, bytes, str]] = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
        }

        logger.debug(
            "whisper_stt_request",
            url=url,
            model=self._model,
            audio_size=len(audio_bytes),
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                data=data,
                files=files,
            )
            response.raise_for_status()
            result = response.json()
            text: str = result.get("text", "")

        logger.debug("whisper_stt_response", text_length=len(text))
        return text


class DeepgramSTT(STTProvider):
    """Deepgram Nova speech-to-text provider.

    Calls the ``/listen`` endpoint with raw audio bytes in the request body.

    Args:
        api_key: Deepgram API key.
        model: Deepgram model name (default ``"nova-2"``).
        base_url: API base URL (default ``"https://api.deepgram.com/v1"``).
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "nova-2",
        base_url: str = "https://api.deepgram.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
    ) -> str:
        """Transcribe audio using the Deepgram API.

        Posts raw audio bytes to ``/listen`` with model and optional language
        as query parameters.

        Args:
            audio_bytes: Raw audio data.
            language: Optional language hint.

        Returns:
            Transcribed text string.
        """
        params: dict[str, str] = {"model": self._model}
        if language is not None:
            params["language"] = language

        url = f"{self._base_url}/listen"
        headers: dict[str, str] = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "audio/wav",
        }

        logger.debug(
            "deepgram_stt_request",
            url=url,
            model=self._model,
            audio_size=len(audio_bytes),
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                params=params,
                content=audio_bytes,
            )
            response.raise_for_status()
            result = response.json()

        # Deepgram response shape:
        # {"results": {"channels": [{"alternatives": [{"transcript": "..."}]}]}}
        channels = result.get("results", {}).get("channels", [])
        if channels:
            alternatives = channels[0].get("alternatives", [])
            if alternatives:
                text: str = alternatives[0].get("transcript", "")
                logger.debug("deepgram_stt_response", text_length=len(text))
                return text

        logger.debug("deepgram_stt_response", text_length=0)
        return ""

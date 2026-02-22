"""Voice pipeline — transcribe audio, run agent, synthesize response.

The :class:`VoicePipeline` chains an :class:`STTProvider`, an OpenClaw agent,
and an optional :class:`TTSProvider` into a single ``process()`` call that
accepts raw audio bytes and returns a :class:`VoiceResult`.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel

import structlog

from openclaw_sdk.voice.stt import STTProvider
from openclaw_sdk.voice.tts import TTSProvider

if TYPE_CHECKING:
    from openclaw_sdk.core.types import ExecutionResult

logger = structlog.get_logger(__name__)


class _AgentLike(Protocol):
    """Structural protocol for any object with an ``execute`` method."""

    async def execute(self, query: str) -> ExecutionResult: ...


class VoiceResult(BaseModel):
    """Result of a voice pipeline invocation.

    Attributes:
        transcript: The text transcribed from the input audio.
        agent_response: The agent's textual response.
        audio_bytes: Synthesized audio bytes (``None`` when TTS is skipped).
        latency_ms: Total end-to-end latency in milliseconds.
    """

    transcript: str
    agent_response: str
    audio_bytes: bytes | None = None
    latency_ms: int = 0

    model_config = {"arbitrary_types_allowed": True}


class VoicePipeline:
    """Three-stage voice pipeline: STT -> Agent -> TTS.

    Args:
        agent: An agent-like object (anything with
            ``async execute(query) -> ExecutionResult``).
        stt: A speech-to-text provider.
        tts: An optional text-to-speech provider.  When ``None``, the
            pipeline returns text-only results.

    Example::

        from openclaw_sdk.voice import VoicePipeline, WhisperSTT, OpenAITTS

        pipeline = VoicePipeline(
            agent=agent,
            stt=WhisperSTT(api_key="sk-..."),
            tts=OpenAITTS(api_key="sk-..."),
        )
        result = await pipeline.process(audio_bytes)
        print(result.transcript)        # "What is the weather?"
        print(result.agent_response)    # "It's sunny in San Francisco."
        print(len(result.audio_bytes))  # 24576
    """

    def __init__(
        self,
        agent: _AgentLike,
        *,
        stt: STTProvider,
        tts: TTSProvider | None = None,
    ) -> None:
        self._agent = agent
        self._stt = stt
        self._tts = tts

    async def process(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
        synthesize: bool = True,
    ) -> VoiceResult:
        """Run the full voice pipeline.

        Args:
            audio_bytes: Raw input audio to transcribe.
            language: Optional language hint passed to the STT provider.
            synthesize: Whether to run TTS on the agent response.  Ignored
                when no TTS provider was configured.

        Returns:
            A :class:`VoiceResult` with transcript, response, and optional audio.

        Raises:
            Exception: Propagates any exception from the STT provider, agent,
                or TTS provider.
        """
        t0 = time.monotonic()

        # Step 1: Speech-to-text
        logger.debug("voice_pipeline_stt_start", audio_size=len(audio_bytes))
        transcript = await self._stt.transcribe(audio_bytes, language=language)
        logger.debug("voice_pipeline_stt_done", transcript_length=len(transcript))

        # Step 2: Agent execution
        logger.debug("voice_pipeline_agent_start", transcript=transcript)
        result = await self._agent.execute(transcript)
        agent_response = result.content
        logger.debug(
            "voice_pipeline_agent_done",
            response_length=len(agent_response),
        )

        # Step 3: Text-to-speech (optional)
        audio_out: bytes | None = None
        if synthesize and self._tts is not None:
            logger.debug(
                "voice_pipeline_tts_start",
                text_length=len(agent_response),
            )
            audio_out = await self._tts.synthesize(agent_response)
            logger.debug("voice_pipeline_tts_done", audio_size=len(audio_out))

        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.debug("voice_pipeline_complete", latency_ms=latency_ms)

        return VoiceResult(
            transcript=transcript,
            agent_response=agent_response,
            audio_bytes=audio_out,
            latency_ms=latency_ms,
        )

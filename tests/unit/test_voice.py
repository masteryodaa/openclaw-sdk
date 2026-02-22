"""Tests for voice/ — STT providers, TTS providers, and VoicePipeline."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.voice.pipeline import VoicePipeline, VoiceResult
from openclaw_sdk.voice.stt import DeepgramSTT, STTProvider, WhisperSTT
from openclaw_sdk.voice.tts import ElevenLabsTTS, OpenAITTS, TTSProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_AUDIO = b"\x00\x01\x02\x03" * 100  # 400 bytes of fake audio
FAKE_RESPONSE_AUDIO = b"\xff\xfe\xfd" * 200  # 600 bytes of fake TTS audio


class _MockResponse:
    """Minimal stand-in for httpx.Response used in monkeypatching."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        content: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.com")
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=request,
                response=httpx.Response(self.status_code, request=request),
            )

    def json(self) -> dict[str, Any]:
        return self._json_data or {}


async def _make_agent() -> tuple[OpenClawClient, MockGateway]:
    """Create a connected MockGateway client and return (client, mock)."""
    mock = MockGateway()
    await mock.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    return client, mock


# ---------------------------------------------------------------------------
# STT — WhisperSTT
# ---------------------------------------------------------------------------


async def test_whisper_stt_transcribe(monkeypatch: pytest.MonkeyPatch) -> None:
    """WhisperSTT sends multipart POST and returns transcript text."""
    whisper = WhisperSTT(api_key="sk-test", model="whisper-1")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        assert "/audio/transcriptions" in url
        assert "files" in kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
        return _MockResponse(json_data={"text": "Hello from Whisper"})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await whisper.transcribe(FAKE_AUDIO)
    assert result == "Hello from Whisper"


async def test_whisper_stt_with_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """WhisperSTT passes language hint in form data."""
    whisper = WhisperSTT(api_key="sk-test")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        assert kwargs["data"]["language"] == "es"
        return _MockResponse(json_data={"text": "Hola"})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await whisper.transcribe(FAKE_AUDIO, language="es")
    assert result == "Hola"


async def test_whisper_stt_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """WhisperSTT raises on non-2xx response."""
    whisper = WhisperSTT(api_key="sk-bad")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        return _MockResponse(status_code=401)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    with pytest.raises(httpx.HTTPStatusError):
        await whisper.transcribe(FAKE_AUDIO)


# ---------------------------------------------------------------------------
# STT — DeepgramSTT
# ---------------------------------------------------------------------------


async def test_deepgram_stt_transcribe(monkeypatch: pytest.MonkeyPatch) -> None:
    """DeepgramSTT sends audio bytes in body and returns transcript."""
    deepgram = DeepgramSTT(api_key="dg-test", model="nova-2")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        assert "/listen" in url
        assert kwargs["headers"]["Authorization"] == "Token dg-test"
        assert kwargs["content"] == FAKE_AUDIO
        return _MockResponse(
            json_data={
                "results": {
                    "channels": [
                        {"alternatives": [{"transcript": "Hello from Deepgram"}]}
                    ]
                }
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await deepgram.transcribe(FAKE_AUDIO)
    assert result == "Hello from Deepgram"


async def test_deepgram_stt_with_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """DeepgramSTT passes language as query parameter."""
    deepgram = DeepgramSTT(api_key="dg-test")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        assert kwargs["params"]["language"] == "fr"
        return _MockResponse(
            json_data={
                "results": {
                    "channels": [
                        {"alternatives": [{"transcript": "Bonjour"}]}
                    ]
                }
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await deepgram.transcribe(FAKE_AUDIO, language="fr")
    assert result == "Bonjour"


async def test_deepgram_stt_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """DeepgramSTT returns empty string when response has no alternatives."""
    deepgram = DeepgramSTT(api_key="dg-test")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        return _MockResponse(json_data={"results": {"channels": []}})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await deepgram.transcribe(FAKE_AUDIO)
    assert result == ""


async def test_deepgram_stt_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """DeepgramSTT raises on non-2xx response."""
    deepgram = DeepgramSTT(api_key="dg-bad")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        return _MockResponse(status_code=500)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    with pytest.raises(httpx.HTTPStatusError):
        await deepgram.transcribe(FAKE_AUDIO)


# ---------------------------------------------------------------------------
# TTS — OpenAITTS
# ---------------------------------------------------------------------------


async def test_openai_tts_synthesize(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAITTS sends JSON POST and returns audio bytes."""
    tts = OpenAITTS(api_key="sk-test", model="tts-1", voice="alloy")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        assert "/audio/speech" in url
        assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
        body = kwargs["json"]
        assert body["model"] == "tts-1"
        assert body["voice"] == "alloy"
        assert body["input"] == "Hello there"
        return _MockResponse(content=FAKE_RESPONSE_AUDIO)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await tts.synthesize("Hello there")
    assert result == FAKE_RESPONSE_AUDIO


async def test_openai_tts_voice_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAITTS uses per-call voice override."""
    tts = OpenAITTS(api_key="sk-test", voice="alloy")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        assert kwargs["json"]["voice"] == "nova"
        return _MockResponse(content=FAKE_RESPONSE_AUDIO)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await tts.synthesize("Hi", voice="nova")
    assert result == FAKE_RESPONSE_AUDIO


async def test_openai_tts_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAITTS raises on non-2xx response."""
    tts = OpenAITTS(api_key="sk-bad")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        return _MockResponse(status_code=429)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    with pytest.raises(httpx.HTTPStatusError):
        await tts.synthesize("Hello")


# ---------------------------------------------------------------------------
# TTS — ElevenLabsTTS
# ---------------------------------------------------------------------------


async def test_elevenlabs_tts_synthesize(monkeypatch: pytest.MonkeyPatch) -> None:
    """ElevenLabsTTS sends JSON POST to /text-to-speech/{voice_id}."""
    tts = ElevenLabsTTS(api_key="el-test", voice_id="abc123")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        assert "/text-to-speech/abc123" in url
        assert kwargs["headers"]["xi-api-key"] == "el-test"
        body = kwargs["json"]
        assert body["text"] == "Synthesize me"
        assert body["model_id"] == "eleven_monolingual_v1"
        return _MockResponse(content=FAKE_RESPONSE_AUDIO)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await tts.synthesize("Synthesize me")
    assert result == FAKE_RESPONSE_AUDIO


async def test_elevenlabs_tts_voice_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """ElevenLabsTTS uses per-call voice ID override."""
    tts = ElevenLabsTTS(api_key="el-test", voice_id="default-id")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        assert "/text-to-speech/custom-id" in url
        return _MockResponse(content=FAKE_RESPONSE_AUDIO)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    result = await tts.synthesize("Hello", voice="custom-id")
    assert result == FAKE_RESPONSE_AUDIO


async def test_elevenlabs_tts_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """ElevenLabsTTS raises on non-2xx response."""
    tts = ElevenLabsTTS(api_key="el-bad")

    async def mock_post(
        self: Any, url: str, **kwargs: Any
    ) -> _MockResponse:
        return _MockResponse(status_code=503)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    with pytest.raises(httpx.HTTPStatusError):
        await tts.synthesize("Hello")


# ---------------------------------------------------------------------------
# VoicePipeline — end-to-end
# ---------------------------------------------------------------------------


async def test_voice_pipeline_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """VoicePipeline runs STT -> Agent -> TTS and returns VoiceResult."""
    client, mock = await _make_agent()

    mock.register("chat.send", {"runId": "r1", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": "The weather is sunny."}},
        )
    )

    agent = client.get_agent("voice-bot")

    # Create mock STT and TTS
    mock_stt = AsyncMock(spec=STTProvider)
    mock_stt.transcribe = AsyncMock(return_value="What is the weather?")

    mock_tts = AsyncMock(spec=TTSProvider)
    mock_tts.synthesize = AsyncMock(return_value=FAKE_RESPONSE_AUDIO)

    pipeline = VoicePipeline(agent, stt=mock_stt, tts=mock_tts)
    result = await pipeline.process(FAKE_AUDIO)

    assert result.transcript == "What is the weather?"
    assert result.agent_response == "The weather is sunny."
    assert result.audio_bytes == FAKE_RESPONSE_AUDIO
    assert result.latency_ms >= 0

    mock_stt.transcribe.assert_called_once_with(FAKE_AUDIO, language=None)
    mock_tts.synthesize.assert_called_once_with("The weather is sunny.")

    await client.close()


async def test_voice_pipeline_no_tts_provider() -> None:
    """VoicePipeline without TTS provider returns None audio_bytes."""
    client, mock = await _make_agent()

    mock.register("chat.send", {"runId": "r2", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": "Noted."}},
        )
    )

    agent = client.get_agent("voice-bot")

    mock_stt = AsyncMock(spec=STTProvider)
    mock_stt.transcribe = AsyncMock(return_value="Take a note")

    pipeline = VoicePipeline(agent, stt=mock_stt, tts=None)
    result = await pipeline.process(FAKE_AUDIO)

    assert result.transcript == "Take a note"
    assert result.agent_response == "Noted."
    assert result.audio_bytes is None

    await client.close()


async def test_voice_pipeline_synthesize_false() -> None:
    """VoicePipeline with synthesize=False skips TTS even if provider exists."""
    client, mock = await _make_agent()

    mock.register("chat.send", {"runId": "r3", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": "Skipping TTS."}},
        )
    )

    agent = client.get_agent("voice-bot")

    mock_stt = AsyncMock(spec=STTProvider)
    mock_stt.transcribe = AsyncMock(return_value="Hello")

    mock_tts = AsyncMock(spec=TTSProvider)
    mock_tts.synthesize = AsyncMock(return_value=FAKE_RESPONSE_AUDIO)

    pipeline = VoicePipeline(agent, stt=mock_stt, tts=mock_tts)
    result = await pipeline.process(FAKE_AUDIO, synthesize=False)

    assert result.transcript == "Hello"
    assert result.agent_response == "Skipping TTS."
    assert result.audio_bytes is None

    mock_tts.synthesize.assert_not_called()

    await client.close()


async def test_voice_pipeline_stt_failure() -> None:
    """VoicePipeline propagates STT provider errors."""
    client, mock = await _make_agent()

    mock.register("chat.send", {"runId": "r4", "status": "started"})
    agent = client.get_agent("voice-bot")

    mock_stt = AsyncMock(spec=STTProvider)
    mock_stt.transcribe = AsyncMock(side_effect=RuntimeError("STT failed"))

    pipeline = VoicePipeline(agent, stt=mock_stt)

    with pytest.raises(RuntimeError, match="STT failed"):
        await pipeline.process(FAKE_AUDIO)

    await client.close()


async def test_voice_pipeline_agent_failure() -> None:
    """VoicePipeline propagates agent execution errors."""
    client, mock = await _make_agent()

    mock.register("chat.send", {"runId": "r5", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.ERROR,
            data={"payload": {"message": "Agent exploded"}},
        )
    )

    agent = client.get_agent("voice-bot")

    mock_stt = AsyncMock(spec=STTProvider)
    mock_stt.transcribe = AsyncMock(return_value="Hello")

    pipeline = VoicePipeline(agent, stt=mock_stt)

    with pytest.raises(Exception):
        await pipeline.process(FAKE_AUDIO)

    await client.close()


async def test_voice_pipeline_tts_failure() -> None:
    """VoicePipeline propagates TTS provider errors."""
    client, mock = await _make_agent()

    mock.register("chat.send", {"runId": "r6", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": "All good."}},
        )
    )

    agent = client.get_agent("voice-bot")

    mock_stt = AsyncMock(spec=STTProvider)
    mock_stt.transcribe = AsyncMock(return_value="Speak to me")

    mock_tts = AsyncMock(spec=TTSProvider)
    mock_tts.synthesize = AsyncMock(side_effect=RuntimeError("TTS failed"))

    pipeline = VoicePipeline(agent, stt=mock_stt, tts=mock_tts)

    with pytest.raises(RuntimeError, match="TTS failed"):
        await pipeline.process(FAKE_AUDIO)

    await client.close()


async def test_voice_pipeline_language_passthrough() -> None:
    """VoicePipeline passes language hint to STT provider."""
    client, mock = await _make_agent()

    mock.register("chat.send", {"runId": "r7", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": "Respuesta"}},
        )
    )

    agent = client.get_agent("voice-bot")

    mock_stt = AsyncMock(spec=STTProvider)
    mock_stt.transcribe = AsyncMock(return_value="Pregunta")

    pipeline = VoicePipeline(agent, stt=mock_stt)
    result = await pipeline.process(FAKE_AUDIO, language="es")

    mock_stt.transcribe.assert_called_once_with(FAKE_AUDIO, language="es")
    assert result.transcript == "Pregunta"

    await client.close()


# ---------------------------------------------------------------------------
# VoiceResult model
# ---------------------------------------------------------------------------


def test_voice_result_model() -> None:
    """VoiceResult is a valid Pydantic model with expected fields."""
    vr = VoiceResult(
        transcript="Hello",
        agent_response="Hi there",
        audio_bytes=b"\x00\x01",
        latency_ms=42,
    )
    assert vr.transcript == "Hello"
    assert vr.agent_response == "Hi there"
    assert vr.audio_bytes == b"\x00\x01"
    assert vr.latency_ms == 42


def test_voice_result_none_audio() -> None:
    """VoiceResult audio_bytes defaults to None."""
    vr = VoiceResult(transcript="T", agent_response="R")
    assert vr.audio_bytes is None
    assert vr.latency_ms == 0

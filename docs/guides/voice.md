# Voice Pipeline

The OpenClaw SDK includes a voice processing module that chains speech-to-text (STT),
agent execution, and text-to-speech (TTS) into a single pipeline. Feed in raw audio
bytes and get back a transcription, the agent's textual response, and optionally
synthesized audio -- all in one `await pipeline.process()` call.

The module ships with concrete providers for OpenAI Whisper, Deepgram Nova, OpenAI TTS,
and ElevenLabs, plus abstract base classes for plugging in your own STT/TTS services.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.voice import VoicePipeline, WhisperSTT, OpenAITTS

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")

        pipeline = VoicePipeline(
            agent,
            stt=WhisperSTT(api_key="sk-..."),
            tts=OpenAITTS(api_key="sk-..."),
        )

        # Read audio from a file
        with open("question.wav", "rb") as f:
            audio_bytes = f.read()

        result = await pipeline.process(audio_bytes)
        print(f"Transcript: {result.transcript}")
        print(f"Response:   {result.agent_response}")
        print(f"Latency:    {result.latency_ms}ms")

        # Save synthesized audio
        if result.audio_bytes:
            with open("response.mp3", "wb") as f:
                f.write(result.audio_bytes)

asyncio.run(main())
```

## How It Works

The `VoicePipeline` executes three stages sequentially:

1. **STT** -- The `STTProvider` transcribes raw audio bytes into text.
2. **Agent** -- The transcribed text is passed to `agent.execute()` as the query.
3. **TTS** -- The agent's response text is synthesized back into audio bytes by the
   `TTSProvider` (optional).

```
Audio In -> [STTProvider] -> Text -> [Agent] -> Response Text -> [TTSProvider] -> Audio Out
```

## STT Providers

All STT providers implement the `STTProvider` abstract base class, which defines a single
method:

```python
class STTProvider(abc.ABC):
    @abc.abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
    ) -> str: ...
```

### WhisperSTT

Uses the OpenAI Whisper API (`/audio/transcriptions` endpoint) with multipart form data.

```python
from openclaw_sdk.voice import WhisperSTT

stt = WhisperSTT(
    api_key="sk-...",
    model="whisper-1",
    base_url="https://api.openai.com/v1",
)

transcript = await stt.transcribe(audio_bytes, language="en")
```

| Parameter  | Type  | Default                        | Description                     |
|------------|-------|--------------------------------|---------------------------------|
| `api_key`  | `str` | *required*                     | OpenAI API key                  |
| `model`    | `str` | `"whisper-1"`                  | Whisper model name              |
| `base_url` | `str` | `"https://api.openai.com/v1"`  | API base URL                    |

### DeepgramSTT

Uses the Deepgram Nova API (`/listen` endpoint) with raw audio bytes in the request body.

```python
from openclaw_sdk.voice import DeepgramSTT

stt = DeepgramSTT(
    api_key="dg-...",
    model="nova-2",
)

transcript = await stt.transcribe(audio_bytes, language="en")
```

| Parameter  | Type  | Default                            | Description                |
|------------|-------|------------------------------------|----------------------------|
| `api_key`  | `str` | *required*                         | Deepgram API key           |
| `model`    | `str` | `"nova-2"`                         | Deepgram model name        |
| `base_url` | `str` | `"https://api.deepgram.com/v1"`    | API base URL               |

!!! tip "Language hints"
    Both providers accept an optional `language` parameter (BCP-47 code like `"en"`,
    `"fr"`, `"de"`). Providing a language hint can improve transcription accuracy,
    especially for short audio clips.

## TTS Providers

All TTS providers implement the `TTSProvider` abstract base class:

```python
class TTSProvider(abc.ABC):
    @abc.abstractmethod
    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> bytes: ...
```

### OpenAITTS

Uses the OpenAI TTS API (`/audio/speech` endpoint). Returns MP3 audio bytes by default.

```python
from openclaw_sdk.voice import OpenAITTS

tts = OpenAITTS(
    api_key="sk-...",
    model="tts-1",
    voice="alloy",
)

audio = await tts.synthesize("Hello, how can I help you?")
```

| Parameter  | Type  | Default                        | Description                          |
|------------|-------|--------------------------------|--------------------------------------|
| `api_key`  | `str` | *required*                     | OpenAI API key                       |
| `model`    | `str` | `"tts-1"`                      | TTS model name                       |
| `voice`    | `str` | `"alloy"`                      | Default voice (`alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`) |
| `base_url` | `str` | `"https://api.openai.com/v1"`  | API base URL                         |

### ElevenLabsTTS

Uses the ElevenLabs API (`/text-to-speech/{voice_id}` endpoint). Returns MP3 audio bytes
by default.

```python
from openclaw_sdk.voice import ElevenLabsTTS

tts = ElevenLabsTTS(
    api_key="el-...",
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
    model_id="eleven_monolingual_v1",
)

audio = await tts.synthesize("Here is your answer.", voice="custom-voice-id")
```

| Parameter  | Type  | Default                            | Description                           |
|------------|-------|------------------------------------|---------------------------------------|
| `api_key`  | `str` | *required*                         | ElevenLabs API key                    |
| `voice_id` | `str` | `"21m00Tcm4TlvDq8ikWAM"` (Rachel) | Default voice ID                      |
| `model_id` | `str` | `"eleven_monolingual_v1"`          | ElevenLabs model identifier           |
| `base_url` | `str` | `"https://api.elevenlabs.io/v1"`   | API base URL                          |

!!! tip "Voice override"
    All TTS providers accept a `voice` parameter on `synthesize()` that overrides the
    default voice configured in the constructor. This lets you switch voices per-call
    without creating multiple provider instances.

## VoicePipeline

The `VoicePipeline` wires together an STT provider, an agent, and an optional TTS
provider into a single processing call.

```python
from openclaw_sdk.voice import VoicePipeline, WhisperSTT, ElevenLabsTTS

pipeline = VoicePipeline(
    agent,
    stt=WhisperSTT(api_key="sk-..."),
    tts=ElevenLabsTTS(api_key="el-..."),
)
```

| Parameter | Type                  | Default    | Description                                      |
|-----------|-----------------------|------------|--------------------------------------------------|
| `agent`   | `Agent` (or any `_AgentLike`) | *required* | Agent with an `execute(query)` method     |
| `stt`     | `STTProvider`         | *required* | Speech-to-text provider                          |
| `tts`     | `TTSProvider \| None` | `None`     | Text-to-speech provider (omit for text-only)     |

### Processing Audio

```python
result = await pipeline.process(
    audio_bytes,
    language="en",
    synthesize=True,
)
```

| Parameter    | Type            | Default | Description                                             |
|--------------|-----------------|---------|---------------------------------------------------------|
| `audio_bytes`| `bytes`         | *required* | Raw input audio to transcribe (WAV, MP3, OGG, etc.) |
| `language`   | `str \| None`   | `None`  | Language hint passed to the STT provider                |
| `synthesize` | `bool`          | `True`  | Whether to run TTS on the response (ignored if no TTS configured) |

## VoiceResult

The `process()` method returns a `VoiceResult` model:

```python
result = await pipeline.process(audio_bytes)

print(result.transcript)       # "What is the weather today?"
print(result.agent_response)   # "It's sunny in San Francisco."
print(result.latency_ms)       # 1523
print(len(result.audio_bytes)) # 24576 (or None if TTS was skipped)
```

| Field            | Type           | Description                                        |
|------------------|----------------|----------------------------------------------------|
| `transcript`     | `str`          | Text transcribed from the input audio              |
| `agent_response` | `str`          | The agent's textual response                       |
| `audio_bytes`    | `bytes \| None`| Synthesized audio bytes (`None` when TTS is skipped) |
| `latency_ms`     | `int`          | Total end-to-end latency in milliseconds           |

## Text-Only Mode

If you only need STT + agent processing without audio synthesis, omit the TTS provider:

```python
pipeline = VoicePipeline(
    agent,
    stt=WhisperSTT(api_key="sk-..."),
    # No TTS -- text-only mode
)

result = await pipeline.process(audio_bytes)
print(result.transcript)       # Transcribed text
print(result.agent_response)   # Agent response
print(result.audio_bytes)      # None
```

You can also disable synthesis on a per-call basis:

```python
pipeline = VoicePipeline(agent, stt=stt, tts=tts)
result = await pipeline.process(audio_bytes, synthesize=False)
print(result.audio_bytes)  # None (TTS was skipped for this call)
```

## Custom Providers

To integrate a custom STT or TTS service, subclass the abstract base class:

```python
from openclaw_sdk.voice import STTProvider, TTSProvider

class MyCustomSTT(STTProvider):
    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
    ) -> str:
        # Call your custom transcription API
        ...

class MyCustomTTS(TTSProvider):
    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
    ) -> bytes:
        # Call your custom synthesis API
        ...

# Use with VoicePipeline
pipeline = VoicePipeline(
    agent,
    stt=MyCustomSTT(),
    tts=MyCustomTTS(),
)
```

!!! warning "Error propagation"
    The `VoicePipeline` does not catch exceptions from providers or the agent. If the
    STT API returns a non-2xx status or the agent execution fails, the exception
    propagates to the caller. Wrap `pipeline.process()` in a try/except for
    production use.

# Text-to-Speech

The `TTSManager` provides gateway-level control over OpenClaw's text-to-speech
system. Enable or disable TTS, switch providers, and convert text to audio —
all via gateway RPC.

!!! note
    This guide covers **gateway TTS operations** (enabling, providers, conversion).
    For building full audio-in/audio-out pipelines with STT + Agent + TTS, see
    the [Voice Pipeline](voice.md) guide.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        tts = client.tts

        # Check current TTS status
        status = await tts.status()
        print(f"TTS enabled: {status.get('enabled')}")
        print(f"Provider: {status.get('provider')}")

        # Enable TTS
        await tts.enable()

        # List available providers
        providers = await tts.providers()
        print(f"Available: {providers.get('providers')}")

asyncio.run(main())
```

## Enabling and Disabling

Toggle TTS on the gateway. When disabled, TTS conversion requests are rejected.

```python
# Enable
result = await client.tts.enable()
# {'enabled': True}

# Disable
result = await client.tts.disable()
# {'enabled': False}
```

## Checking Status

```python
status = await client.tts.status()
# {
#   'enabled': True,
#   'provider': 'edge',
#   'voice': '...',
#   ...
# }
```

## Switching Providers

OpenClaw supports multiple TTS providers. Use `set_provider()` to switch:

```python
await client.tts.set_provider("edge")       # Microsoft Edge TTS (free)
await client.tts.set_provider("openai")      # OpenAI TTS
await client.tts.set_provider("elevenlabs")  # ElevenLabs
```

!!! tip
    Use `providers()` to discover which providers are configured on your gateway
    before switching.

## Listing Providers

```python
result = await client.tts.providers()
for provider in result.get("providers", []):
    print(f"{provider['name']} — {provider.get('description', '')}")
```

## Converting Text to Speech

```python
audio = await client.tts.convert("Hello, this is OpenClaw speaking!")
# Returns audio data dict from the gateway
```

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        tts = client.tts

        # Enable TTS and pick a provider
        await tts.enable()
        await tts.set_provider("edge")

        # Verify configuration
        status = await tts.status()
        print(f"Provider: {status.get('provider')}")
        print(f"Enabled: {status.get('enabled')}")

        # List all available providers
        providers = await tts.providers()
        for p in providers.get("providers", []):
            print(f"  - {p['name']}")

        # Convert text
        audio = await tts.convert("The daily report is ready.")
        print(f"Audio data received: {type(audio)}")

        # Disable when done
        await tts.disable()

asyncio.run(main())
```

## API Reference

::: openclaw_sdk.tts.manager.TTSManager
    options:
      show_source: false

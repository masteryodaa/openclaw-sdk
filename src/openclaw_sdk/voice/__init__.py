"""Voice pipeline module — STT, TTS, and end-to-end voice processing.

This module provides speech-to-text and text-to-speech provider abstractions
with concrete implementations for OpenAI Whisper, Deepgram, OpenAI TTS, and
ElevenLabs.  The :class:`VoicePipeline` chains them together with an OpenClaw
agent for audio-in / audio-out workflows.
"""
from __future__ import annotations

from openclaw_sdk.voice.pipeline import VoicePipeline, VoiceResult
from openclaw_sdk.voice.stt import DeepgramSTT, STTProvider, WhisperSTT
from openclaw_sdk.voice.tts import ElevenLabsTTS, OpenAITTS, TTSProvider

__all__ = [
    "DeepgramSTT",
    "ElevenLabsTTS",
    "OpenAITTS",
    "STTProvider",
    "TTSProvider",
    "VoicePipeline",
    "VoiceResult",
    "WhisperSTT",
]

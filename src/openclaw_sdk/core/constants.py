from __future__ import annotations

from enum import StrEnum


class GatewayMode(StrEnum):
    LOCAL = "local"
    PROTOCOL = "protocol"
    OPENAI_COMPAT = "openai_compat"
    DOCKER = "docker"  # Future
    AUTO = "auto"


class AgentStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    IDLE = "idle"
    ERROR = "error"
    DELETED = "deleted"


class EventType(StrEnum):
    # SDK-level event types (used in MockGateway and tests)
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_GENERATED = "file_generated"
    CONTENT = "content"
    ERROR = "error"
    DONE = "done"

    # Real gateway event types (from live OpenClaw protocol)
    AGENT = "agent"
    CHAT = "chat"
    PRESENCE = "presence"
    HEALTH = "health"
    TICK = "tick"
    HEARTBEAT = "heartbeat"
    CRON = "cron"
    SHUTDOWN = "shutdown"


class ChannelType(StrEnum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    SIGNAL = "signal"
    IMESSAGE = "imessage"
    SMS = "sms"
    TEAMS = "teams"
    GOOGLE_CHAT = "google_chat"
    MATRIX = "matrix"
    ZALO = "zalo"
    CUSTOM = "custom"


class MemoryBackend(StrEnum):
    LOCAL = "memory"
    REDIS = "redis"
    QDRANT = "qdrant"
    CHROMA = "chroma"
    PGVECTOR = "pgvector"

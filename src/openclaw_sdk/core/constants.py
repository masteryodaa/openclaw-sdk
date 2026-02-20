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
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_GENERATED = "file_generated"
    CONTENT = "content"
    ERROR = "error"
    DONE = "done"


class ChannelType(StrEnum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    SIGNAL = "signal"
    IMESSAGE = "imessage"
    TEAMS = "teams"
    GOOGLE_CHAT = "google_chat"
    MATRIX = "matrix"
    ZALO = "zalo"
    CUSTOM = "custom"


class ToolType(StrEnum):
    DATABASE = "database"
    FILES = "files"
    BROWSER = "browser"
    SHELL = "shell"
    WEB_SEARCH = "web_search"
    CUSTOM = "custom"


class MemoryBackend(StrEnum):
    LOCAL = "memory"
    REDIS = "redis"
    QDRANT = "qdrant"
    CHROMA = "chroma"
    PGVECTOR = "pgvector"

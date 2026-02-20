from __future__ import annotations

from pydantic import BaseModel

from openclaw_sdk.core.constants import MemoryBackend


class MemoryConfig(BaseModel):
    backend: MemoryBackend = MemoryBackend.LOCAL
    connection_string: str | None = None
    collection_name: str | None = None
    embedding_model: str | None = None
    ttl_seconds: int | None = None
    max_history: int = 100

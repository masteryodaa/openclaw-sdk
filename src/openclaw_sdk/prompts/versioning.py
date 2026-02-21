"""Prompt versioning — store, retrieve, compare, and rollback prompt versions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class PromptVersion(BaseModel):
    """A single versioned snapshot of a prompt."""

    version: int
    content: str
    hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute a short SHA-256 hash of the prompt content."""
        return hashlib.sha256(content.encode()).hexdigest()[:12]


class PromptStore:
    """In-memory versioned prompt store with tagging and comparison.

    Example::

        store = PromptStore()
        store.save("greeter", "Hello, how can I help?")
        store.save("greeter", "Hi there! What can I do for you?", tags=["friendly"])
        latest = store.get("greeter")            # version 2
        v1 = store.get("greeter", version=1)     # version 1
        history = store.list_versions("greeter")  # [v1, v2]
        diff = store.diff("greeter", 1, 2)        # shows changes
    """

    def __init__(self) -> None:
        self._prompts: dict[str, list[PromptVersion]] = {}

    def save(
        self,
        name: str,
        content: str,
        *,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> PromptVersion:
        """Save a new version of a prompt. Returns the created version."""
        versions = self._prompts.setdefault(name, [])
        version_num = len(versions) + 1
        pv = PromptVersion(
            version=version_num,
            content=content,
            hash=PromptVersion.compute_hash(content),
            metadata=metadata or {},
            tags=tags or [],
        )
        versions.append(pv)
        return pv

    def get(self, name: str, *, version: int | None = None) -> PromptVersion:
        """Get a prompt version. Returns latest if version is None."""
        versions = self._prompts.get(name)
        if not versions:
            raise KeyError(f"Prompt '{name}' not found")
        if version is None:
            return versions[-1]
        if version < 1 or version > len(versions):
            raise KeyError(
                f"Version {version} not found for '{name}' (1-{len(versions)})"
            )
        return versions[version - 1]

    def list_versions(self, name: str) -> list[PromptVersion]:
        """List all versions of a prompt."""
        return list(self._prompts.get(name, []))

    def list_prompts(self) -> list[str]:
        """List all prompt names."""
        return sorted(self._prompts.keys())

    def get_by_tag(self, name: str, tag: str) -> list[PromptVersion]:
        """Get all versions of a prompt with a specific tag."""
        versions = self._prompts.get(name, [])
        return [v for v in versions if tag in v.tags]

    def diff(self, name: str, version_a: int, version_b: int) -> dict[str, Any]:
        """Compare two versions of a prompt."""
        a = self.get(name, version=version_a)
        b = self.get(name, version=version_b)
        return {
            "name": name,
            "version_a": version_a,
            "version_b": version_b,
            "content_a": a.content,
            "content_b": b.content,
            "same": a.hash == b.hash,
            "hash_a": a.hash,
            "hash_b": b.hash,
        }

    def rollback(self, name: str, version: int) -> PromptVersion:
        """Create a new version by copying content from an older version."""
        old = self.get(name, version=version)
        return self.save(name, old.content, tags=["rollback", f"from-v{version}"])

    def export_json(self) -> str:
        """Export all prompts to JSON."""
        data: dict[str, list[dict[str, Any]]] = {}
        for name, versions in self._prompts.items():
            data[name] = [
                {
                    "version": v.version,
                    "content": v.content,
                    "hash": v.hash,
                    "metadata": v.metadata,
                    "tags": v.tags,
                    "created_at": v.created_at.isoformat(),
                }
                for v in versions
            ]
        return json.dumps(data, indent=2)

    def import_json(self, json_str: str) -> None:
        """Import prompts from JSON (merges with existing)."""
        data: dict[str, list[dict[str, Any]]] = json.loads(json_str)
        for name, versions in data.items():
            for v in versions:
                self.save(
                    name,
                    v["content"],
                    metadata=v.get("metadata", {}),
                    tags=v.get("tags", []),
                )

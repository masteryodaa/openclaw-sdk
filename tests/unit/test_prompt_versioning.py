"""Tests for prompt versioning — PromptStore and PromptVersion."""

from __future__ import annotations

import json

import pytest

from openclaw_sdk.prompts.versioning import PromptStore, PromptVersion


class TestPromptVersion:
    """Tests for the PromptVersion model."""

    def test_compute_hash_deterministic(self) -> None:
        """Same content always produces the same hash."""
        content = "You are a helpful assistant."
        h1 = PromptVersion.compute_hash(content)
        h2 = PromptVersion.compute_hash(content)
        assert h1 == h2
        assert len(h1) == 12  # truncated sha256

    def test_compute_hash_different_content(self) -> None:
        """Different content produces different hashes."""
        h1 = PromptVersion.compute_hash("Hello")
        h2 = PromptVersion.compute_hash("Goodbye")
        assert h1 != h2


class TestPromptStore:
    """Tests for the PromptStore."""

    def test_save_and_get_latest(self) -> None:
        """Saving a prompt and retrieving it without version returns latest."""
        store = PromptStore()
        store.save("greeter", "Hello v1")
        store.save("greeter", "Hello v2")
        latest = store.get("greeter")
        assert latest.version == 2
        assert latest.content == "Hello v2"

    def test_get_specific_version(self) -> None:
        """Retrieving a specific version returns that version."""
        store = PromptStore()
        store.save("greeter", "Hello v1")
        store.save("greeter", "Hello v2")
        v1 = store.get("greeter", version=1)
        assert v1.version == 1
        assert v1.content == "Hello v1"

    def test_get_nonexistent_raises(self) -> None:
        """Getting a prompt that does not exist raises KeyError."""
        store = PromptStore()
        with pytest.raises(KeyError, match="Prompt 'missing' not found"):
            store.get("missing")

    def test_get_invalid_version_raises(self) -> None:
        """Getting an out-of-range version raises KeyError."""
        store = PromptStore()
        store.save("greeter", "Hello v1")
        with pytest.raises(KeyError, match="Version 99 not found"):
            store.get("greeter", version=99)
        with pytest.raises(KeyError, match="Version 0 not found"):
            store.get("greeter", version=0)

    def test_list_versions(self) -> None:
        """list_versions returns all versions in order."""
        store = PromptStore()
        store.save("greeter", "v1")
        store.save("greeter", "v2")
        store.save("greeter", "v3")
        versions = store.list_versions("greeter")
        assert len(versions) == 3
        assert [v.version for v in versions] == [1, 2, 3]
        assert [v.content for v in versions] == ["v1", "v2", "v3"]

    def test_list_versions_empty(self) -> None:
        """list_versions for unknown prompt returns empty list."""
        store = PromptStore()
        assert store.list_versions("nonexistent") == []

    def test_list_prompts(self) -> None:
        """list_prompts returns sorted prompt names."""
        store = PromptStore()
        store.save("zebra", "z")
        store.save("alpha", "a")
        store.save("middle", "m")
        assert store.list_prompts() == ["alpha", "middle", "zebra"]

    def test_list_prompts_empty(self) -> None:
        """list_prompts on empty store returns empty list."""
        store = PromptStore()
        assert store.list_prompts() == []

    def test_get_by_tag(self) -> None:
        """get_by_tag returns only versions matching the tag."""
        store = PromptStore()
        store.save("greeter", "formal", tags=["formal"])
        store.save("greeter", "casual", tags=["casual"])
        store.save("greeter", "formal v2", tags=["formal", "v2"])

        formal = store.get_by_tag("greeter", "formal")
        assert len(formal) == 2
        assert formal[0].content == "formal"
        assert formal[1].content == "formal v2"

    def test_get_by_tag_no_matches(self) -> None:
        """get_by_tag returns empty list when no versions match."""
        store = PromptStore()
        store.save("greeter", "hello")
        assert store.get_by_tag("greeter", "nonexistent") == []

    def test_diff_same_content(self) -> None:
        """diff reports same=True when content is identical."""
        store = PromptStore()
        store.save("greeter", "Hello!")
        store.save("greeter", "Hello!")  # same content
        result = store.diff("greeter", 1, 2)
        assert result["same"] is True
        assert result["hash_a"] == result["hash_b"]
        assert result["content_a"] == result["content_b"] == "Hello!"
        assert result["name"] == "greeter"
        assert result["version_a"] == 1
        assert result["version_b"] == 2

    def test_diff_different_content(self) -> None:
        """diff reports same=False when content differs."""
        store = PromptStore()
        store.save("greeter", "Hello!")
        store.save("greeter", "Hi there!")
        result = store.diff("greeter", 1, 2)
        assert result["same"] is False
        assert result["hash_a"] != result["hash_b"]
        assert result["content_a"] == "Hello!"
        assert result["content_b"] == "Hi there!"

    def test_rollback_creates_new_version(self) -> None:
        """rollback copies old content into a new version with rollback tags."""
        store = PromptStore()
        store.save("greeter", "Original")
        store.save("greeter", "Changed")
        rolled = store.rollback("greeter", 1)
        assert rolled.version == 3
        assert rolled.content == "Original"
        assert "rollback" in rolled.tags
        assert "from-v1" in rolled.tags
        # Confirm it is the latest
        assert store.get("greeter").version == 3

    def test_export_import_json(self) -> None:
        """export_json and import_json round-trip correctly."""
        store = PromptStore()
        store.save("greeter", "Hello!", metadata={"author": "alice"}, tags=["prod"])
        store.save("greeter", "Hi there!", tags=["staging"])
        store.save("farewell", "Goodbye!")

        exported = store.export_json()
        data = json.loads(exported)
        assert "greeter" in data
        assert "farewell" in data
        assert len(data["greeter"]) == 2
        assert len(data["farewell"]) == 1

        # Import into a fresh store
        new_store = PromptStore()
        new_store.import_json(exported)

        # Verify content was imported
        assert new_store.list_prompts() == ["farewell", "greeter"]
        g_versions = new_store.list_versions("greeter")
        assert len(g_versions) == 2
        assert g_versions[0].content == "Hello!"
        assert g_versions[0].metadata == {"author": "alice"}
        assert g_versions[0].tags == ["prod"]
        assert g_versions[1].content == "Hi there!"
        assert g_versions[1].tags == ["staging"]

    def test_save_returns_prompt_version(self) -> None:
        """save() returns the created PromptVersion with correct fields."""
        store = PromptStore()
        pv = store.save("test", "content", metadata={"k": "v"}, tags=["t1"])
        assert isinstance(pv, PromptVersion)
        assert pv.version == 1
        assert pv.content == "content"
        assert pv.hash == PromptVersion.compute_hash("content")
        assert pv.metadata == {"k": "v"}
        assert pv.tags == ["t1"]
        assert pv.created_at is not None

    def test_save_with_metadata(self) -> None:
        """Metadata is persisted on the version."""
        store = PromptStore()
        pv = store.save("x", "y", metadata={"author": "bob", "reason": "experiment"})
        retrieved = store.get("x")
        assert retrieved.metadata == {"author": "bob", "reason": "experiment"}
        assert pv.metadata == retrieved.metadata

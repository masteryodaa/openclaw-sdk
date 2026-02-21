"""Tests for I/O alignment with OpenClaw gateway protocol."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.config import ClientConfig, ExecutionOptions
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import Attachment, StreamEvent, TokenUsage
from openclaw_sdk.gateway.mock import MockGateway


class TestAttachmentToGateway:
    def test_from_base64(self) -> None:
        att = Attachment(
            file_path="test.png",
            mime_type="image/png",
            content_base64="aGVsbG8=",
        )
        result = att.to_gateway()
        assert result["mimeType"] == "image/png"
        assert result["content"] == "aGVsbG8="
        assert result["fileName"] == "test.png"

    def test_from_file(self, tmp_path: Path) -> None:
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # JPEG header
        att = Attachment(file_path=str(img), mime_type="image/jpeg")
        result = att.to_gateway()
        assert result["mimeType"] == "image/jpeg"
        decoded = base64.b64decode(result["content"])
        assert decoded[:4] == b"\xff\xd8\xff\xe0"

    def test_validates_size(self, tmp_path: Path) -> None:
        big = tmp_path / "big.png"
        big.write_bytes(b"\x00" * (6 * 1024 * 1024))  # 6MB
        att = Attachment(file_path=str(big), mime_type="image/png")
        with pytest.raises(ValueError, match="5.*MB"):
            att.to_gateway()

    def test_validates_mime_type(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"PDF content")
        att = Attachment(file_path=str(f), mime_type="application/pdf")
        with pytest.raises(ValueError, match="mime"):
            att.to_gateway()

    def test_from_path_factory(self, tmp_path: Path) -> None:
        img = tmp_path / "photo.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 50)
        att = Attachment.from_path(img)
        assert att.file_path == str(img)
        assert att.mime_type == "image/png"
        assert att.name == "photo.png"

    def test_auto_detect_mime_from_extension(self, tmp_path: Path) -> None:
        img = tmp_path / "photo.jpeg"
        img.write_bytes(b"\xff\xd8" + b"\x00" * 50)
        att = Attachment(file_path=str(img))
        result = att.to_gateway()
        assert result["mimeType"] == "image/jpeg"

    def test_type_field_matches_mime(self) -> None:
        att = Attachment(
            file_path="icon.webp",
            mime_type="image/webp",
            content_base64="AAAA",
        )
        result = att.to_gateway()
        assert result["type"] == "image/webp"
        assert result["mimeType"] == "image/webp"

    def test_name_override(self) -> None:
        att = Attachment(
            file_path="some/path/img.png",
            mime_type="image/png",
            name="custom_name.png",
            content_base64="AAAA",
        )
        result = att.to_gateway()
        assert result["fileName"] == "custom_name.png"

    def test_unknown_mime_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "noext"
        f.write_bytes(b"data")
        att = Attachment(file_path=str(f))
        with pytest.raises(ValueError, match="Cannot determine mime type"):
            att.to_gateway()


class TestExecuteSendsAttachments:
    async def test_attachments_in_params(self, tmp_path: Path) -> None:
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 50)

        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        # Pre-emit DONE event
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "done"}},
            )
        )

        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")

        options = ExecutionOptions(attachments=[Attachment.from_path(img)])
        await agent.execute("describe this image", options=options)

        # Check that chat.send was called with attachments
        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert "attachments" in params
                assert len(params["attachments"]) == 1
                assert params["attachments"][0]["mimeType"] == "image/png"
                break
        else:
            pytest.fail("chat.send not called")

    async def test_string_path_converted(self, tmp_path: Path) -> None:
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8" + b"\x00" * 50)

        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "done"}},
            )
        )

        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")

        options = ExecutionOptions(attachments=[str(img)])
        await agent.execute("describe", options=options)

        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert "attachments" in params
                break
        else:
            pytest.fail("chat.send not called")

    async def test_path_object_converted(self, tmp_path: Path) -> None:
        img = tmp_path / "test.gif"
        img.write_bytes(b"GIF89a" + b"\x00" * 50)

        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "done"}},
            )
        )

        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")

        options = ExecutionOptions(attachments=[img])  # Path object
        await agent.execute("describe", options=options)

        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert "attachments" in params
                assert params["attachments"][0]["mimeType"] == "image/gif"
                break
        else:
            pytest.fail("chat.send not called")

    async def test_no_attachments_no_key(self) -> None:
        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "done"}},
            )
        )

        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")

        await agent.execute("hello")

        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert "attachments" not in params
                break
        else:
            pytest.fail("chat.send not called")


class TestTokenUsage:
    def test_from_gateway_all_fields(self) -> None:
        data = {
            "input": 100,
            "output": 50,
            "cacheRead": 20,
            "cacheWrite": 10,
            "totalTokens": 180,
        }
        usage = TokenUsage.from_gateway(data)
        assert usage.input == 100
        assert usage.output == 50
        assert usage.cache_read == 20
        assert usage.cache_write == 10
        assert usage.total_tokens == 180

    def test_from_gateway_partial(self) -> None:
        data = {"input": 100, "output": 50}
        usage = TokenUsage.from_gateway(data)
        assert usage.cache_read == 0
        assert usage.cache_write == 0
        assert usage.total_tokens == 150  # computed from input + output

    def test_total_property(self) -> None:
        usage = TokenUsage(input=100, output=50, total_tokens=160)
        assert usage.total == 160

    def test_total_property_computed(self) -> None:
        usage = TokenUsage(input=100, output=50)
        assert usage.total == 150  # input + output when total_tokens is 0

    def test_backward_compatible(self) -> None:
        """Existing code using TokenUsage(input=10, output=5) still works."""
        usage = TokenUsage(input=10, output=5)
        assert usage.input == 10
        assert usage.output == 5
        assert usage.cache_read == 0
        assert usage.cache_write == 0

    def test_from_gateway_empty(self) -> None:
        usage = TokenUsage.from_gateway({})
        assert usage.input == 0
        assert usage.output == 0
        assert usage.total == 0


class TestChatSendParams:
    async def test_sends_thinking_param(self) -> None:
        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "result"}},
            )
        )
        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")
        options = ExecutionOptions(thinking=True)
        await agent.execute("think about this", options=options)

        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert params["thinking"] is True
                break
        else:
            pytest.fail("chat.send not called")

    async def test_sends_deliver_param(self) -> None:
        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "result"}},
            )
        )
        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")
        options = ExecutionOptions(deliver=False)
        await agent.execute("no delivery", options=options)

        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert params["deliver"] is False
                break
        else:
            pytest.fail("chat.send not called")

    async def test_sends_timeout_ms(self) -> None:
        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "result"}},
            )
        )
        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")
        options = ExecutionOptions(timeout_seconds=60)
        await agent.execute("test", options=options)

        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert params["timeoutMs"] == 60000
                break
        else:
            pytest.fail("chat.send not called")

    async def test_no_options_no_extra_params(self) -> None:
        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "result"}},
            )
        )
        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")
        await agent.execute("test")

        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert "thinking" not in params
                assert "deliver" not in params
                assert "timeoutMs" not in params
                break
        else:
            pytest.fail("chat.send not called")

    async def test_thinking_false_not_sent(self) -> None:
        mock = MockGateway()
        await mock.connect()
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"content": "result"}},
            )
        )
        client = OpenClawClient(config=ClientConfig(), gateway=mock)
        agent = client.get_agent("test")
        options = ExecutionOptions(thinking=False)
        await agent.execute("test", options=options)

        for method, params in mock.calls:
            if method == "chat.send":
                assert params is not None
                assert "thinking" not in params  # False = don't send
                break


# ------------------------------------------------------------------ #
# Helper for event processing tests
# ------------------------------------------------------------------ #


async def _exec_with_events(
    events: list[StreamEvent],
    callbacks: list[CallbackHandler] | None = None,
) -> Any:
    """Set up a mock gateway, emit events, and run agent.execute()."""
    mock = MockGateway()
    await mock.connect()
    mock.register("chat.send", {"runId": "r1", "status": "started"})
    for ev in events:
        mock.emit_event(ev)
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = client.get_agent("test")
    return await agent.execute("test", callbacks=callbacks)


def _ev(event_type: EventType, payload: dict[str, Any]) -> StreamEvent:
    """Shorthand to create a StreamEvent."""
    return StreamEvent(event_type=event_type, data={"payload": payload})


# ------------------------------------------------------------------ #
# Task 4: Event Processing Tests
# ------------------------------------------------------------------ #


class TestEventProcessing:
    async def test_thinking_events_accumulated(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.THINKING, {"thinking": "Let me think..."}),
            _ev(EventType.THINKING, {"thinking": " step 2"}),
            _ev(EventType.CONTENT, {"content": "Answer"}),
            _ev(EventType.DONE, {"content": ""}),
        ])
        assert result.thinking == "Let me think... step 2"
        assert result.content == "Answer"

    async def test_tool_call_and_result_paired(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.TOOL_CALL, {"tool": "web_search", "input": "python SDK"}),
            _ev(EventType.TOOL_RESULT, {"output": "Found 10 results"}),
            _ev(EventType.CONTENT, {"content": "Here are the results"}),
            _ev(EventType.DONE, {"content": ""}),
        ])
        assert len(result.tool_calls) == 1
        tc = result.tool_calls[0]
        assert tc.tool == "web_search"
        assert tc.input == "python SDK"
        assert tc.output == "Found 10 results"
        assert tc.duration_ms is not None
        assert tc.duration_ms >= 0

    async def test_tool_call_with_dict_input(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.TOOL_CALL, {"tool": "read_file", "input": {"path": "/tmp/f.txt"}}),
            _ev(EventType.TOOL_RESULT, {"output": "file content"}),
            _ev(EventType.DONE, {"content": ""}),
        ])
        assert len(result.tool_calls) == 1
        # Dict input should be JSON-serialized
        parsed = json.loads(result.tool_calls[0].input)
        assert parsed["path"] == "/tmp/f.txt"

    async def test_multiple_tool_calls(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.TOOL_CALL, {"tool": "search", "input": "a"}),
            _ev(EventType.TOOL_RESULT, {"output": "r1"}),
            _ev(EventType.TOOL_CALL, {"tool": "read", "input": "b"}),
            _ev(EventType.TOOL_RESULT, {"output": "r2"}),
            _ev(EventType.CONTENT, {"content": "done"}),
            _ev(EventType.DONE, {"content": ""}),
        ])
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].tool == "search"
        assert result.tool_calls[1].tool == "read"

    async def test_file_generated_events(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.FILE_GENERATED, {
                "name": "report.pdf",
                "path": "/tmp/report.pdf",
                "sizeBytes": 1024,
                "mimeType": "application/pdf",
            }),
            _ev(EventType.CONTENT, {"content": "Generated report"}),
            _ev(EventType.DONE, {"content": ""}),
        ])
        assert len(result.files) == 1
        assert result.files[0].name == "report.pdf"
        assert result.files[0].path == "/tmp/report.pdf"
        assert result.files[0].size_bytes == 1024
        assert result.files[0].mime_type == "application/pdf"
        assert result.has_files is True

    async def test_token_usage_from_done(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.CONTENT, {"content": "answer"}),
            _ev(EventType.DONE, {
                "content": "",
                "usage": {"input": 100, "output": 50, "cacheRead": 20, "totalTokens": 170},
            }),
        ])
        assert result.token_usage.input == 100
        assert result.token_usage.output == 50
        assert result.token_usage.cache_read == 20
        assert result.token_usage.total_tokens == 170

    async def test_token_usage_from_token_usage_key(self) -> None:
        """Gateway may use 'tokenUsage' instead of 'usage'."""
        result = await _exec_with_events([
            _ev(EventType.DONE, {
                "content": "ok",
                "tokenUsage": {"input": 50, "output": 25},
            }),
        ])
        assert result.token_usage.input == 50
        assert result.token_usage.output == 25

    async def test_stop_reason_from_done(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.DONE, {"content": "ok", "stopReason": "max_tokens"}),
        ])
        assert result.stop_reason == "max_tokens"

    async def test_stop_reason_defaults_to_complete(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.DONE, {"content": "ok"}),
        ])
        assert result.stop_reason == "complete"

    async def test_aborted_state(self) -> None:
        result = await _exec_with_events([
            _ev(EventType.CONTENT, {"content": "partial"}),
            _ev(EventType.DONE, {"content": "", "state": "aborted"}),
        ])
        assert result.success is False
        assert result.stop_reason == "aborted"
        assert result.content == "partial"

    async def test_backward_compatible_content_only(self) -> None:
        """Existing CONTENT → DONE flow still works unchanged."""
        result = await _exec_with_events([
            _ev(EventType.CONTENT, {"content": "Hello "}),
            _ev(EventType.CONTENT, {"content": "world"}),
            _ev(EventType.DONE, {"content": ""}),
        ])
        assert result.success is True
        assert result.content == "Hello world"
        assert result.thinking is None
        assert result.tool_calls == []
        assert result.files == []

    async def test_fires_tool_call_callback(self) -> None:
        cb = CallbackHandler()
        cb.on_tool_call = _make_async_mock()  # type: ignore[assignment]
        cb.on_tool_result = _make_async_mock()  # type: ignore[assignment]

        await _exec_with_events(
            [
                _ev(EventType.TOOL_CALL, {"tool": "shell", "input": "ls"}),
                _ev(EventType.TOOL_RESULT, {"output": "file.txt"}),
                _ev(EventType.DONE, {"content": ""}),
            ],
            callbacks=[cb],
        )
        cb.on_tool_call.assert_called_once()  # type: ignore[union-attr]
        cb.on_tool_result.assert_called_once()  # type: ignore[union-attr]

    async def test_fires_file_generated_callback(self) -> None:
        cb = CallbackHandler()
        cb.on_file_generated = _make_async_mock()  # type: ignore[assignment]

        await _exec_with_events(
            [
                _ev(EventType.FILE_GENERATED, {
                    "name": "out.csv", "path": "/tmp/out.csv",
                    "sizeBytes": 512, "mimeType": "text/csv",
                }),
                _ev(EventType.DONE, {"content": ""}),
            ],
            callbacks=[cb],
        )
        cb.on_file_generated.assert_called_once()  # type: ignore[union-attr]

    async def test_full_execution_flow(self) -> None:
        """Realistic multi-event execution: thinking → tool → file → content → done."""
        result = await _exec_with_events([
            _ev(EventType.THINKING, {"thinking": "I need to search first"}),
            _ev(EventType.TOOL_CALL, {"tool": "web_search", "input": "SDK docs"}),
            _ev(EventType.TOOL_RESULT, {"output": "Found docs at..."}),
            _ev(EventType.FILE_GENERATED, {
                "name": "summary.md", "path": "/out/summary.md",
                "sizeBytes": 2048, "mimeType": "text/markdown",
            }),
            _ev(EventType.CONTENT, {"content": "Here's what I found: "}),
            _ev(EventType.CONTENT, {"content": "The SDK supports..."}),
            _ev(EventType.DONE, {
                "content": "",
                "usage": {"input": 200, "output": 100, "totalTokens": 300},
                "stopReason": "complete",
            }),
        ])
        assert result.success is True
        assert result.thinking == "I need to search first"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool == "web_search"
        assert len(result.files) == 1
        assert result.files[0].name == "summary.md"
        assert result.content == "Here's what I found: The SDK supports..."
        assert result.token_usage.input == 200
        assert result.token_usage.total_tokens == 300
        assert result.stop_reason == "complete"


def _make_async_mock() -> Any:
    """Create an AsyncMock that also supports assert_called_once."""
    from unittest.mock import AsyncMock
    return AsyncMock()

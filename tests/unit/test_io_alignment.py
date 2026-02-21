"""Tests for I/O alignment with OpenClaw gateway protocol."""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

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

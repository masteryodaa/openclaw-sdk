"""Phase 6H -- TTS, Wizard, Voice Wake & System Misc (19 gateway methods).

Tests cover:
- All 6 TTS gateway facade methods + TTSManager methods
- All 4 Wizard gateway facade methods
- All 2 Voice wake gateway facade methods
- All 7 System misc gateway facade methods + OpsManager methods
- Client.tts property integration
"""

from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.ops.manager import OpsManager
from openclaw_sdk.tts.manager import TTSManager

# ------------------------------------------------------------------ #
# Realistic mock responses
# ------------------------------------------------------------------ #

_TTS_ENABLE_RESPONSE: dict[str, Any] = {"enabled": True}
_TTS_DISABLE_RESPONSE: dict[str, Any] = {"enabled": False}
_TTS_CONVERT_RESPONSE: dict[str, Any] = {
    "audio": "base64encodedaudiodata==",
    "format": "mp3",
    "durationMs": 1250,
}
_TTS_SET_PROVIDER_RESPONSE: dict[str, Any] = {"ok": True}
_TTS_STATUS_RESPONSE: dict[str, Any] = {
    "enabled": True,
    "provider": "openai",
    "voice": "alloy",
    "speed": 1.0,
}
_TTS_PROVIDERS_RESPONSE: dict[str, Any] = {
    "providers": [
        {"id": "openai", "name": "OpenAI TTS", "voices": ["alloy", "echo", "fable"]},
        {"id": "elevenlabs", "name": "ElevenLabs", "voices": ["rachel", "domi"]},
        {"id": "edge", "name": "Microsoft Edge TTS", "voices": ["en-US-JennyNeural"]},
    ],
}

_WIZARD_START_RESPONSE: dict[str, Any] = {
    "sessionId": "wiz-001",
    "step": 1,
    "totalSteps": 5,
    "title": "Initial Setup",
}
_WIZARD_NEXT_RESPONSE: dict[str, Any] = {
    "sessionId": "wiz-001",
    "step": 2,
    "totalSteps": 5,
    "title": "Configure Model",
}
_WIZARD_CANCEL_RESPONSE: dict[str, Any] = {"ok": True}
_WIZARD_STATUS_RESPONSE: dict[str, Any] = {
    "sessionId": "wiz-001",
    "step": 2,
    "totalSteps": 5,
    "completed": False,
    "cancelled": False,
}

_VOICEWAKE_GET_RESPONSE: dict[str, Any] = {
    "triggers": ["hey openclaw", "ok openclaw"],
}
_VOICEWAKE_SET_RESPONSE: dict[str, Any] = {"ok": True}

_SYSTEM_EVENT_RESPONSE: dict[str, Any] = {"ok": True}
_SEND_RESPONSE: dict[str, Any] = {"ok": True}
_BROWSER_REQUEST_RESPONSE: dict[str, Any] = {
    "status": 200,
    "body": "<html><body>Hello</body></html>",
    "headers": {"content-type": "text/html"},
}
_LAST_HEARTBEAT_RESPONSE: dict[str, Any] = {
    "ts": 1709142000000,
    "status": "ok",
    "reason": "periodic",
    "durationMs": 42,
}
_SET_HEARTBEATS_RESPONSE: dict[str, Any] = {"ok": True}
_UPDATE_RUN_RESPONSE: dict[str, Any] = {
    "ok": True,
    "result": {
        "status": "up-to-date",
        "mode": "stable",
        "currentVersion": "2026.2.3-1",
    },
    "restart": False,
    "sentinel": "abc123",
}
_SECRETS_RELOAD_RESPONSE: dict[str, Any] = {"ok": True, "warningCount": 0}


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _mock() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


def _make_tts_manager() -> tuple[MockGateway, TTSManager]:
    mock = _mock()
    return mock, TTSManager(mock)


def _make_ops_manager() -> tuple[MockGateway, OpsManager]:
    mock = _mock()
    return mock, OpsManager(mock)


# ================================================================== #
# Gateway TTS facade tests (6 methods)
# ================================================================== #


class TestGatewayTTSEnable:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("tts.enable", _TTS_ENABLE_RESPONSE)

        result = await mock.tts_enable()

        mock.assert_called("tts.enable")
        assert result["enabled"] is True

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("tts.enable", _TTS_ENABLE_RESPONSE)

        await mock.tts_enable()

        _, params = mock.calls[-1]
        assert params == {}


class TestGatewayTTSDisable:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("tts.disable", _TTS_DISABLE_RESPONSE)

        result = await mock.tts_disable()

        mock.assert_called("tts.disable")
        assert result["enabled"] is False

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("tts.disable", _TTS_DISABLE_RESPONSE)

        await mock.tts_disable()

        _, params = mock.calls[-1]
        assert params == {}


class TestGatewayTTSConvert:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("tts.convert", _TTS_CONVERT_RESPONSE)

        result = await mock.tts_convert("Hello world")

        mock.assert_called("tts.convert")
        assert "audio" in result

    async def test_passes_text_param(self) -> None:
        mock = _mock()
        mock.register("tts.convert", _TTS_CONVERT_RESPONSE)

        await mock.tts_convert("Hello world")

        _, params = mock.calls[-1]
        assert params == {"text": "Hello world"}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("tts.convert", _TTS_CONVERT_RESPONSE)

        result = await mock.tts_convert("Hello")

        assert result["format"] == "mp3"
        assert result["durationMs"] == 1250


class TestGatewayTTSSetProvider:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("tts.setProvider", _TTS_SET_PROVIDER_RESPONSE)

        result = await mock.tts_set_provider("elevenlabs")

        mock.assert_called("tts.setProvider")
        assert result["ok"] is True

    async def test_passes_provider_param(self) -> None:
        mock = _mock()
        mock.register("tts.setProvider", _TTS_SET_PROVIDER_RESPONSE)

        await mock.tts_set_provider("openai")

        _, params = mock.calls[-1]
        assert params == {"provider": "openai"}

    async def test_edge_provider(self) -> None:
        mock = _mock()
        mock.register("tts.setProvider", _TTS_SET_PROVIDER_RESPONSE)

        await mock.tts_set_provider("edge")

        _, params = mock.calls[-1]
        assert params == {"provider": "edge"}


class TestGatewayTTSStatus:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("tts.status", _TTS_STATUS_RESPONSE)

        result = await mock.tts_status()

        mock.assert_called("tts.status")
        assert result["enabled"] is True

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("tts.status", _TTS_STATUS_RESPONSE)

        await mock.tts_status()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("tts.status", _TTS_STATUS_RESPONSE)

        result = await mock.tts_status()

        assert result["provider"] == "openai"
        assert result["voice"] == "alloy"
        assert result["speed"] == 1.0


class TestGatewayTTSProviders:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("tts.providers", _TTS_PROVIDERS_RESPONSE)

        result = await mock.tts_providers()

        mock.assert_called("tts.providers")
        assert "providers" in result

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("tts.providers", _TTS_PROVIDERS_RESPONSE)

        await mock.tts_providers()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("tts.providers", _TTS_PROVIDERS_RESPONSE)

        result = await mock.tts_providers()

        assert len(result["providers"]) == 3
        ids = {p["id"] for p in result["providers"]}
        assert ids == {"openai", "elevenlabs", "edge"}


# ================================================================== #
# TTSManager tests (6 methods)
# ================================================================== #


class TestTTSManagerEnable:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.enable", _TTS_ENABLE_RESPONSE)

        result = await mgr.enable()

        mock.assert_called("tts.enable")
        assert result["enabled"] is True

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.enable", _TTS_ENABLE_RESPONSE)

        await mgr.enable()

        _, params = mock.calls[-1]
        assert params == {}


class TestTTSManagerDisable:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.disable", _TTS_DISABLE_RESPONSE)

        result = await mgr.disable()

        mock.assert_called("tts.disable")
        assert result["enabled"] is False


class TestTTSManagerConvert:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.convert", _TTS_CONVERT_RESPONSE)

        result = await mgr.convert("Hello world")

        mock.assert_called("tts.convert")
        assert "audio" in result

    async def test_passes_text_param(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.convert", _TTS_CONVERT_RESPONSE)

        await mgr.convert("Test speech")

        _, params = mock.calls[-1]
        assert params == {"text": "Test speech"}


class TestTTSManagerSetProvider:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.setProvider", _TTS_SET_PROVIDER_RESPONSE)

        result = await mgr.set_provider("elevenlabs")

        mock.assert_called("tts.setProvider")
        assert result["ok"] is True

    async def test_passes_provider_param(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.setProvider", _TTS_SET_PROVIDER_RESPONSE)

        await mgr.set_provider("edge")

        _, params = mock.calls[-1]
        assert params == {"provider": "edge"}


class TestTTSManagerStatus:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.status", _TTS_STATUS_RESPONSE)

        result = await mgr.status()

        mock.assert_called("tts.status")
        assert result["enabled"] is True
        assert result["provider"] == "openai"


class TestTTSManagerProviders:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_tts_manager()
        mock.register("tts.providers", _TTS_PROVIDERS_RESPONSE)

        result = await mgr.providers()

        mock.assert_called("tts.providers")
        assert len(result["providers"]) == 3


# ================================================================== #
# Gateway Wizard facade tests (4 methods)
# ================================================================== #


class TestGatewayWizardStart:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("wizard.start", _WIZARD_START_RESPONSE)

        result = await mock.wizard_start()

        mock.assert_called("wizard.start")
        assert result["sessionId"] == "wiz-001"

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("wizard.start", _WIZARD_START_RESPONSE)

        await mock.wizard_start()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("wizard.start", _WIZARD_START_RESPONSE)

        result = await mock.wizard_start()

        assert result["step"] == 1
        assert result["totalSteps"] == 5
        assert result["title"] == "Initial Setup"


class TestGatewayWizardNext:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("wizard.next", _WIZARD_NEXT_RESPONSE)

        result = await mock.wizard_next("wiz-001")

        mock.assert_called("wizard.next")
        assert result["step"] == 2

    async def test_passes_session_id(self) -> None:
        mock = _mock()
        mock.register("wizard.next", _WIZARD_NEXT_RESPONSE)

        await mock.wizard_next("wiz-002")

        _, params = mock.calls[-1]
        assert params == {"sessionId": "wiz-002"}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("wizard.next", _WIZARD_NEXT_RESPONSE)

        result = await mock.wizard_next("wiz-001")

        assert result["sessionId"] == "wiz-001"
        assert result["title"] == "Configure Model"


class TestGatewayWizardCancel:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("wizard.cancel", _WIZARD_CANCEL_RESPONSE)

        result = await mock.wizard_cancel("wiz-001")

        mock.assert_called("wizard.cancel")
        assert result["ok"] is True

    async def test_passes_session_id(self) -> None:
        mock = _mock()
        mock.register("wizard.cancel", _WIZARD_CANCEL_RESPONSE)

        await mock.wizard_cancel("wiz-003")

        _, params = mock.calls[-1]
        assert params == {"sessionId": "wiz-003"}


class TestGatewayWizardStatus:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("wizard.status", _WIZARD_STATUS_RESPONSE)

        result = await mock.wizard_status("wiz-001")

        mock.assert_called("wizard.status")
        assert result["step"] == 2

    async def test_passes_session_id(self) -> None:
        mock = _mock()
        mock.register("wizard.status", _WIZARD_STATUS_RESPONSE)

        await mock.wizard_status("wiz-004")

        _, params = mock.calls[-1]
        assert params == {"sessionId": "wiz-004"}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("wizard.status", _WIZARD_STATUS_RESPONSE)

        result = await mock.wizard_status("wiz-001")

        assert result["completed"] is False
        assert result["cancelled"] is False
        assert result["totalSteps"] == 5


# ================================================================== #
# Gateway Voice wake facade tests (2 methods)
# ================================================================== #


class TestGatewayVoicewakeGet:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("voicewake.get", _VOICEWAKE_GET_RESPONSE)

        result = await mock.voicewake_get()

        mock.assert_called("voicewake.get")
        assert "triggers" in result

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("voicewake.get", _VOICEWAKE_GET_RESPONSE)

        await mock.voicewake_get()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("voicewake.get", _VOICEWAKE_GET_RESPONSE)

        result = await mock.voicewake_get()

        assert isinstance(result["triggers"], list)
        assert len(result["triggers"]) == 2
        assert "hey openclaw" in result["triggers"]


class TestGatewayVoicewakeSet:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("voicewake.set", _VOICEWAKE_SET_RESPONSE)

        result = await mock.voicewake_set(["wake up", "hello"])

        mock.assert_called("voicewake.set")
        assert result["ok"] is True

    async def test_passes_triggers_param(self) -> None:
        mock = _mock()
        mock.register("voicewake.set", _VOICEWAKE_SET_RESPONSE)

        await mock.voicewake_set(["hey agent", "ok agent"])

        _, params = mock.calls[-1]
        assert params == {"triggers": ["hey agent", "ok agent"]}

    async def test_empty_triggers(self) -> None:
        mock = _mock()
        mock.register("voicewake.set", _VOICEWAKE_SET_RESPONSE)

        await mock.voicewake_set([])

        _, params = mock.calls[-1]
        assert params == {"triggers": []}


# ================================================================== #
# Gateway System misc facade tests (7 methods)
# ================================================================== #


class TestGatewaySystemEvent:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("system-event", _SYSTEM_EVENT_RESPONSE)

        result = await mock.system_event("Agent started")

        mock.assert_called("system-event")
        assert result["ok"] is True

    async def test_passes_text_param(self) -> None:
        mock = _mock()
        mock.register("system-event", _SYSTEM_EVENT_RESPONSE)

        await mock.system_event("Deployment complete")

        _, params = mock.calls[-1]
        assert params == {"text": "Deployment complete"}


class TestGatewaySendMessage:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("send", _SEND_RESPONSE)

        result = await mock.send_message("user@example.com", "idem-key-001")

        mock.assert_called("send")
        assert result["ok"] is True

    async def test_passes_params(self) -> None:
        mock = _mock()
        mock.register("send", _SEND_RESPONSE)

        await mock.send_message("user-123", "key-abc")

        _, params = mock.calls[-1]
        assert params == {"to": "user-123", "idempotencyKey": "key-abc"}


class TestGatewayBrowserRequest:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("browser.request", _BROWSER_REQUEST_RESPONSE)

        result = await mock.browser_request("GET", "/api/status")

        mock.assert_called("browser.request")
        assert result["status"] == 200

    async def test_passes_params(self) -> None:
        mock = _mock()
        mock.register("browser.request", _BROWSER_REQUEST_RESPONSE)

        await mock.browser_request("POST", "/api/data")

        _, params = mock.calls[-1]
        assert params == {"method": "POST", "path": "/api/data"}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("browser.request", _BROWSER_REQUEST_RESPONSE)

        result = await mock.browser_request("GET", "/")

        assert "body" in result
        assert "headers" in result
        assert result["headers"]["content-type"] == "text/html"


class TestGatewayLastHeartbeat:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("last-heartbeat", _LAST_HEARTBEAT_RESPONSE)

        result = await mock.last_heartbeat()

        mock.assert_called("last-heartbeat")
        assert "ts" in result

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("last-heartbeat", _LAST_HEARTBEAT_RESPONSE)

        await mock.last_heartbeat()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("last-heartbeat", _LAST_HEARTBEAT_RESPONSE)

        result = await mock.last_heartbeat()

        assert result["ts"] == 1709142000000
        assert result["status"] == "ok"
        assert result["reason"] == "periodic"
        assert result["durationMs"] == 42


class TestGatewaySetHeartbeats:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("set-heartbeats", _SET_HEARTBEATS_RESPONSE)

        result = await mock.set_heartbeats(True)

        mock.assert_called("set-heartbeats")
        assert result["ok"] is True

    async def test_passes_enabled_true(self) -> None:
        mock = _mock()
        mock.register("set-heartbeats", _SET_HEARTBEATS_RESPONSE)

        await mock.set_heartbeats(True)

        _, params = mock.calls[-1]
        assert params == {"enabled": True}

    async def test_passes_enabled_false(self) -> None:
        mock = _mock()
        mock.register("set-heartbeats", _SET_HEARTBEATS_RESPONSE)

        await mock.set_heartbeats(False)

        _, params = mock.calls[-1]
        assert params == {"enabled": False}


class TestGatewayUpdateRun:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("update.run", _UPDATE_RUN_RESPONSE)

        result = await mock.update_run()

        mock.assert_called("update.run")
        assert result["ok"] is True

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("update.run", _UPDATE_RUN_RESPONSE)

        await mock.update_run()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("update.run", _UPDATE_RUN_RESPONSE)

        result = await mock.update_run()

        assert result["result"]["status"] == "up-to-date"
        assert result["result"]["mode"] == "stable"
        assert result["restart"] is False
        assert result["sentinel"] == "abc123"


class TestGatewaySecretsReload:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("secrets.reload", _SECRETS_RELOAD_RESPONSE)

        result = await mock.secrets_reload()

        mock.assert_called("secrets.reload")
        assert result["ok"] is True

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("secrets.reload", _SECRETS_RELOAD_RESPONSE)

        await mock.secrets_reload()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("secrets.reload", _SECRETS_RELOAD_RESPONSE)

        result = await mock.secrets_reload()

        assert result["warningCount"] == 0


# ================================================================== #
# OpsManager system misc method tests (5 methods)
# ================================================================== #


class TestOpsManagerSystemEvent:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("system-event", _SYSTEM_EVENT_RESPONSE)

        result = await mgr.system_event("Agent deployed")

        mock.assert_called("system-event")
        assert result["ok"] is True

    async def test_passes_text_param(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("system-event", _SYSTEM_EVENT_RESPONSE)

        await mgr.system_event("Restart requested")

        _, params = mock.calls[-1]
        assert params == {"text": "Restart requested"}


class TestOpsManagerLastHeartbeat:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("last-heartbeat", _LAST_HEARTBEAT_RESPONSE)

        result = await mgr.last_heartbeat()

        mock.assert_called("last-heartbeat")
        assert result["ts"] == 1709142000000

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("last-heartbeat", _LAST_HEARTBEAT_RESPONSE)

        await mgr.last_heartbeat()

        _, params = mock.calls[-1]
        assert params == {}


class TestOpsManagerSetHeartbeats:
    async def test_calls_gateway_enabled(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("set-heartbeats", _SET_HEARTBEATS_RESPONSE)

        result = await mgr.set_heartbeats(True)

        mock.assert_called("set-heartbeats")
        assert result["ok"] is True

    async def test_passes_enabled_param(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("set-heartbeats", _SET_HEARTBEATS_RESPONSE)

        await mgr.set_heartbeats(False)

        _, params = mock.calls[-1]
        assert params == {"enabled": False}


class TestOpsManagerUpdateRun:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("update.run", _UPDATE_RUN_RESPONSE)

        result = await mgr.update_run()

        mock.assert_called("update.run")
        assert result["ok"] is True

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("update.run", _UPDATE_RUN_RESPONSE)

        await mgr.update_run()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_returns_full_response(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("update.run", _UPDATE_RUN_RESPONSE)

        result = await mgr.update_run()

        assert result["result"]["currentVersion"] == "2026.2.3-1"
        assert result["restart"] is False


class TestOpsManagerSecretsReload:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("secrets.reload", _SECRETS_RELOAD_RESPONSE)

        result = await mgr.secrets_reload()

        mock.assert_called("secrets.reload")
        assert result["ok"] is True

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("secrets.reload", _SECRETS_RELOAD_RESPONSE)

        await mgr.secrets_reload()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_returns_warning_count(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("secrets.reload", {"ok": True, "warningCount": 2})

        result = await mgr.secrets_reload()

        assert result["warningCount"] == 2


# ================================================================== #
# Client.tts property integration test
# ================================================================== #


class TestClientTTSProperty:
    def test_tts_property_returns_tts_manager(self) -> None:
        from openclaw_sdk.core.client import OpenClawClient
        from openclaw_sdk.core.config import ClientConfig

        mock = _mock()
        config = ClientConfig(gateway_ws_url="ws://localhost:18789/gateway")
        client = OpenClawClient(config=config, gateway=mock)

        assert isinstance(client.tts, TTSManager)

    def test_tts_property_is_cached(self) -> None:
        from openclaw_sdk.core.client import OpenClawClient
        from openclaw_sdk.core.config import ClientConfig

        mock = _mock()
        config = ClientConfig(gateway_ws_url="ws://localhost:18789/gateway")
        client = OpenClawClient(config=config, gateway=mock)

        tts1 = client.tts
        tts2 = client.tts
        assert tts1 is tts2


# ================================================================== #
# TTSManager import/export tests
# ================================================================== #


class TestTTSManagerExport:
    def test_importable_from_package(self) -> None:
        from openclaw_sdk import TTSManager as Imported

        assert Imported is TTSManager

    def test_importable_from_tts_module(self) -> None:
        from openclaw_sdk.tts import TTSManager as Imported

        assert Imported is TTSManager


# ================================================================== #
# Existing OpsManager methods still work (no regression)
# ================================================================== #


class TestOpsManagerExistingMethodsStillWork:
    """Ensure adding new methods doesn't break existing OpsManager methods."""

    async def test_logs_tail_still_works(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register(
            "logs.tail", {"file": "app.log", "cursor": 0, "size": 100, "lines": []}
        )

        result = await mgr.logs_tail()

        mock.assert_called("logs.tail")
        assert result["file"] == "app.log"

    async def test_usage_status_still_works(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("usage.status", {"updatedAt": 1234, "providers": []})

        result = await mgr.usage_status()

        mock.assert_called("usage.status")
        assert "providers" in result

    async def test_system_status_still_works(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register(
            "status",
            {
                "linkChannel": "ws://127.0.0.1:18789/gateway",
                "heartbeat": 1709142000000,
                "channelSummary": {},
                "queuedSystemEvents": 0,
                "sessions": {"count": 5},
            },
        )

        result = await mgr.system_status()

        mock.assert_called("status")
        assert result["sessions"]["count"] == 5

    async def test_memory_status_still_works(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register(
            "doctor.memory.status",
            {"agentId": "a1", "provider": "openai", "embedding": {"ok": True}},
        )

        result = await mgr.memory_status()

        mock.assert_called("doctor.memory.status")
        assert result["embedding"]["ok"] is True

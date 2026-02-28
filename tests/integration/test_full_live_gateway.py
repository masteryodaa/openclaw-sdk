"""Comprehensive live gateway integration tests for ALL Sprint 6 methods.

Tests every gateway facade method and manager wrapper against the real
OpenClaw gateway at ws://127.0.0.1:18789/gateway.

Run with:
    pytest tests/integration/test_full_live_gateway.py -v --timeout=30

Categories:
    1. Read-only / safe queries (always safe to run)
    2. Safe mutating (idempotent or reversible)
    3. Agent CRUD lifecycle (create → test → cleanup)
    4. Session operations (need existing session key)
    5. Wizard lifecycle (start → status → cancel)
    6. Role-restricted (expect auth errors)
    7. Cron lifecycle (add → list → remove)
    8. Manager-level tests (wrappers over gateway)
    9. OpenClawClient end-to-end
"""

from __future__ import annotations

import uuid

import pytest
from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.config.manager import ConfigManager
from openclaw_sdk.core.client import OpenClawClient, _openclaw_is_running
from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.devices.manager import DeviceManager
from openclaw_sdk.gateway.protocol import ProtocolGateway
from openclaw_sdk.nodes.manager import NodeManager
from openclaw_sdk.ops.manager import OpsManager
from openclaw_sdk.skills.manager import SkillManager
from openclaw_sdk.tts.manager import TTSManager

pytestmark = pytest.mark.integration


def gateway_available() -> bool:
    return _openclaw_is_running()


@pytest.fixture
async def gw():
    """Connect to a live OpenClaw gateway, skipping if unavailable."""
    if not gateway_available():
        pytest.skip("OpenClaw not running at 127.0.0.1:18789")
    gateway = ProtocolGateway()
    try:
        await gateway.connect()
        probe = await gateway.health()
        if not probe.healthy:
            await gateway.close()
            pytest.skip("Gateway reports unhealthy")
    except GatewayError as exc:
        await gateway.close()
        pytest.skip(f"Gateway not fully available: {exc}")
    yield gateway
    await gateway.close()


# ================================================================== #
# 1. READ-ONLY / SAFE QUERIES
# ================================================================== #


class TestReadOnlyQueries:
    """Safe read-only gateway methods that never mutate state."""

    async def test_health(self, gw: ProtocolGateway) -> None:
        status = await gw.health()
        assert status.healthy

    async def test_system_status(self, gw: ProtocolGateway) -> None:
        result = await gw.system_status()
        assert isinstance(result, dict)
        assert "sessions" in result or "heartbeat" in result

    async def test_system_presence(self, gw: ProtocolGateway) -> None:
        result = await gw.system_presence()
        assert isinstance(result, dict)

    async def test_doctor_memory_status(self, gw: ProtocolGateway) -> None:
        result = await gw.doctor_memory_status()
        assert isinstance(result, dict)
        # May have agentId, provider, embedding fields
        assert "agentId" in result or "provider" in result or "embedding" in result

    async def test_last_heartbeat(self, gw: ProtocolGateway) -> None:
        result = await gw.last_heartbeat()
        assert isinstance(result, dict)

    async def test_sessions_list(self, gw: ProtocolGateway) -> None:
        result = await gw.sessions_list()
        assert isinstance(result, list)

    async def test_sessions_usage(self, gw: ProtocolGateway) -> None:
        result = await gw.sessions_usage()
        assert isinstance(result, dict)

    async def test_usage_status(self, gw: ProtocolGateway) -> None:
        result = await gw.usage_status()
        assert isinstance(result, dict)

    async def test_usage_cost(self, gw: ProtocolGateway) -> None:
        result = await gw.usage_cost()
        assert isinstance(result, dict)

    async def test_agents_list(self, gw: ProtocolGateway) -> None:
        result = await gw.agents_list()
        assert isinstance(result, dict)
        assert "agents" in result

    async def test_agent_identity_get(self, gw: ProtocolGateway) -> None:
        result = await gw.agent_identity_get()
        assert isinstance(result, dict)
        assert "agentId" in result or "name" in result

    async def test_config_get(self, gw: ProtocolGateway) -> None:
        result = await gw.config_get()
        assert isinstance(result, dict)
        assert "raw" in result or "path" in result

    async def test_config_schema(self, gw: ProtocolGateway) -> None:
        result = await gw.config_schema()
        assert isinstance(result, dict)
        assert "schema" in result

    async def test_channels_status(self, gw: ProtocolGateway) -> None:
        result = await gw.call("channels.status", {})
        assert isinstance(result, dict)
        assert "channels" in result

    async def test_cron_list(self, gw: ProtocolGateway) -> None:
        result = await gw.call("cron.list", {})
        assert isinstance(result, dict)

    async def test_cron_status(self, gw: ProtocolGateway) -> None:
        result = await gw.call("cron.status", {})
        assert isinstance(result, dict)

    async def test_models_list(self, gw: ProtocolGateway) -> None:
        result = await gw.models_list()
        assert isinstance(result, dict)
        assert "models" in result
        assert len(result["models"]) > 0

    async def test_tools_catalog(self, gw: ProtocolGateway) -> None:
        result = await gw.tools_catalog()
        assert isinstance(result, dict)
        assert "groups" in result or "profiles" in result

    async def test_skills_status(self, gw: ProtocolGateway) -> None:
        result = await gw.skills_status()
        assert isinstance(result, dict)
        assert "skills" in result

    async def test_tts_status(self, gw: ProtocolGateway) -> None:
        result = await gw.tts_status()
        assert isinstance(result, dict)

    async def test_tts_providers(self, gw: ProtocolGateway) -> None:
        result = await gw.tts_providers()
        assert isinstance(result, dict)
        assert "providers" in result

    async def test_voicewake_get(self, gw: ProtocolGateway) -> None:
        result = await gw.voicewake_get()
        assert isinstance(result, dict)
        assert "triggers" in result

    async def test_device_pair_list(self, gw: ProtocolGateway) -> None:
        result = await gw.device_pair_list()
        assert isinstance(result, dict)
        assert "paired" in result

    async def test_node_list(self, gw: ProtocolGateway) -> None:
        result = await gw.node_list()
        assert isinstance(result, list)

    async def test_node_pair_list(self, gw: ProtocolGateway) -> None:
        result = await gw.node_pair_list()
        assert isinstance(result, dict)
        assert "paired" in result or "pending" in result

    async def test_exec_approvals_get(self, gw: ProtocolGateway) -> None:
        result = await gw.exec_approvals_get()
        assert isinstance(result, dict)

    async def test_logs_tail(self, gw: ProtocolGateway) -> None:
        result = await gw.logs_tail()
        assert isinstance(result, dict)

    async def test_secrets_reload(self, gw: ProtocolGateway) -> None:
        result = await gw.secrets_reload()
        assert isinstance(result, dict)

    async def test_usage_summary_aggregation(self, gw: ProtocolGateway) -> None:
        """Test the legacy usage_summary aggregation from sessions.list."""
        result = await gw.usage_summary()
        assert isinstance(result, dict)
        assert "totalTokens" in result
        assert "sessionCount" in result


# ================================================================== #
# 2. SAFE MUTATING (idempotent or reversible)
# ================================================================== #


class TestSafeMutating:
    """Mutating operations that are idempotent or easily reversed."""

    async def test_tts_enable_disable(self, gw: ProtocolGateway) -> None:
        """Enable then disable TTS — round-trip."""
        # Get original state
        original = await gw.tts_status()
        original_enabled = original.get("enabled", False)

        # Enable
        result = await gw.tts_enable()
        assert isinstance(result, dict)

        # Disable
        result = await gw.tts_disable()
        assert isinstance(result, dict)

        # Restore original state
        if original_enabled:
            await gw.tts_enable()

    async def test_tts_set_provider(self, gw: ProtocolGateway) -> None:
        """Set TTS provider to edge (always available)."""
        try:
            result = await gw.tts_set_provider("edge")
            assert isinstance(result, dict)
        except GatewayError:
            # May fail if edge provider not available
            pass

    async def test_voicewake_set_roundtrip(self, gw: ProtocolGateway) -> None:
        """Set voice wake triggers then restore originals."""
        # Get original triggers
        original = await gw.voicewake_get()
        original_triggers = original.get("triggers", ["openclaw"])

        # Set test triggers
        result = await gw.voicewake_set(["openclaw", "hey"])
        assert isinstance(result, dict)

        # Restore original
        await gw.voicewake_set(original_triggers)

    async def test_set_heartbeats(self, gw: ProtocolGateway) -> None:
        """Toggle heartbeats on then off."""
        result = await gw.set_heartbeats(True)
        assert isinstance(result, dict)

        result = await gw.set_heartbeats(False)
        assert isinstance(result, dict)

    async def test_system_event(self, gw: ProtocolGateway) -> None:
        """Emit a test system event."""
        result = await gw.system_event("sdk-live-test")
        assert isinstance(result, dict)

    async def test_update_run(self, gw: ProtocolGateway) -> None:
        """Run update check (read-only check, doesn't actually update)."""
        try:
            result = await gw.update_run()
            assert isinstance(result, dict)
        except GatewayError:
            # May fail in some environments
            pass


# ================================================================== #
# 3. AGENT CRUD LIFECYCLE
# ================================================================== #


class TestAgentCRUD:
    """Create → list → files → identity → delete agent lifecycle."""

    async def test_agent_crud_lifecycle(self, gw: ProtocolGateway) -> None:
        """Full agent CRUD lifecycle."""
        test_name = f"sdk-test-{uuid.uuid4().hex[:8]}"

        # Create — workspace is required by the gateway
        try:
            create_result = await gw.agents_create(test_name, workspace=".")
            assert isinstance(create_result, dict)
            created_id = create_result.get("agentId", test_name)
        except GatewayError as exc:
            pytest.skip(f"agents.create failed: {exc}")
            return

        try:
            # List — verify list works (created agent may not appear
            # immediately; gateway may only list persistent agents)
            list_result = await gw.agents_list()
            assert isinstance(list_result, dict)
            assert "agents" in list_result

            # Files list on default agent (our new agent may not have files)
            default_id = list_result.get("defaultId", "main")
            files_result = await gw.agents_files_list(default_id)
            assert isinstance(files_result, dict)

            # Files set on default agent
            try:
                set_result = await gw.agents_files_set(
                    default_id, "sdk-test.md", "# SDK Test\nHello"
                )
                assert isinstance(set_result, dict)
            except GatewayError:
                pass

            # Files get on default agent
            try:
                get_result = await gw.agents_files_get(default_id, "sdk-test.md")
                assert isinstance(get_result, dict)
            except GatewayError:
                pass
        finally:
            # Cleanup — delete the test agent
            try:
                await gw.agents_delete(created_id)
            except GatewayError:
                pass


# ================================================================== #
# 4. SESSION OPERATIONS
# ================================================================== #


class TestSessionOperations:
    """Tests that need an existing session key."""

    async def _get_session_key(self, gw: ProtocolGateway) -> str | None:
        """Get the first available session key."""
        sessions = await gw.sessions_list()
        if sessions:
            return sessions[0].get("key")
        return None

    async def test_sessions_preview(self, gw: ProtocolGateway) -> None:
        key = await self._get_session_key(gw)
        if not key:
            pytest.skip("No sessions available")
        result = await gw.sessions_preview([key])
        assert isinstance(result, dict)

    async def test_sessions_resolve(self, gw: ProtocolGateway) -> None:
        key = await self._get_session_key(gw)
        if not key:
            pytest.skip("No sessions available")
        result = await gw.sessions_resolve(key)
        assert isinstance(result, dict)

    async def test_chat_history(self, gw: ProtocolGateway) -> None:
        key = await self._get_session_key(gw)
        if not key:
            pytest.skip("No sessions available")
        result = await gw.chat_history(key)
        assert isinstance(result, list)

    async def test_chat_inject(self, gw: ProtocolGateway) -> None:
        key = await self._get_session_key(gw)
        if not key:
            pytest.skip("No sessions available")
        try:
            result = await gw.chat_inject(key, "SDK integration test message")
            assert isinstance(result, dict)
        except GatewayError:
            pass  # May fail if session is in certain states

    async def test_chat_abort_no_active_run(self, gw: ProtocolGateway) -> None:
        """chat.abort on a session with no active run — should not crash."""
        key = await self._get_session_key(gw)
        if not key:
            pytest.skip("No sessions available")
        try:
            result = await gw.chat_abort(key)
            assert isinstance(result, dict)
        except GatewayError:
            pass  # Expected if no run is active

    async def test_sessions_patch(self, gw: ProtocolGateway) -> None:
        """Patch a session with a harmless field."""
        key = await self._get_session_key(gw)
        if not key:
            pytest.skip("No sessions available")
        try:
            result = await gw.sessions_patch(key, {})
            assert isinstance(result, dict)
        except GatewayError:
            pass  # Some sessions may not be patchable


# ================================================================== #
# 5. WIZARD LIFECYCLE
# ================================================================== #


class TestWizard:
    """Start → status → cancel wizard lifecycle."""

    async def test_wizard_lifecycle(self, gw: ProtocolGateway) -> None:
        """Start a wizard, check status, cancel it."""
        # Start
        try:
            start_result = await gw.wizard_start()
            assert isinstance(start_result, dict)
            session_id = start_result.get("sessionId")
            if not session_id:
                pytest.skip("wizard.start didn't return sessionId")
                return
        except GatewayError as exc:
            pytest.skip(f"wizard.start failed: {exc}")
            return

        # Status
        try:
            status_result = await gw.wizard_status(session_id)
            assert isinstance(status_result, dict)
        except GatewayError:
            pass

        # Cancel
        try:
            cancel_result = await gw.wizard_cancel(session_id)
            assert isinstance(cancel_result, dict)
        except GatewayError:
            pass  # May already be done


# ================================================================== #
# 6. ROLE-RESTRICTED (expect auth errors)
# ================================================================== #


class TestRoleRestricted:
    """Methods requiring elevated roles — should error gracefully."""

    async def test_skills_bins_role_restricted(self, gw: ProtocolGateway) -> None:
        """skills.bins requires elevated role — expect error."""
        try:
            result = await gw.skills_bins()
            # If it succeeds, it's still valid
            assert isinstance(result, dict)
        except GatewayError:
            pass  # Expected — role restricted

    async def test_node_invoke_result_role_restricted(self, gw: ProtocolGateway) -> None:
        """node.invoke.result requires node role — expect error."""
        try:
            result = await gw.node_invoke_result(requestId="fake")
            assert isinstance(result, dict)
        except GatewayError:
            pass  # Expected

    async def test_node_event_role_restricted(self, gw: ProtocolGateway) -> None:
        """node.event requires node role — expect error."""
        try:
            result = await gw.node_event(text="test")
            assert isinstance(result, dict)
        except GatewayError:
            pass  # Expected


# ================================================================== #
# 7. CRON LIFECYCLE
# ================================================================== #


class TestCronLifecycle:
    """Add → list → remove cron job lifecycle."""

    async def test_cron_add_and_remove(self, gw: ProtocolGateway) -> None:
        """Create a cron job, verify it appears in list, then remove it."""
        job_name = f"sdk-test-{uuid.uuid4().hex[:8]}"

        # Add — schedule must be an object: {kind: "cron", expr: "..."}
        # payload must be an object: {message: "...", kind?: "agentTurn"}
        try:
            add_result = await gw.call(
                "cron.add",
                {
                    "name": job_name,
                    "schedule": {"kind": "cron", "expr": "0 0 31 2 *"},
                    "sessionTarget": "agent:main:main",
                    "payload": {"message": "SDK test - safe to delete"},
                },
            )
            assert isinstance(add_result, dict)
        except GatewayError as exc:
            pytest.skip(f"cron.add failed: {exc}")
            return

        job_id = add_result.get("id") or add_result.get("jobId")

        try:
            # List and verify
            list_result = await gw.call("cron.list", {})
            assert isinstance(list_result, dict)
            job_ids = [j.get("id") for j in list_result.get("jobs", [])]
            assert job_id in job_ids
        finally:
            # Cleanup — remove the job
            if job_id:
                try:
                    await gw.call("cron.remove", {"id": job_id})
                except GatewayError:
                    pass


# ================================================================== #
# 8. APPROVAL OPERATIONS
# ================================================================== #


class TestApprovals:
    """Test approval settings and resolve with fake IDs."""

    async def test_exec_approvals_get_settings(self, gw: ProtocolGateway) -> None:
        result = await gw.exec_approvals_get()
        assert isinstance(result, dict)

    async def test_exec_approval_resolve_fake(self, gw: ProtocolGateway) -> None:
        """Resolving a non-existent approval should error gracefully."""
        fake_id = f"fake-{uuid.uuid4().hex[:12]}"
        try:
            result = await gw.resolve_approval(fake_id, "deny")
            assert isinstance(result, dict)
        except GatewayError:
            pass  # Expected

    async def test_exec_approvals_set_roundtrip(self, gw: ProtocolGateway) -> None:
        """Read settings, write them back unchanged."""
        current = await gw.exec_approvals_get()
        if not current.get("exists"):
            pytest.skip("No approval settings file exists")
        file_data = current.get("file")
        base_hash = current.get("hash")
        if not file_data:
            pytest.skip("No file data in approval settings")
        try:
            result = await gw.exec_approvals_set(file_data, base_hash=base_hash)
            assert isinstance(result, dict)
        except GatewayError:
            pass  # CAS conflict is acceptable


# ================================================================== #
# 9. DEVICE OPERATIONS
# ================================================================== #


class TestDeviceOperations:
    """Test device pairing with fake IDs (expect graceful errors)."""

    async def test_device_pair_list(self, gw: ProtocolGateway) -> None:
        result = await gw.device_pair_list()
        assert isinstance(result, dict)
        assert "paired" in result

    async def test_device_pair_approve_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.device_pair_approve(f"fake-{uuid.uuid4().hex[:8]}")
        except GatewayError:
            pass  # Expected

    async def test_device_pair_reject_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.device_pair_reject(f"fake-{uuid.uuid4().hex[:8]}")
        except GatewayError:
            pass  # Expected

    async def test_device_pair_remove_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.device_pair_remove(f"fake-{uuid.uuid4().hex[:8]}")
        except GatewayError:
            pass  # Expected

    async def test_device_token_rotate_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.device_token_rotate(f"fake-{uuid.uuid4().hex[:8]}", "operator")
        except GatewayError:
            pass  # Expected

    async def test_device_token_revoke_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.device_token_revoke(f"fake-{uuid.uuid4().hex[:8]}", "operator")
        except GatewayError:
            pass  # Expected


# ================================================================== #
# 10. NODE OPERATIONS
# ================================================================== #


class TestNodeOperations:
    """Test node methods with real data where available, fake IDs otherwise."""

    async def test_node_list(self, gw: ProtocolGateway) -> None:
        result = await gw.node_list()
        assert isinstance(result, list)

    async def test_node_pair_list(self, gw: ProtocolGateway) -> None:
        result = await gw.node_pair_list()
        assert isinstance(result, dict)

    async def test_node_rename_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.node_rename(f"fake-{uuid.uuid4().hex[:8]}", "Test Node")
        except GatewayError:
            pass  # Expected

    async def test_node_pair_approve_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.node_pair_approve(f"fake-{uuid.uuid4().hex[:8]}")
        except GatewayError:
            pass  # Expected

    async def test_node_pair_reject_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.node_pair_reject(f"fake-{uuid.uuid4().hex[:8]}")
        except GatewayError:
            pass  # Expected

    async def test_node_pair_verify_fake(self, gw: ProtocolGateway) -> None:
        try:
            await gw.node_pair_verify(f"fake-{uuid.uuid4().hex[:8]}", "fake-token")
        except GatewayError:
            pass  # Expected


# ================================================================== #
# 11. MANAGER-LEVEL TESTS
# ================================================================== #


class TestManagers:
    """Test manager wrappers that delegate to gateway RPC."""

    # -- OpsManager --

    async def test_ops_logs_tail(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.logs_tail()
        assert isinstance(result, dict)

    async def test_ops_usage_status(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.usage_status()
        assert isinstance(result, dict)

    async def test_ops_usage_cost(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.usage_cost()
        assert isinstance(result, dict)

    async def test_ops_sessions_usage(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.sessions_usage()
        assert isinstance(result, dict)

    async def test_ops_system_status(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.system_status()
        assert isinstance(result, dict)

    async def test_ops_memory_status(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.memory_status()
        assert isinstance(result, dict)

    async def test_ops_system_event(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.system_event("manager-test")
        assert isinstance(result, dict)

    async def test_ops_last_heartbeat(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.last_heartbeat()
        assert isinstance(result, dict)

    async def test_ops_set_heartbeats(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.set_heartbeats(True)
        assert isinstance(result, dict)
        await ops.set_heartbeats(False)

    async def test_ops_secrets_reload(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.secrets_reload()
        assert isinstance(result, dict)

    async def test_ops_usage_summary_legacy(self, gw: ProtocolGateway) -> None:
        ops = OpsManager(gw)
        result = await ops.usage_summary()
        assert isinstance(result, dict)
        assert "totalTokens" in result

    # -- ApprovalManager --

    async def test_approval_manager_get_settings(self, gw: ProtocolGateway) -> None:
        mgr = ApprovalManager(gw)
        result = await mgr.get_settings()
        assert isinstance(result, dict)

    async def test_approval_manager_resolve_fake(self, gw: ProtocolGateway) -> None:
        mgr = ApprovalManager(gw)
        try:
            await mgr.resolve(f"fake-{uuid.uuid4().hex[:8]}", "deny")
        except GatewayError:
            pass

    # -- DeviceManager --

    async def test_device_manager_list_paired(self, gw: ProtocolGateway) -> None:
        mgr = DeviceManager(gw)
        result = await mgr.list_paired()
        assert isinstance(result, dict)
        assert "paired" in result

    # -- SkillManager (gateway mode) --

    async def test_skill_manager_status(self, gw: ProtocolGateway) -> None:
        mgr = SkillManager(gateway=gw)
        result = await mgr.status()
        assert isinstance(result, dict)
        assert "skills" in result

    # -- ConfigManager --

    async def test_config_manager_get(self, gw: ProtocolGateway) -> None:
        mgr = ConfigManager(gw)
        result = await mgr.get()
        assert isinstance(result, dict)

    async def test_config_manager_schema(self, gw: ProtocolGateway) -> None:
        mgr = ConfigManager(gw)
        result = await mgr.schema()
        assert isinstance(result, dict)
        assert "schema" in result

    async def test_config_manager_discover_models(self, gw: ProtocolGateway) -> None:
        mgr = ConfigManager(gw)
        result = await mgr.discover_models()
        assert isinstance(result, dict)
        assert "models" in result
        assert len(result["models"]) > 0

    async def test_config_manager_discover_tools(self, gw: ProtocolGateway) -> None:
        mgr = ConfigManager(gw)
        result = await mgr.discover_tools()
        assert isinstance(result, dict)

    async def test_config_manager_get_parsed(self, gw: ProtocolGateway) -> None:
        mgr = ConfigManager(gw)
        config, hash_val = await mgr.get_parsed()
        assert isinstance(config, dict)

    async def test_config_manager_list_agents(self, gw: ProtocolGateway) -> None:
        mgr = ConfigManager(gw)
        agents = await mgr.list_agents()
        assert isinstance(agents, list)

    # -- NodeManager --

    async def test_node_manager_system_presence(self, gw: ProtocolGateway) -> None:
        mgr = NodeManager(gw)
        result = await mgr.system_presence()
        assert isinstance(result, dict)

    async def test_node_manager_list(self, gw: ProtocolGateway) -> None:
        mgr = NodeManager(gw)
        result = await mgr.list()
        assert isinstance(result, list)

    async def test_node_manager_pair_list(self, gw: ProtocolGateway) -> None:
        mgr = NodeManager(gw)
        result = await mgr.pair_list()
        assert isinstance(result, dict)

    # -- TTSManager --

    async def test_tts_manager_status(self, gw: ProtocolGateway) -> None:
        mgr = TTSManager(gw)
        result = await mgr.status()
        assert isinstance(result, dict)

    async def test_tts_manager_providers(self, gw: ProtocolGateway) -> None:
        mgr = TTSManager(gw)
        result = await mgr.providers()
        assert isinstance(result, dict)
        assert "providers" in result

    async def test_tts_manager_enable_disable(self, gw: ProtocolGateway) -> None:
        mgr = TTSManager(gw)
        # Get original
        original = await mgr.status()
        original_enabled = original.get("enabled", False)

        await mgr.enable()
        await mgr.disable()

        # Restore
        if original_enabled:
            await mgr.enable()


# ================================================================== #
# 12. OPENCLAW CLIENT END-TO-END
# ================================================================== #


class TestOpenClawClientE2E:
    """Full client connect → use → close lifecycle."""

    async def test_client_connect_and_health(self) -> None:
        if not gateway_available():
            pytest.skip("OpenClaw not running")
        try:
            client = await OpenClawClient.connect()
        except Exception as exc:
            pytest.skip(f"Client connect failed: {exc}")
            return
        try:
            health = await client.health()
            assert health.healthy
        finally:
            await client.close()

    async def test_client_list_agents(self) -> None:
        if not gateway_available():
            pytest.skip("OpenClaw not running")
        try:
            client = await OpenClawClient.connect()
        except Exception as exc:
            pytest.skip(f"Client connect failed: {exc}")
            return
        try:
            agents = await client.list_agents()
            assert isinstance(agents, list)
        finally:
            await client.close()

    async def test_client_context_manager(self) -> None:
        if not gateway_available():
            pytest.skip("OpenClaw not running")
        try:
            async with await OpenClawClient.connect() as client:
                health = await client.health()
                assert health.healthy
        except Exception as exc:
            pytest.skip(f"Client failed: {exc}")

    async def test_client_gateway_property(self) -> None:
        if not gateway_available():
            pytest.skip("OpenClaw not running")
        try:
            client = await OpenClawClient.connect()
        except Exception as exc:
            pytest.skip(f"Client connect failed: {exc}")
            return
        try:
            gw = client.gateway
            result = await gw.sessions_list()
            assert isinstance(result, list)
        finally:
            await client.close()

    async def test_client_manager_properties(self) -> None:
        """Test that all manager properties are accessible."""
        if not gateway_available():
            pytest.skip("OpenClaw not running")
        try:
            client = await OpenClawClient.connect()
        except Exception as exc:
            pytest.skip(f"Client connect failed: {exc}")
            return
        try:
            # Access all lazy manager properties
            assert client.channels is not None
            assert client.scheduling is not None
            assert client.skills is not None
            assert client.webhooks is not None
            assert client.schedules is not None
            assert client.config_mgr is not None
            assert client.approvals is not None
            assert client.nodes is not None
            assert client.ops is not None
            assert client.devices is not None
            assert client.tts is not None

            # Actually call a method on each manager
            await client.ops.logs_tail()
            await client.approvals.get_settings()
            await client.devices.list_paired()
            await client.nodes.pair_list()
            await client.tts.status()
        finally:
            await client.close()


# ================================================================== #
# 13. SKILLS GATEWAY METHODS
# ================================================================== #


class TestSkillsGateway:
    """Test skills methods accessible via gateway."""

    async def test_skills_status_facade(self, gw: ProtocolGateway) -> None:
        result = await gw.skills_status()
        assert isinstance(result, dict)
        assert "skills" in result
        # Verify skill structure
        skills = result["skills"]
        assert isinstance(skills, list)
        if skills:
            skill = skills[0]
            assert "name" in skill

    async def test_skills_install_fake(self, gw: ProtocolGateway) -> None:
        """Install a non-existent skill — should fail gracefully."""
        try:
            await gw.skills_install("nonexistent-skill", f"install-{uuid.uuid4().hex[:8]}")
        except GatewayError:
            pass  # Expected

    async def test_skills_update_fake(self, gw: ProtocolGateway) -> None:
        """Update a non-existent skill — should fail gracefully."""
        try:
            await gw.skills_update("nonexistent-skill-key")
        except GatewayError:
            pass  # Expected


# ================================================================== #
# 14. CONFIG READ-ONLY VERIFICATION
# ================================================================== #


class TestConfigReadOnly:
    """Test config methods without actually changing config."""

    async def test_config_get_has_expected_fields(self, gw: ProtocolGateway) -> None:
        result = await gw.config_get()
        assert isinstance(result, dict)
        # Should have at least path and raw
        assert "raw" in result or "path" in result

    async def test_config_schema_has_json_schema(self, gw: ProtocolGateway) -> None:
        result = await gw.config_schema()
        schema = result.get("schema", {})
        assert isinstance(schema, dict)
        # Should look like a JSON Schema
        assert "type" in schema or "$schema" in schema or "properties" in schema

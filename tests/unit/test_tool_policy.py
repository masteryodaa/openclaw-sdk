from __future__ import annotations

from openclaw_sdk.tools.policy import (
    ElevatedPolicy,
    ExecPolicy,
    FsPolicy,
    ToolPolicy,
    WebFetchPolicy,
    WebPolicy,
    WebSearchPolicy,
)


class TestDefaultConstruction:
    def test_default_profile_is_coding(self) -> None:
        policy = ToolPolicy()
        assert policy.profile == "coding"

    def test_default_allow_is_empty(self) -> None:
        policy = ToolPolicy()
        assert policy.allow == []

    def test_default_deny_list_is_empty(self) -> None:
        policy = ToolPolicy()
        assert policy.deny_list == []

    def test_default_also_allow_is_empty(self) -> None:
        policy = ToolPolicy()
        assert policy.also_allow == []

    def test_default_exec_policy(self) -> None:
        policy = ToolPolicy()
        assert policy.exec_policy.security == "allowlist"
        assert policy.exec_policy.ask == "on-miss"

    def test_default_fs_policy(self) -> None:
        policy = ToolPolicy()
        assert policy.fs.workspace_only is True

    def test_default_elevated_policy(self) -> None:
        policy = ToolPolicy()
        assert policy.elevated.enabled is False
        assert policy.elevated.allow_from == []

    def test_default_web_policy(self) -> None:
        policy = ToolPolicy()
        assert policy.web.search.provider == "brave"
        assert policy.web.fetch.enabled is True


class TestPresetFactories:
    def test_minimal_preset(self) -> None:
        policy = ToolPolicy.minimal()
        assert policy.profile == "minimal"

    def test_coding_preset(self) -> None:
        policy = ToolPolicy.coding()
        assert policy.profile == "coding"

    def test_messaging_preset(self) -> None:
        policy = ToolPolicy.messaging()
        assert policy.profile == "messaging"

    def test_full_preset(self) -> None:
        policy = ToolPolicy.full()
        assert policy.profile == "full"

    def test_preset_has_default_sub_policies(self) -> None:
        """Presets should have the same defaults as base construction."""
        policy = ToolPolicy.minimal()
        assert policy.exec_policy == ExecPolicy()
        assert policy.fs == FsPolicy()
        assert policy.elevated == ElevatedPolicy()
        assert policy.web == WebPolicy()


class TestFluentDeny:
    def test_deny_adds_tools(self) -> None:
        policy = ToolPolicy().deny("shell", "sudo")
        assert policy.deny_list == ["shell", "sudo"]

    def test_deny_is_additive(self) -> None:
        policy = ToolPolicy().deny("shell").deny("sudo").deny("rm")
        assert policy.deny_list == ["shell", "sudo", "rm"]

    def test_deny_deduplicates(self) -> None:
        policy = ToolPolicy().deny("shell", "sudo").deny("shell", "rm")
        assert policy.deny_list == ["shell", "sudo", "rm"]

    def test_deny_preserves_order(self) -> None:
        policy = ToolPolicy().deny("b", "a").deny("c", "a")
        assert policy.deny_list == ["b", "a", "c"]


class TestFluentAllowTools:
    def test_allow_tools_adds(self) -> None:
        policy = ToolPolicy().allow_tools("file_read", "file_write")
        assert policy.allow == ["file_read", "file_write"]

    def test_allow_tools_deduplicates(self) -> None:
        policy = ToolPolicy().allow_tools("a", "b").allow_tools("b", "c")
        assert policy.allow == ["a", "b", "c"]


class TestFluentWithExec:
    def test_with_exec_updates_security(self) -> None:
        policy = ToolPolicy().with_exec(security="full")
        assert policy.exec_policy.security == "full"
        assert policy.exec_policy.ask == "on-miss"  # default preserved

    def test_with_exec_updates_ask(self) -> None:
        policy = ToolPolicy().with_exec(ask="always")
        assert policy.exec_policy.ask == "always"
        assert policy.exec_policy.security == "allowlist"  # default preserved

    def test_with_exec_updates_both(self) -> None:
        policy = ToolPolicy().with_exec(security="deny", ask="off")
        assert policy.exec_policy.security == "deny"
        assert policy.exec_policy.ask == "off"


class TestFluentWithFs:
    def test_with_fs_default(self) -> None:
        policy = ToolPolicy().with_fs()
        assert policy.fs.workspace_only is True

    def test_with_fs_false(self) -> None:
        policy = ToolPolicy().with_fs(workspace_only=False)
        assert policy.fs.workspace_only is False


class TestImmutability:
    def test_deny_does_not_mutate_original(self) -> None:
        original = ToolPolicy()
        _ = original.deny("shell")
        assert original.deny_list == []

    def test_allow_tools_does_not_mutate_original(self) -> None:
        original = ToolPolicy()
        _ = original.allow_tools("file_read")
        assert original.allow == []

    def test_with_exec_does_not_mutate_original(self) -> None:
        original = ToolPolicy()
        _ = original.with_exec(security="full")
        assert original.exec_policy.security == "allowlist"

    def test_with_fs_does_not_mutate_original(self) -> None:
        original = ToolPolicy()
        _ = original.with_fs(workspace_only=False)
        assert original.fs.workspace_only is True

    def test_chained_fluent_calls_preserve_immutability(self) -> None:
        base = ToolPolicy.minimal()
        derived = base.deny("shell").allow_tools("read").with_exec(security="full")
        assert base.deny_list == []
        assert base.allow == []
        assert base.exec_policy.security == "allowlist"
        assert derived.deny_list == ["shell"]
        assert derived.allow == ["read"]
        assert derived.exec_policy.security == "full"
        assert derived.profile == "minimal"


class TestToOpenclaw:
    def test_basic_output(self) -> None:
        policy = ToolPolicy()
        out = policy.to_openclaw()
        assert out["profile"] == "coding"
        assert out["exec"] == {"security": "allowlist", "ask": "on-miss"}
        assert out["fs"] == {"workspaceOnly": True}
        assert out["elevated"] == {"enabled": False, "allowFrom": []}
        assert out["web"] == {
            "search": {"provider": "brave"},
            "fetch": {"enabled": True},
        }

    def test_omits_empty_allow(self) -> None:
        policy = ToolPolicy()
        out = policy.to_openclaw()
        assert "allow" not in out

    def test_omits_empty_deny(self) -> None:
        policy = ToolPolicy()
        out = policy.to_openclaw()
        assert "deny" not in out

    def test_omits_empty_also_allow(self) -> None:
        policy = ToolPolicy()
        out = policy.to_openclaw()
        assert "alsoAllow" not in out

    def test_includes_allow_when_present(self) -> None:
        policy = ToolPolicy().allow_tools("read", "write")
        out = policy.to_openclaw()
        assert out["allow"] == ["read", "write"]

    def test_includes_deny_when_present(self) -> None:
        policy = ToolPolicy().deny("shell")
        out = policy.to_openclaw()
        assert out["deny"] == ["shell"]

    def test_includes_also_allow_when_present(self) -> None:
        policy = ToolPolicy(also_allow=["custom_tool"])
        out = policy.to_openclaw()
        assert out["alsoAllow"] == ["custom_tool"]

    def test_full_preset_output(self) -> None:
        policy = (
            ToolPolicy.full()
            .deny("sudo")
            .allow_tools("file_read")
            .with_exec(security="full", ask="off")
            .with_fs(workspace_only=False)
        )
        out = policy.to_openclaw()
        assert out["profile"] == "full"
        assert out["deny"] == ["sudo"]
        assert out["allow"] == ["file_read"]
        assert out["exec"] == {"security": "full", "ask": "off"}
        assert out["fs"] == {"workspaceOnly": False}


class TestDenyAlias:
    def test_constructor_accepts_deny_alias(self) -> None:
        policy = ToolPolicy(deny=["shell", "sudo"])  # type: ignore[call-arg]
        assert policy.deny_list == ["shell", "sudo"]

    def test_constructor_accepts_deny_list(self) -> None:
        policy = ToolPolicy(deny_list=["shell", "sudo"])
        assert policy.deny_list == ["shell", "sudo"]


class TestRoundtrip:
    def test_full_roundtrip(self) -> None:
        """Build a policy via fluent API, serialize, and verify structure."""
        policy = (
            ToolPolicy.coding()
            .deny("sudo", "rm")
            .allow_tools("file_read", "file_write")
            .with_exec(security="allowlist", ask="always")
            .with_fs(workspace_only=True)
        )

        out = policy.to_openclaw()

        assert out == {
            "profile": "coding",
            "allow": ["file_read", "file_write"],
            "deny": ["sudo", "rm"],
            "exec": {"security": "allowlist", "ask": "always"},
            "fs": {"workspaceOnly": True},
            "elevated": {"enabled": False, "allowFrom": []},
            "web": {
                "search": {"provider": "brave"},
                "fetch": {"enabled": True},
            },
        }

    def test_roundtrip_with_all_fields_populated(self) -> None:
        """Ensure every field appears when populated."""
        policy = ToolPolicy(
            profile="full",
            allow=["a"],
            deny=["b"],  # type: ignore[call-arg]
            also_allow=["c"],
            exec=ExecPolicy(security="full", ask="off"),  # type: ignore[call-arg]
            fs=FsPolicy(workspace_only=False),
            elevated=ElevatedPolicy(enabled=True, allow_from=["admin"]),
            web=WebPolicy(
                search=WebSearchPolicy(provider="google"),
                fetch=WebFetchPolicy(enabled=False),
            ),
        )

        out = policy.to_openclaw()

        assert out["profile"] == "full"
        assert out["allow"] == ["a"]
        assert out["deny"] == ["b"]
        assert out["alsoAllow"] == ["c"]
        assert out["exec"] == {"security": "full", "ask": "off"}
        assert out["fs"] == {"workspaceOnly": False}
        assert out["elevated"] == {"enabled": True, "allowFrom": ["admin"]}
        assert out["web"] == {
            "search": {"provider": "google"},
            "fetch": {"enabled": False},
        }

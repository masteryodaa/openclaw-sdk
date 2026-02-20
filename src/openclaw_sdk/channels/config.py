from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from openclaw_sdk.core.constants import ChannelType


class ChannelConfig(BaseModel):
    channel_type: ChannelType
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class WhatsAppChannelConfig(ChannelConfig):
    channel_type: ChannelType = ChannelType.WHATSAPP
    dm_policy: Literal["all", "contacts", "allowlist"] = "contacts"
    allow_from: list[str] = Field(default_factory=list)
    auto_reconnect: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelegramChannelConfig(ChannelConfig):
    channel_type: ChannelType = ChannelType.TELEGRAM
    dm_policy: Literal["all", "contacts", "allowlist"] = "all"
    allow_from: list[str] = Field(default_factory=list)
    auto_reconnect: bool = True


class DiscordChannelConfig(ChannelConfig):
    channel_type: ChannelType = ChannelType.DISCORD
    dm_policy: Literal["all", "contacts", "allowlist"] = "contacts"
    allow_from: list[str] = Field(default_factory=list)
    guild_id: str | None = None


class SlackChannelConfig(ChannelConfig):
    channel_type: ChannelType = ChannelType.SLACK
    dm_policy: Literal["all", "contacts", "allowlist"] = "contacts"
    allow_from: list[str] = Field(default_factory=list)
    team_id: str | None = None


class GenericChannelConfig(ChannelConfig):
    channel_type: ChannelType = ChannelType.CUSTOM
    channel_name: str = ""

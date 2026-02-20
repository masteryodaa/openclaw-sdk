"""OpenClaw Python SDK — Wrap. Enhance. Ship."""

from openclaw_sdk.__version__ import __version__

# Compatibility metadata (Section 8.2 of spec)
# Declare the range of OpenClaw gateway versions this SDK release supports.
# SDK startup may optionally warn when the connected OpenClaw is outside this range.
__openclaw_compat__ = {
    "min": "2026.2.0",              # Minimum supported OpenClaw version
    "max_tested": "2026.2.3-1",     # Highest version tested against
}

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.channels.config import (
    ChannelConfig,
    DiscordChannelConfig,
    GenericChannelConfig,
    SlackChannelConfig,
    TelegramChannelConfig,
    WhatsAppChannelConfig,
)
from openclaw_sdk.core.config import AgentConfig, ClientConfig, ExecutionOptions
from openclaw_sdk.core.constants import (
    AgentStatus,
    ChannelType,
    EventType,
    GatewayMode,
    MemoryBackend,
    ToolType,
)
from openclaw_sdk.core.exceptions import (
    AgentExecutionError,
    AgentNotFoundError,
    CallbackError,
    ChannelError,
    ConfigurationError,
    GatewayError,
    OpenClawError,
    OutputParsingError,
    PipelineError,
    ScheduleError,
    SkillError,
    SkillNotFoundError,
    StreamError,
    WebhookError,
)
from openclaw_sdk.core.types import (
    AgentSummary,
    Attachment,
    ExecutionResult,
    GeneratedFile,
    HealthStatus,
    SessionInfo,
    StreamEvent,
    TokenUsage,
    ToolCall,
)
from openclaw_sdk.memory.config import MemoryConfig
from openclaw_sdk.scheduling.manager import CronJob, ScheduleConfig, ScheduleManager
from openclaw_sdk.skills.clawhub import ClawHub, ClawHubSkill
from openclaw_sdk.skills.manager import SkillInfo, SkillManager
from openclaw_sdk.tools.config import (
    BrowserToolConfig,
    DatabaseToolConfig,
    FileToolConfig,
    ShellToolConfig,
    ToolConfig,
    WebSearchToolConfig,
)
from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.config.manager import ConfigManager
from openclaw_sdk.devices.manager import DeviceManager
from openclaw_sdk.nodes.manager import NodeManager
from openclaw_sdk.ops.manager import OpsManager
from openclaw_sdk.webhooks.manager import WebhookConfig, WebhookManager

__all__ = [
    "__version__",
    "__openclaw_compat__",
    "OpenClawClient",
    "Agent",
    "ClientConfig",
    "AgentConfig",
    "ExecutionOptions",
    "GatewayMode",
    "AgentStatus",
    "EventType",
    "ChannelType",
    "ToolType",
    "MemoryBackend",
    "OpenClawError",
    "ConfigurationError",
    "GatewayError",
    "AgentNotFoundError",
    "AgentExecutionError",
    "StreamError",
    "ChannelError",
    "SkillError",
    "SkillNotFoundError",
    "WebhookError",
    "ScheduleError",
    "PipelineError",
    "OutputParsingError",
    "CallbackError",
    "Attachment",
    "ToolCall",
    "GeneratedFile",
    "TokenUsage",
    "ExecutionResult",
    "StreamEvent",
    "AgentSummary",
    "HealthStatus",
    "SessionInfo",
    "ToolConfig",
    "DatabaseToolConfig",
    "FileToolConfig",
    "BrowserToolConfig",
    "ShellToolConfig",
    "WebSearchToolConfig",
    "ChannelConfig",
    "WhatsAppChannelConfig",
    "TelegramChannelConfig",
    "DiscordChannelConfig",
    "SlackChannelConfig",
    "GenericChannelConfig",
    "MemoryConfig",
    "SkillManager",
    "SkillInfo",
    "ClawHub",
    "ClawHubSkill",
    "WebhookManager",
    "WebhookConfig",
    "ScheduleManager",
    "ScheduleConfig",
    "CronJob",
    "ConfigManager",
    "DeviceManager",
    "ApprovalManager",
    "NodeManager",
    "OpsManager",
]
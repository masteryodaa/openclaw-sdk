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
    ContentBlock,
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
from openclaw_sdk.skills.config import SkillEntry, SkillInstallConfig, SkillLoadConfig, SkillsConfig
from openclaw_sdk.skills.manager import SkillInfo, SkillManager
from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.cache.base import InMemoryCache, ResponseCache
from openclaw_sdk.config.manager import ConfigManager
from openclaw_sdk.devices.manager import DeviceManager
from openclaw_sdk.nodes.manager import NodeManager
from openclaw_sdk.ops.manager import OpsManager
from openclaw_sdk.tracing.span import Span
from openclaw_sdk.tracing.tracer import Tracer, TracingCallbackHandler
from openclaw_sdk.prompts.template import PromptTemplate
from openclaw_sdk.prompts.versioning import PromptStore, PromptVersion
from openclaw_sdk.evaluation.evaluators import (
    ContainsEvaluator,
    Evaluator,
    ExactMatchEvaluator,
    LengthEvaluator,
    RegexEvaluator,
)
from openclaw_sdk.evaluation.eval_suite import EvalCase, EvalCaseResult, EvalReport, EvalSuite
from openclaw_sdk.tools.policy import (
    ElevatedPolicy,
    ExecPolicy,
    FsPolicy,
    ToolPolicy,
    WebFetchPolicy,
    WebPolicy,
    WebSearchPolicy,
)
from openclaw_sdk.mcp.server import HttpMcpServer, McpServer, StdioMcpServer
from openclaw_sdk.callbacks.handler import (
    CallbackHandler,
    CompositeCallbackHandler,
    CostCallbackHandler,
    LoggingCallbackHandler,
)
from openclaw_sdk.guardrails import (
    ContentFilterGuardrail,
    CostLimitGuardrail,
    Guardrail,
    GuardrailResult,
    MaxTokensGuardrail,
    PIIGuardrail,
    RegexFilterGuardrail,
)
from openclaw_sdk.pipeline.pipeline import ConditionalPipeline
from openclaw_sdk.templates.registry import get_template, list_templates
from openclaw_sdk.webhooks.manager import WebhookConfig, WebhookManager
from openclaw_sdk.coordination import (
    AgentRouter,
    ConsensusGroup,
    ConsensusResult,
    Supervisor,
    SupervisorResult,
)
from openclaw_sdk.multitenancy import Tenant, TenantConfig, TenantWorkspace

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
    "ContentBlock",
    "ToolCall",
    "GeneratedFile",
    "TokenUsage",
    "ExecutionResult",
    "StreamEvent",
    "AgentSummary",
    "HealthStatus",
    "SessionInfo",
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
    "SkillsConfig",
    "SkillEntry",
    "SkillLoadConfig",
    "SkillInstallConfig",
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
    "ResponseCache",
    "InMemoryCache",
    # v0.2 — Tracing
    "Span",
    "Tracer",
    "TracingCallbackHandler",
    # v0.2 — Prompts
    "PromptTemplate",
    "PromptVersion",
    "PromptStore",
    # v0.2 — Evaluation
    "Evaluator",
    "ContainsEvaluator",
    "ExactMatchEvaluator",
    "RegexEvaluator",
    "LengthEvaluator",
    "EvalCase",
    "EvalCaseResult",
    "EvalReport",
    "EvalSuite",
    # Tool Policy
    "ToolPolicy",
    "ExecPolicy",
    "FsPolicy",
    "ElevatedPolicy",
    "WebPolicy",
    "WebSearchPolicy",
    "WebFetchPolicy",
    # MCP Servers
    "McpServer",
    "StdioMcpServer",
    "HttpMcpServer",
    # Callbacks
    "CallbackHandler",
    "LoggingCallbackHandler",
    "CostCallbackHandler",
    "CompositeCallbackHandler",
    # Templates
    "get_template",
    "list_templates",
    # Conditional Pipeline
    "ConditionalPipeline",
    # Coordination
    "Supervisor",
    "SupervisorResult",
    "ConsensusGroup",
    "ConsensusResult",
    "AgentRouter",
    # Guardrails
    "Guardrail",
    "GuardrailResult",
    "PIIGuardrail",
    "CostLimitGuardrail",
    "ContentFilterGuardrail",
    "MaxTokensGuardrail",
    "RegexFilterGuardrail",
    # Multi-tenancy
    "Tenant",
    "TenantConfig",
    "TenantWorkspace",
]

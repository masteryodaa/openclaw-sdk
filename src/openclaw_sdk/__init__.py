"""OpenClaw Python SDK — Wrap. Enhance. Ship."""

from openclaw_sdk.__version__ import __version__

# Compatibility metadata (Section 8.2 of spec)
# Declare the range of OpenClaw gateway versions this SDK release supports.
# SDK startup may optionally warn when the connected OpenClaw is outside this range.
__openclaw_compat__ = {
    "min": "2026.2.0",  # Minimum supported OpenClaw version
    "max_tested": "2026.2.28",  # Highest version tested against
}

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.conversation import Conversation
from openclaw_sdk.channels.config import (
    ChannelConfig,
    DiscordChannelConfig,
    GenericChannelConfig,
    SlackChannelConfig,
    TelegramChannelConfig,
    WhatsAppChannelConfig,
)
from openclaw_sdk.channels.sms import SMSChannelConfig, SMSMessage, TwilioSMSClient
from openclaw_sdk.core.config import AgentConfig, ClientConfig, ExecutionOptions
from openclaw_sdk.core.constants import (
    AgentStatus,
    ChannelType,
    EventType,
    GatewayMode,
    MemoryBackend,
)
from openclaw_sdk.core.dedup import RequestDeduplicator
from openclaw_sdk.core.exceptions import (
    AgentExecutionError,
    AgentNotFoundError,
    AlertError,
    APIConnectionError,
    APITimeoutError,
    AuditError,
    AuthenticationError,
    AutonomousError,
    BillingError,
    CallbackError,
    ChannelError,
    CircuitOpenError,
    ConfigurationError,
    ConnectorError,
    DashboardError,
    DataSourceError,
    GatewayError,
    OpenClawError,
    OutputParsingError,
    PipelineError,
    PluginError,
    RateLimitError,
    ScheduleError,
    SkillError,
    SkillNotFoundError,
    StreamError,
    VoiceError,
    WebhookError,
    WorkflowError,
)
from openclaw_sdk.core.types import (
    AgentFileContent,
    AgentFileInfo,
    AgentIdentity,
    AgentListItem,
    AgentListResponse,
    AgentSummary,
    Attachment,
    ContentBlock,
    ContentEvent,
    DoneEvent,
    ErrorEvent,
    ExecutionResult,
    FileEvent,
    GeneratedFile,
    HealthStatus,
    SessionInfo,
    StreamEvent,
    ThinkingEvent,
    TokenUsage,
    ToolCall,
    ToolCallEvent,
    ToolResultEvent,
    TypedStreamEvent,
)
from openclaw_sdk.memory.config import MemoryConfig
from openclaw_sdk.scheduling.manager import CronJob, ScheduleConfig, ScheduleManager
from openclaw_sdk.skills.clawhub import ClawHub, ClawHubSkill
from openclaw_sdk.skills.config import (
    SkillEntry,
    SkillInstallConfig,
    SkillLoadConfig,
    SkillsConfig,
)
from openclaw_sdk.skills.manager import SkillInfo, SkillManager
from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.cache.base import InMemoryCache, ResponseCache
from openclaw_sdk.cache.embeddings import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    SimpleEmbeddingProvider,
)
from openclaw_sdk.cache.semantic import SemanticCache
from openclaw_sdk.config.manager import ConfigManager, KNOWN_PROVIDERS
from openclaw_sdk.devices.manager import DeviceManager
from openclaw_sdk.nodes.manager import NodeManager
from openclaw_sdk.ops.manager import OpsManager
from openclaw_sdk.tts.manager import TTSManager
from openclaw_sdk.tracing.otel import OTelCallbackHandler
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
from openclaw_sdk.evaluation.eval_suite import (
    EvalCase,
    EvalCaseResult,
    EvalReport,
    EvalSuite,
)
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
from openclaw_sdk.webhooks.manager import (
    DeliveryStatus,
    WebhookConfig,
    WebhookDelivery,
    WebhookDeliveryEngine,
    WebhookManager,
)
from openclaw_sdk.coordination import (
    AgentRouter,
    ConsensusGroup,
    ConsensusResult,
    Supervisor,
    SupervisorResult,
)
from openclaw_sdk.multitenancy import Tenant, TenantConfig, TenantWorkspace
from openclaw_sdk.resilience.circuit_breaker import CircuitBreaker
from openclaw_sdk.resilience.rate_limiter import RateLimiter
from openclaw_sdk.resilience.retry import RetryPolicy, retry_async

# v2.0 — Plugins
from openclaw_sdk.plugins import Plugin, PluginHook, PluginMetadata, PluginRegistry

# v2.0 — Alerting
from openclaw_sdk.alerting import (
    Alert,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertSink,
    ConsecutiveFailureRule,
    CostThresholdRule,
    ErrorRateRule,
    LatencyThresholdRule,
    LogAlertSink,
    PagerDutyAlertSink,
    SlackAlertSink,
    WebhookAlertSink,
)

# v2.0 — Audit
from openclaw_sdk.audit import (
    AuditEvent,
    AuditLogger,
    AuditSink,
    FileAuditSink,
    InMemoryAuditSink,
    StructlogAuditSink,
)

# v2.0 — Billing
from openclaw_sdk.billing import (
    BillingManager,
    BillingPeriod,
    Invoice,
    LineItem,
    PricingTier,
    UsageRecord,
)

# v2.0 — Data Sources
from openclaw_sdk.data import (
    ColumnInfo,
    DataSource,
    DataSourceRegistry,
    QueryResult,
    SQLiteDataSource,
    SupabaseDataSource,
    TableInfo,
)

# v2.0 — Connectors
from openclaw_sdk.connectors import (
    Connector,
    ConnectorAction,
    ConnectorConfig,
    GitHubConnector,
    GmailConnector,
    GoogleSheetsConnector,
    HubSpotConnector,
    JiraConnector,
    NotionConnector,
    SalesforceConnector,
    SlackConnector,
    StripeConnector,
    ZendeskConnector,
)

# v2.0 — Autonomous
from openclaw_sdk.autonomous import (
    AgentCapability,
    Budget,
    Goal,
    GoalLoop,
    GoalStatus,
    Orchestrator,
    Watchdog,
    WatchdogAction,
)

# v2.0 — Voice
from openclaw_sdk.voice import (
    DeepgramSTT,
    ElevenLabsTTS,
    OpenAITTS,
    STTProvider,
    TTSProvider,
    VoicePipeline,
    VoiceResult,
    WhisperSTT,
)

# v2.0 — Workflows
from openclaw_sdk.workflows import (
    StepStatus,
    StepType,
    Workflow,
    WorkflowResult,
    WorkflowStep,
    research_workflow,
    review_workflow,
    support_workflow,
)

__all__ = [
    "__version__",
    "__openclaw_compat__",
    # Core
    "OpenClawClient",
    "Agent",
    "Conversation",
    "ClientConfig",
    "AgentConfig",
    "ExecutionOptions",
    "GatewayMode",
    "AgentStatus",
    "EventType",
    "ChannelType",
    "MemoryBackend",
    "RequestDeduplicator",
    # Exceptions
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
    "RateLimitError",
    "AuthenticationError",
    "APITimeoutError",
    "APIConnectionError",
    "CircuitOpenError",
    "AlertError",
    "AuditError",
    "AutonomousError",
    "BillingError",
    "ConnectorError",
    "DashboardError",
    "DataSourceError",
    "PluginError",
    "VoiceError",
    "WorkflowError",
    # Types
    "AgentFileContent",
    "AgentFileInfo",
    "AgentIdentity",
    "AgentListItem",
    "AgentListResponse",
    "Attachment",
    "ContentBlock",
    "ToolCall",
    "GeneratedFile",
    "TokenUsage",
    "ExecutionResult",
    "StreamEvent",
    "TypedStreamEvent",
    "ContentEvent",
    "ThinkingEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "FileEvent",
    "DoneEvent",
    "ErrorEvent",
    "AgentSummary",
    "HealthStatus",
    "SessionInfo",
    # Channels
    "ChannelConfig",
    "WhatsAppChannelConfig",
    "TelegramChannelConfig",
    "DiscordChannelConfig",
    "SlackChannelConfig",
    "GenericChannelConfig",
    "SMSChannelConfig",
    "SMSMessage",
    "TwilioSMSClient",
    # Memory
    "MemoryConfig",
    # Skills
    "SkillManager",
    "SkillInfo",
    "ClawHub",
    "ClawHubSkill",
    "SkillsConfig",
    "SkillEntry",
    "SkillLoadConfig",
    "SkillInstallConfig",
    # Managers
    "WebhookManager",
    "WebhookConfig",
    "WebhookDelivery",
    "WebhookDeliveryEngine",
    "DeliveryStatus",
    "ScheduleManager",
    "ScheduleConfig",
    "CronJob",
    "ConfigManager",
    "KNOWN_PROVIDERS",
    "DeviceManager",
    "ApprovalManager",
    "NodeManager",
    "OpsManager",
    "TTSManager",
    # Cache
    "ResponseCache",
    "InMemoryCache",
    "SemanticCache",
    "EmbeddingProvider",
    "SimpleEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    # Tracing
    "OTelCallbackHandler",
    "Span",
    "Tracer",
    "TracingCallbackHandler",
    # Prompts
    "PromptTemplate",
    "PromptVersion",
    "PromptStore",
    # Evaluation
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
    # Pipeline
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
    # Resilience
    "RetryPolicy",
    "retry_async",
    "CircuitBreaker",
    "CircuitOpenError",
    "RateLimiter",
    # v2.0 — Plugins
    "Plugin",
    "PluginHook",
    "PluginMetadata",
    "PluginRegistry",
    # v2.0 — Alerting
    "Alert",
    "AlertManager",
    "AlertRule",
    "AlertSeverity",
    "AlertSink",
    "CostThresholdRule",
    "LatencyThresholdRule",
    "ErrorRateRule",
    "ConsecutiveFailureRule",
    "LogAlertSink",
    "WebhookAlertSink",
    "SlackAlertSink",
    "PagerDutyAlertSink",
    # v2.0 — Audit
    "AuditEvent",
    "AuditLogger",
    "AuditSink",
    "InMemoryAuditSink",
    "FileAuditSink",
    "StructlogAuditSink",
    # v2.0 — Billing
    "BillingManager",
    "BillingPeriod",
    "Invoice",
    "LineItem",
    "PricingTier",
    "UsageRecord",
    # v2.0 — Data Sources
    "DataSource",
    "QueryResult",
    "ColumnInfo",
    "TableInfo",
    "DataSourceRegistry",
    "SQLiteDataSource",
    "SupabaseDataSource",
    # v2.0 — Connectors
    "Connector",
    "ConnectorConfig",
    "ConnectorAction",
    "GitHubConnector",
    "SlackConnector",
    "GoogleSheetsConnector",
    "GmailConnector",
    "NotionConnector",
    "JiraConnector",
    "StripeConnector",
    "HubSpotConnector",
    "SalesforceConnector",
    "ZendeskConnector",
    # v2.0 — Autonomous
    "Goal",
    "GoalStatus",
    "GoalLoop",
    "Budget",
    "AgentCapability",
    "Orchestrator",
    "Watchdog",
    "WatchdogAction",
    # v2.0 — Voice
    "STTProvider",
    "WhisperSTT",
    "DeepgramSTT",
    "TTSProvider",
    "OpenAITTS",
    "ElevenLabsTTS",
    "VoicePipeline",
    "VoiceResult",
    # v2.0 — Workflows
    "Workflow",
    "WorkflowStep",
    "WorkflowResult",
    "StepStatus",
    "StepType",
    "review_workflow",
    "research_workflow",
    "support_workflow",
]

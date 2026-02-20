from __future__ import annotations

from typing import Any


class OpenClawError(Exception):
    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ConfigurationError(OpenClawError): ...


class ConnectionError(OpenClawError): ...


class GatewayError(OpenClawError): ...


class AgentNotFoundError(OpenClawError): ...


class AgentExecutionError(OpenClawError): ...


class TimeoutError(OpenClawError): ...


class StreamError(OpenClawError): ...


class ChannelError(OpenClawError): ...


class SkillError(OpenClawError): ...


class SkillNotFoundError(SkillError): ...


class WebhookError(OpenClawError): ...


class ScheduleError(OpenClawError): ...


class PipelineError(OpenClawError): ...


class OutputParsingError(OpenClawError): ...


class CallbackError(OpenClawError): ...

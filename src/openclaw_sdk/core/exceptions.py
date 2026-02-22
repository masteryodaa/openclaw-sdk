from __future__ import annotations

from typing import Any


class OpenClawError(Exception):
    """Base exception for all OpenClaw SDK errors.

    Attributes:
        code: Optional machine-readable error code (e.g. ``"ERR_001"``).
        details: Arbitrary key/value context about the error.
        status_code: HTTP-style status code when the error originates from
            a gateway / API response (``None`` when not applicable).
        retry_after: Suggested delay in seconds before retrying the
            operation (``None`` when unknown or not applicable).
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        self.retry_after = retry_after

    @property
    def is_retryable(self) -> bool:
        """Whether the operation that raised this error can be retried."""
        return False


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


# ---------------------------------------------------------------------------
# Retryable / non-retryable specialisations
# ---------------------------------------------------------------------------


class RateLimitError(GatewayError):
    """The gateway returned a rate-limit (HTTP 429) response.

    Always retryable.  ``retry_after`` is populated when the gateway
    supplies a ``Retry-After`` header or equivalent payload field.
    """

    @property
    def is_retryable(self) -> bool:  # noqa: D102
        return True


class AuthenticationError(GatewayError):
    """Authentication / authorisation failure (HTTP 401/403).

    Never retryable — the caller must fix credentials before retrying.
    """

    @property
    def is_retryable(self) -> bool:  # noqa: D102
        return False


class APITimeoutError(TimeoutError):
    """The gateway or upstream API did not respond within the deadline.

    Always retryable — the request may succeed on a subsequent attempt.
    """

    @property
    def is_retryable(self) -> bool:  # noqa: D102
        return True


class APIConnectionError(ConnectionError):
    """A transport-level connection failure (DNS, TCP, TLS).

    Always retryable — transient network issues are common.
    """

    @property
    def is_retryable(self) -> bool:  # noqa: D102
        return True


class CircuitOpenError(OpenClawError):
    """Raised when a circuit breaker is open and rejecting calls.

    Not retryable — the caller should wait for the circuit breaker to
    transition to half-open before retrying.
    """

    @property
    def is_retryable(self) -> bool:  # noqa: D102
        return False


# ---------------------------------------------------------------------------
# v2.0 module exceptions
# ---------------------------------------------------------------------------


class DataSourceError(OpenClawError): ...


class ConnectorError(OpenClawError): ...


class VoiceError(OpenClawError): ...


class WorkflowError(OpenClawError): ...


class AuditError(OpenClawError): ...


class AlertError(OpenClawError): ...


class BillingError(OpenClawError): ...


class DashboardError(OpenClawError): ...


class PluginError(OpenClawError): ...


class AutonomousError(OpenClawError): ...

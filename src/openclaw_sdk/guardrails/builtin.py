"""Built-in guardrail implementations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from openclaw_sdk.guardrails.base import Guardrail, GuardrailResult

if TYPE_CHECKING:
    from openclaw_sdk.tracking.cost import CostTracker


# ---------------------------------------------------------------------------
# PII patterns
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# US phone: optional +1, then 10 digits with optional separators
_PHONE_PATTERN = re.compile(
    r"(?:\+?1[\s\-.]?)?"            # optional country code
    r"(?:\(?\d{3}\)?[\s\-.]?)"      # area code
    r"\d{3}[\s\-.]?"                # exchange
    r"\d{4}"                         # subscriber
)

# SSN: xxx-xx-xxxx
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Credit card: 16 digits with optional separators (spaces or dashes)
_CC_PATTERN = re.compile(r"\b(?:\d[ \-]?){15}\d\b")

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": _EMAIL_PATTERN,
    "phone": _PHONE_PATTERN,
    "ssn": _SSN_PATTERN,
    "credit_card": _CC_PATTERN,
}


class PIIGuardrail(Guardrail):
    """Detects and optionally redacts personally-identifiable information.

    Supported PII types: email addresses, US phone numbers, SSNs, and
    credit-card numbers (16-digit).

    Args:
        action: What to do when PII is detected.
            * ``"block"`` -- fail the check (default).
            * ``"redact"`` -- replace detected PII with ``[REDACTED]`` and pass.
            * ``"warn"`` -- pass the check but attach a warning message.
    """

    def __init__(self, action: Literal["block", "redact", "warn"] = "block") -> None:
        self._action = action

    async def check_input(self, query: str) -> GuardrailResult:
        return self._check(query)

    async def check_output(self, response: str) -> GuardrailResult:
        return self._check(response)

    # ------------------------------------------------------------------

    def _check(self, text: str) -> GuardrailResult:
        detected: list[str] = []
        for pii_type, pattern in _PII_PATTERNS.items():
            if pattern.search(text):
                detected.append(pii_type)

        if not detected:
            return GuardrailResult(
                passed=True,
                guardrail_name=self.name,
                message="No PII detected.",
            )

        types_str = ", ".join(detected)

        if self._action == "block":
            return GuardrailResult(
                passed=False,
                guardrail_name=self.name,
                message=f"PII detected ({types_str}). Blocked.",
            )

        if self._action == "redact":
            redacted = text
            for pattern in _PII_PATTERNS.values():
                redacted = pattern.sub("[REDACTED]", redacted)
            return GuardrailResult(
                passed=True,
                guardrail_name=self.name,
                message=f"PII detected ({types_str}). Redacted.",
                modified_text=redacted,
            )

        # action == "warn"
        return GuardrailResult(
            passed=True,
            guardrail_name=self.name,
            message=f"PII detected ({types_str}). Warning only.",
        )


class CostLimitGuardrail(Guardrail):
    """Blocks execution when the estimated session cost would exceed a budget.

    Args:
        max_cost_usd: Maximum allowed cumulative cost in US dollars.
        tracker: An optional :class:`CostTracker` instance. When ``None`` the
                 guardrail always passes (no cost data available).
    """

    def __init__(
        self,
        max_cost_usd: float,
        tracker: CostTracker | None = None,
    ) -> None:
        self._max_cost_usd = max_cost_usd
        self._tracker = tracker

    async def check_input(self, query: str) -> GuardrailResult:
        if self._tracker is None:
            return GuardrailResult(
                passed=True,
                guardrail_name=self.name,
                message="No cost tracker attached; skipping cost check.",
            )

        summary = self._tracker.get_summary()
        current_cost = summary.total_cost_usd

        if current_cost >= self._max_cost_usd:
            return GuardrailResult(
                passed=False,
                guardrail_name=self.name,
                message=(
                    f"Cost limit exceeded: ${current_cost:.4f} >= "
                    f"${self._max_cost_usd:.4f}."
                ),
            )

        return GuardrailResult(
            passed=True,
            guardrail_name=self.name,
            message=(
                f"Cost OK: ${current_cost:.4f} / ${self._max_cost_usd:.4f}."
            ),
        )

    async def check_output(self, response: str) -> GuardrailResult:
        # Cost is already incurred by the time we see the output.
        return GuardrailResult(
            passed=True,
            guardrail_name=self.name,
            message="Output check always passes (cost already incurred).",
        )


class ContentFilterGuardrail(Guardrail):
    """Blocks queries or responses that contain banned words.

    Args:
        blocked_words: List of words to block.
        case_sensitive: Whether to perform case-sensitive matching.
                        Defaults to ``False`` (case-insensitive).
    """

    def __init__(
        self,
        blocked_words: list[str],
        case_sensitive: bool = False,
    ) -> None:
        self._case_sensitive = case_sensitive
        if case_sensitive:
            self._blocked_words = list(blocked_words)
        else:
            self._blocked_words = [w.lower() for w in blocked_words]

    async def check_input(self, query: str) -> GuardrailResult:
        return self._check(query)

    async def check_output(self, response: str) -> GuardrailResult:
        return self._check(response)

    def _check(self, text: str) -> GuardrailResult:
        compare_text = text if self._case_sensitive else text.lower()

        found: list[str] = []
        for word in self._blocked_words:
            if word in compare_text:
                found.append(word)

        if found:
            return GuardrailResult(
                passed=False,
                guardrail_name=self.name,
                message=f"Blocked words detected: {', '.join(found)}.",
            )

        return GuardrailResult(
            passed=True,
            guardrail_name=self.name,
            message="No blocked words detected.",
        )


class MaxTokensGuardrail(Guardrail):
    """Limits the length of agent responses.

    Args:
        max_chars: Maximum allowed character count for the output.
                   Defaults to 10 000.
    """

    def __init__(self, max_chars: int = 10_000) -> None:
        self._max_chars = max_chars

    async def check_input(self, query: str) -> GuardrailResult:
        return GuardrailResult(
            passed=True,
            guardrail_name=self.name,
            message="Input check always passes.",
        )

    async def check_output(self, response: str) -> GuardrailResult:
        length = len(response)
        if length > self._max_chars:
            return GuardrailResult(
                passed=False,
                guardrail_name=self.name,
                message=(
                    f"Response too long: {length} chars > "
                    f"{self._max_chars} max."
                ),
            )
        return GuardrailResult(
            passed=True,
            guardrail_name=self.name,
            message=f"Response length OK: {length} chars.",
        )


class RegexFilterGuardrail(Guardrail):
    """Custom regex-based blocking guardrail.

    Args:
        patterns: List of regex pattern strings. Any match triggers the action.
        action: ``"block"`` (default) fails the check; ``"warn"`` passes but
                attaches a warning message.
    """

    def __init__(
        self,
        patterns: list[str],
        action: Literal["block", "warn"] = "block",
    ) -> None:
        self._compiled = [re.compile(p) for p in patterns]
        self._action = action

    async def check_input(self, query: str) -> GuardrailResult:
        return self._check(query)

    async def check_output(self, response: str) -> GuardrailResult:
        return self._check(response)

    def _check(self, text: str) -> GuardrailResult:
        matched: list[str] = []
        for pattern in self._compiled:
            if pattern.search(text):
                matched.append(pattern.pattern)

        if not matched:
            return GuardrailResult(
                passed=True,
                guardrail_name=self.name,
                message="No regex patterns matched.",
            )

        patterns_str = ", ".join(matched)

        if self._action == "block":
            return GuardrailResult(
                passed=False,
                guardrail_name=self.name,
                message=f"Regex patterns matched: {patterns_str}. Blocked.",
            )

        # action == "warn"
        return GuardrailResult(
            passed=True,
            guardrail_name=self.name,
            message=f"Regex patterns matched: {patterns_str}. Warning only.",
        )

# Guardrails

Validate inputs and outputs to keep agents safe and compliant. Block PII, limit costs, filter content.

## Overview

Guardrails check queries before execution and responses after. Each guardrail returns a `GuardrailResult` with pass/fail status and an optional message.

```python
from openclaw_sdk import PIIGuardrail, CostLimitGuardrail, ContentFilterGuardrail

# Check for PII in user input
pii = PIIGuardrail(action="block")
result = await pii.check_input("My SSN is 123-45-6789")
print(result.passed)   # False
print(result.message)  # "PII detected: SSN"
```

## Built-in Guardrails

### PII Detection

Detects emails, phone numbers, SSNs, and credit card numbers:

```python
from openclaw_sdk import PIIGuardrail

# Block: fail the check if PII found
blocker = PIIGuardrail(action="block")

# Redact: replace PII with [REDACTED]
redactor = PIIGuardrail(action="redact")
result = await redactor.check_input("Email me at john@example.com")
print(result.modified_text)  # "Email me at [REDACTED]"

# Warn: pass but flag the issue
warner = PIIGuardrail(action="warn")
result = await warner.check_input("Call 555-123-4567")
print(result.passed)   # True
print(result.message)  # "PII detected: phone number"
```

### Cost Limits

Prevent runaway spending:

```python
from openclaw_sdk import CostLimitGuardrail, CostTracker

tracker = CostTracker()
guard = CostLimitGuardrail(max_cost_usd=5.00, tracker=tracker)

# Before each execution
result = await guard.check_input("Generate a report")
if not result.passed:
    print(f"Budget exceeded: {result.message}")
```

### Content Filter

Block queries or responses containing banned words:

```python
from openclaw_sdk import ContentFilterGuardrail

filter_guard = ContentFilterGuardrail(
    blocked_words=["hack", "exploit", "attack"],
    case_sensitive=False,
)

result = await filter_guard.check_input("How to hack a website")
print(result.passed)  # False
```

### Max Response Length

Limit output length:

```python
from openclaw_sdk import MaxTokensGuardrail

guard = MaxTokensGuardrail(max_chars=5000)
result = await guard.check_output("A" * 10000)
print(result.passed)  # False
```

### Regex Filter

Custom pattern-based filtering:

```python
from openclaw_sdk import RegexFilterGuardrail

# Block SQL injection patterns
sql_guard = RegexFilterGuardrail(
    patterns=[r"(?i)(drop|delete|truncate)\s+table"],
)

result = await sql_guard.check_input("DROP TABLE users")
print(result.passed)  # False
```

## Custom Guardrails

Create your own by extending `Guardrail`:

```python
from openclaw_sdk import Guardrail, GuardrailResult

class LanguageGuardrail(Guardrail):
    """Only allow English text."""

    async def check_input(self, query: str) -> GuardrailResult:
        # Simple heuristic — real implementation would use a language detector
        if all(ord(c) < 128 for c in query if c.isalpha()):
            return GuardrailResult(passed=True, guardrail_name=self.name)
        return GuardrailResult(
            passed=False,
            guardrail_name=self.name,
            message="Non-English text detected",
        )

    async def check_output(self, response: str) -> GuardrailResult:
        return GuardrailResult(passed=True, guardrail_name=self.name)
```

## Composing Guardrails

Run multiple guardrails together:

```python
guardrails = [
    PIIGuardrail(action="block"),
    ContentFilterGuardrail(blocked_words=["hack"]),
    MaxTokensGuardrail(max_chars=10000),
]

query = "Send me the data"
for guard in guardrails:
    result = await guard.check_input(query)
    if not result.passed:
        print(f"Blocked by {result.guardrail_name}: {result.message}")
        break
```

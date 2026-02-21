# Prompt Templates

Prompt templates let you define reusable prompts with placeholder variables.
Use them to build consistent, parameterized queries for your agents without
manual string formatting.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient, PromptTemplate

async def main():
    template = PromptTemplate("Hello {name}, tell me about {topic}")

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")
        prompt = template.render(name="Alice", topic="quantum computing")
        result = await agent.execute(prompt)
        print(result.output)

asyncio.run(main())
```

## Creating Templates

A `PromptTemplate` takes a string with `{variable}` placeholders:

```python
from openclaw_sdk import PromptTemplate

template = PromptTemplate("Summarize the following text in {language}:\n\n{text}")
```

Variable names follow Python identifier rules: letters, digits, and underscores.

## Rendering

Call `.render()` with keyword arguments to fill in all variables and produce
the final prompt string:

```python
template = PromptTemplate("Translate '{phrase}' to {target_language}")

prompt = template.render(phrase="Good morning", target_language="Japanese")
print(prompt)
# Translate 'Good morning' to Japanese
```

!!! warning "All variables required"
    `.render()` raises a `KeyError` if any template variable is not provided.
    Use `.partial()` if you want to fill in variables incrementally.

## Inspecting Variables

The `.variables` property returns the set of variable names found in the
template:

```python
template = PromptTemplate("Dear {name}, your order #{order_id} is {status}")
print(template.variables)
# {'name', 'order_id', 'status'}
```

This is useful for validation, documentation generation, or building dynamic
UIs that prompt users for each variable.

## Partial Application

Use `.partial()` to fill in some variables now and leave the rest for later.
It returns a new `PromptTemplate`:

```python
from openclaw_sdk import PromptTemplate

base = PromptTemplate("You are a {role}. Answer this question: {question}")

# Fix the role, leave question open
tutor = base.partial(role="helpful tutor")
print(tutor.variables)
# {'question'}

# Render the rest later
prompt = tutor.render(question="What causes rain?")
print(prompt)
# You are a helpful tutor. Answer this question: What causes rain?
```

!!! tip "Build template libraries"
    Use `.partial()` to create a library of role-specific templates from a
    single base template. Each partially applied template is an independent
    object that can be rendered separately.

## Composition

Combine two templates with the `+` operator. The result is a new template
whose text is the two originals joined with a newline:

```python
from openclaw_sdk import PromptTemplate

system = PromptTemplate("You are a {role} who speaks {language}.")
task = PromptTemplate("Please help with: {request}")

combined = system + task
print(combined.variables)
# {'role', 'language', 'request'}

prompt = combined.render(role="translator", language="French", request="Translate 'hello'")
print(prompt)
# You are a translator who speaks French.
# Please help with: Translate 'hello'
```

Composition is associative, so you can chain multiple templates:

```python
full = context + instructions + constraints
```

## Using Templates with Agents

Templates integrate naturally with `agent.execute()`:

```python
import asyncio
from openclaw_sdk import OpenClawClient, PromptTemplate

async def main():
    qa_template = PromptTemplate(
        "Answer the following {difficulty} question about {subject}:\n\n{question}"
    )

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")

        questions = [
            {"difficulty": "easy", "subject": "math", "question": "What is 2 + 2?"},
            {"difficulty": "hard", "subject": "physics", "question": "Explain dark matter."},
        ]

        for q in questions:
            prompt = qa_template.render(**q)
            result = await agent.execute(prompt)
            print(f"Q: {q['question']}")
            print(f"A: {result.output}\n")

asyncio.run(main())
```

## Batch Rendering

Generate multiple prompts from a list of variable sets:

```python
from openclaw_sdk import PromptTemplate

template = PromptTemplate("Write a {tone} email to {recipient} about {topic}")

cases = [
    {"tone": "formal", "recipient": "the CEO", "topic": "quarterly results"},
    {"tone": "casual", "recipient": "the team", "topic": "Friday lunch"},
    {"tone": "urgent", "recipient": "support", "topic": "a production outage"},
]

prompts = [template.render(**case) for case in cases]
```

!!! note "Templates are immutable"
    Both `.partial()` and `+` return new `PromptTemplate` instances. The
    original template is never modified, so it is safe to share templates
    across threads or async tasks.

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient, PromptTemplate

async def main():
    # Build a reusable review template
    base = PromptTemplate(
        "You are a {role} reviewing code.\n"
        "Focus on: {focus}\n\n"
        "Code:\n```{language}\n{code}\n```"
    )

    reviewer = base.partial(role="senior software engineer")

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")

        prompt = reviewer.render(
            focus="error handling and edge cases",
            language="python",
            code='def divide(a, b):\n    return a / b',
        )
        result = await agent.execute(prompt)
        print(result.output)

asyncio.run(main())
```

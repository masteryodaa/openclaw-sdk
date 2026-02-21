# Conditional Pipelines

Build complex agent workflows with branching, parallel execution, and error fallbacks.

## Overview

The `ConditionalPipeline` extends the basic `Pipeline` with three powerful patterns:

- **Branching** — route to different agents based on intermediate results
- **Parallel execution** — run multiple agents concurrently
- **Error fallbacks** — automatically retry with a different agent on failure

## Basic Branching

Route queries to different agents based on a condition:

```python
from openclaw_sdk.pipeline.pipeline import ConditionalPipeline

pipeline = ConditionalPipeline(client)

# Step 1: Classify the input
pipeline.add_step("classify", "classifier", "Is this a complaint or question? {input}")

# Step 2: Branch based on classification
pipeline.add_branch(
    "classify",
    condition=lambda result: "complaint" in result.content.lower(),
    if_true=("handle_complaint", "support-agent", "Handle complaint: {input}"),
    if_false=("answer_question", "faq-bot", "Answer question: {input}"),
)

result = await pipeline.run(input="I want a refund for order #12345")
```

## Parallel Execution

Run multiple agents concurrently and collect all results:

```python
pipeline = ConditionalPipeline(client)

# Run three analysts in parallel
pipeline.add_parallel([
    ("market_analysis", "market-analyst", "Analyze market trends for {topic}"),
    ("tech_analysis", "tech-analyst", "Analyze technology landscape for {topic}"),
    ("competitor_analysis", "competitor-analyst", "Analyze competitors for {topic}"),
])

# Synthesize results
pipeline.add_step(
    "synthesis", "writer",
    "Combine these analyses into a report:\n"
    "Market: {market_analysis}\n"
    "Tech: {tech_analysis}\n"
    "Competitors: {competitor_analysis}",
)

result = await pipeline.run(topic="AI agents in 2026")
```

## Error Fallbacks

Automatically fall back to a different agent if the primary one fails:

```python
pipeline = ConditionalPipeline(client)

pipeline.add_fallback(
    "translate",
    agent_id="gpt4-translator",
    prompt_template="Translate to French: {text}",
    fallback_agent_id="basic-translator",
    fallback_prompt="Simple translation to French: {text}",
)

result = await pipeline.run(text="Hello, how are you?")
```

## Mixed Pipeline

Combine all patterns in a single pipeline:

```python
pipeline = ConditionalPipeline(client)

# Sequential: classify
pipeline.add_step("classify", "classifier", "Classify this query: {input}")

# Branch: route based on classification
pipeline.add_branch(
    "classify",
    condition=lambda r: "urgent" in r.content.lower(),
    if_true=("urgent_response", "senior-agent", "Handle urgent: {input}"),
    if_false=("normal_response", "junior-agent", "Handle: {input}"),
)

result = await pipeline.run(input="My server is down!")
```

## API Reference

- [`ConditionalPipeline`](../api/pipeline.md) — full class documentation
- [`Pipeline`](../api/pipeline.md) — linear pipeline (simpler alternative)

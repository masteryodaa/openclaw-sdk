---
hide:
  - navigation
  - toc
---

<!-- Hero Section -->
<div class="oc-hero" markdown>

<div class="oc-tagline">Wrap. Enhance. Ship.</div>

# OpenClaw SDK

<div class="oc-subtitle">
The official Python SDK for <strong>OpenClaw</strong> — the autonomous AI agent framework with 100k+ stars.
Build agents that control computers, browse the web, send messages, and learn new skills — all from Python.
</div>

<div class="oc-buttons">
<a href="getting-started/quickstart/" class="oc-btn oc-btn-primary">
:material-rocket-launch: Get Started
</a>
<a href="https://github.com/openclaw/openclaw-sdk" class="oc-btn oc-btn-secondary">
:fontawesome-brands-github: View on GitHub
</a>
</div>

</div>

<!-- Stats -->
<div class="oc-stats" markdown>
<div class="oc-stat">
<div class="oc-stat-value">5</div>
<div class="oc-stat-label">Lines to First Agent</div>
</div>
<div class="oc-stat">
<div class="oc-stat-value">80+</div>
<div class="oc-stat-label">Public Exports</div>
</div>
<div class="oc-stat">
<div class="oc-stat-value">98%</div>
<div class="oc-stat-label">Test Coverage</div>
</div>
<div class="oc-stat">
<div class="oc-stat-value">700+</div>
<div class="oc-stat-label">Unit Tests</div>
</div>
</div>

<!-- Code Showcase -->
<div class="oc-code-showcase" markdown>
<div class="oc-code-header">
<span class="oc-code-dot red"></span>
<span class="oc-code-dot yellow"></span>
<span class="oc-code-dot green"></span>
&nbsp; hello_openclaw.py
</div>

```python
import asyncio
from openclaw_sdk import OpenClawClient, AgentConfig

async def main():
    async with await OpenClawClient.connect() as client:
        agent = await client.create_agent(AgentConfig(
            agent_id="my-assistant",
            system_prompt="You are a helpful assistant with full OS access.",
        ))

        # The agent figures out HOW to do it — no tool code needed
        result = await agent.execute("Find today's top tech news and save as a report")
        print(result.content)

        for file in result.files:
            print(f"Generated: {file.name} ({file.size_bytes} bytes)")

asyncio.run(main())
```

</div>

---

<!-- Core Features -->
<div class="oc-section-header" markdown>

## Why OpenClaw SDK?

Most AI frameworks require you to pre-define every tool, chain, and integration in code.
OpenClaw is fundamentally different — **agents create their own tools dynamically**.

</div>

<div class="oc-features" markdown>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:material-robot:</span>

### Dynamic Tool Creation

Unlike LangChain, you don't define tools. The agent creates them on the fly — shell, browser, file system, web search, all built-in.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:material-pipe:</span>

### Pipelines & Coordination

Chain agents sequentially, run them in parallel, or set up supervisor-worker patterns. Conditional branching, error fallbacks, consensus voting.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:material-chat-processing:</span>

### 10+ Messaging Channels

Deploy agents to WhatsApp, Telegram, Discord, Slack, Signal, iMessage, Teams, Matrix — no integration code needed.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:material-shield-check:</span>

### Guardrails & Safety

PII detection, cost limits, content filtering, regex filters. Block dangerous outputs before they reach users.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:material-code-json:</span>

### Structured Output

Parse LLM responses into validated Pydantic models with automatic retry. Full type safety and IDE autocomplete.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:material-chart-line:</span>

### Cost Tracking & Observability

Monitor token usage and USD costs per agent, per model, per day. Hierarchical tracing with span export. All built-in, free.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:material-test-tube:</span>

### Evaluation Framework

Automated agent testing with ContainsEvaluator, ExactMatchEvaluator, RegexEvaluator, LengthEvaluator. Regression-test your prompts.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:material-puzzle:</span>

### Skills & ClawHub Marketplace

Browse, install, and manage skills from ClawHub. Agents can even discover and install skills themselves during execution.

</div>

</div>

---

<!-- Deployment Platforms -->
<div class="oc-section-header" markdown>

## Deploy Anywhere

OpenClaw runs anywhere Node.js runs. Each platform gives agents different superpowers.

</div>

<div class="oc-platforms" markdown>

<div class="oc-platform" markdown>
<div class="oc-platform-icon">:material-desktop-tower-monitor:</div>

#### Desktop

Full OS control — shell, files, browser automation, screenshots.

</div>

<div class="oc-platform" markdown>
<div class="oc-platform-icon">:material-cellphone:</div>

#### Android (Termux)

SMS, camera, GPS, notifications, contacts, flashlight, voice.

</div>

<div class="oc-platform" markdown>
<div class="oc-platform-icon">:material-docker:</div>

#### Docker

Sandboxed execution, no Node.js install, easy scaling.

</div>

<div class="oc-platform" markdown>
<div class="oc-platform-icon">:material-raspberry-pi:</div>

#### Raspberry Pi

GPIO pins, home automation, always-on IoT hub.

</div>

</div>

---

<!-- Use Cases -->
<div class="oc-section-header" markdown>

## Endless Possibilities

If you can describe it, an OpenClaw agent can probably do it.

</div>

<div class="oc-usecases" markdown>

<div class="oc-usecase" markdown>

#### :material-robot-happy: Personal AI Assistant

Desktop Jarvis with full OS control. Morning briefings, file management, code generation, task automation.

</div>

<div class="oc-usecase" markdown>

#### :material-store: Agent Builder Platform

Build a SaaS where users create and manage AI agents through a web UI. Competes with Dify — for free.

</div>

<div class="oc-usecase" markdown>

#### :material-headset: Customer Support

Multi-tier support: FAQ bot on cheap model handles 80% of queries, smart model handles complex issues. 12x cost reduction.

</div>

<div class="oc-usecase" markdown>

#### :material-server-network: DevOps Automation

Monitor servers, manage deployments, diagnose issues. Scheduled health checks every 15 minutes via Slack.

</div>

<div class="oc-usecase" markdown>

#### :material-file-document-edit: Research & Content

Automated research, writing, and review pipelines. Researcher agent finds data, writer creates content, editor polishes it.

</div>

<div class="oc-usecase" markdown>

#### :material-domain: Multi-Tenant SaaS

Isolated workspaces per company. Each tenant gets their own agents, quotas, and billing. Built-in tenant management.

</div>

</div>

---

<!-- Comparison -->
<div class="oc-section-header" markdown>

## How We Compare

OpenClaw SDK vs the competition — side by side.

</div>

<div class="oc-comparison" markdown>

| Feature | LangChain | CrewAI | Dify | AutoGen | **OpenClaw SDK** |
|---------|:---------:|:------:|:----:|:-------:|:----------------:|
| Agent creation | :material-check: | :material-check: | :material-check: | :material-check: | :material-check: |
| Dynamic tools | :material-close: | :material-close: | :material-close: | :material-close: | :material-check: |
| OS/Shell control | :material-close: | :material-close: | :material-close: | :material-close: | :material-check: |
| Browser automation | :material-close: | :material-close: | :material-close: | :material-close: | :material-check: |
| Self-improving | :material-close: | :material-close: | :material-close: | :material-close: | :material-check: |
| 10+ Channels | :material-close: | :material-close: | :material-close: | :material-close: | :material-check: |
| Skills marketplace | :material-close: | :material-close: | :material-check: | :material-close: | :material-check: |
| Pipelines | :material-check: | :material-check: | :material-check: | :material-check: | :material-check: |
| Structured output | :material-check: | :material-close: | :material-close: | :material-close: | :material-check: |
| Cost tracking (free) | :material-close: | :material-close: | :material-check: | :material-check: | :material-check: |
| Guardrails | :material-close: | :material-close: | :material-close: | :material-close: | :material-check: |
| Multi-tenancy | :material-close: | :material-close: | :material-close: | :material-close: | :material-check: |
| Scheduling | :material-close: | :material-close: | :material-close: | :material-close: | :material-check: |
| Free & open-source | :material-check: | Partial | Partial | :material-check: | :material-check: |

</div>

**TL;DR:** LangChain = LEGO bricks (you build everything). OpenClaw SDK = a pre-built robot (it figures things out).

---

<!-- Framework Integrations -->
<div class="oc-section-header" markdown>

## Works With Your Stack

Drop-in integrations for the frameworks you already use.

</div>

<div class="oc-features" markdown>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:simple-fastapi:</span>

### FastAPI

Three pre-built routers: agent execution, channel management, admin endpoints. Production-ready.

[:octicons-arrow-right-24: FastAPI guide](guides/fastapi.md)

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:simple-flask:</span>

### Flask

Blueprint-based integration with agent and channel endpoints. Familiar patterns.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:simple-django:</span>

### Django

URL patterns + views for agent execution. CSRF-exempt API endpoints.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:simple-streamlit:</span>

### Streamlit

One-line chat widget: `st_openclaw_chat(agent)`. Thinking display, token tracking.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:simple-jupyter:</span>

### Jupyter

IPython magic commands: `%openclaw ask "Find data"`. Interactive notebook exploration.

</div>

<div class="oc-feature-card" markdown>
<span class="oc-feature-icon">:simple-celery:</span>

### Celery

Queue long-running agent tasks with `execute_agent.delay("bot", "query")`. Background processing.

</div>

</div>

---

<!-- Install CTA -->
<div class="oc-install" markdown>

## Ready to Build?

```
pip install openclaw-sdk
```

<div style="margin-top: 1.5rem;" markdown>
<a href="getting-started/installation/" class="oc-btn oc-btn-primary">
:material-download: Installation Guide
</a>
<a href="getting-started/quickstart/" class="oc-btn oc-btn-secondary">
:material-book-open-variant: Quickstart Tutorial
</a>
</div>

</div>

---

<div style="text-align: center; padding: 2rem 0; color: var(--oc-text-muted);" markdown>

**OpenClaw SDK** is MIT-licensed and free forever.
You only pay for LLM API calls (Claude, GPT, Gemini) — or use free local models via Ollama.

Built with :material-heart: by the OpenClaw community

</div>

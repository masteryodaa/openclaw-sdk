---
hide:
  - navigation
  - toc
---

<!-- Hero -->
<div class="oc-hero" markdown>

<span class="oc-mascot">🐸</span>

<div class="oc-badge">v2.1 — Autonomous Agent SDK</div>

# The Last Framework <span class="oc-glow">You'll Ever Need</span>

<div class="oc-tagline">Wrap. Enhance. Ship.</div>

<div class="oc-sub">
Build AI agents that create their own tools, control computers, browse the web,
and talk across 10+ messaging channels — all from Python. 263 exports, 1621 tests, production-ready. No chains. No boilerplate. Just vibes.
</div>

<div class="oc-btns">
<a href="getting-started/quickstart/" class="oc-btn oc-btn-1">Get Started</a>
<a href="https://github.com/openclaw-sdk/openclaw-sdk" class="oc-btn oc-btn-2">GitHub</a>
<a href="api/client/" class="oc-btn oc-btn-3">API Docs &rarr;</a>
</div>

<div class="oc-pip">
<code><span class="oc-prompt">$ </span>pip install openclaw-sdk</code>
</div>

</div>

<!-- Terminal -->
<div class="oc-term" markdown>
<div class="oc-term-bar">
<span class="oc-dot r"></span>
<span class="oc-dot y"></span>
<span class="oc-dot g"></span>
<span class="oc-term-title">hello_openclaw.py</span>
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

        # No tools to define. No chains to build.
        # The agent figures out HOW to do it.
        result = await agent.execute(
            "Find today's top tech news and save as a report"
        )
        print(result.content)

        for file in result.files:
            print(f"Generated: {file.name} ({file.size_bytes} bytes)")

asyncio.run(main())
```

</div>

<!-- Capabilities -->
<div class="oc-sec oc-center" markdown>

<div class="oc-tag">Capabilities</div>

## Agents That Think, Act, and Evolve

<div class="oc-desc">
Most AI frameworks make you define every tool and chain.
OpenClaw agents create their own tools, learn new skills, and operate autonomously.
</div>

</div>

<div class="oc-grid" markdown>

<div class="oc-card" markdown>
<span class="oc-card-icon">🧠</span>

### Dynamic Tool Creation

Agents create tools on the fly — shell, browser, file system, web search, code execution. Describe the goal; they figure out how.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🔗</span>

### Pipelines & Coordination

Chain agents sequentially, run in parallel, supervisor-worker patterns. Conditional branching, error fallbacks, consensus voting.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">💬</span>

### 10+ Messaging Channels

Deploy to WhatsApp, Telegram, Discord, Slack, Signal, iMessage, Teams, Matrix — zero integration code.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🛡️</span>

### Guardrails & Safety

PII detection, cost limits, content filtering, regex filters, token limits. Block dangerous outputs before they reach users.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">📐</span>

### Structured Output

Parse LLM responses into validated Pydantic models with automatic retry. Full type safety and IDE autocomplete.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">📊</span>

### Cost Tracking & Tracing

Monitor token usage and USD costs per agent, per model, per day. Hierarchical tracing with span export. Built-in.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🧪</span>

### Evaluation Framework

Regression-test your prompts with Contains, ExactMatch, Regex, Length evaluators. Automated agent testing as a first-class feature.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🧩</span>

### Skills & ClawHub

Browse, install, and manage skills from ClawHub marketplace. Agents discover and install skills during execution.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🔌</span>

### Plugins & Alerting

Extend the SDK with plugins that hook into execution lifecycle. Monitor agents with alert rules, route to Slack, PagerDuty, or custom sinks.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🎙️</span>

### Voice Pipeline

Speech-to-text and text-to-speech with Whisper, Deepgram, ElevenLabs, and OpenAI TTS. Full audio-in / audio-out agent workflows.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🤖</span>

### Autonomous Agents

Goal-driven execution with multi-step planning, orchestration, budget limits, and a safety watchdog that can pause or kill runaway agents.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🔄</span>

### Workflows

Branching state machines with conditions, approvals, and parallel steps. Built-in presets for code review, research, and support triage.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🗄️</span>

### Data Sources

Unified async interface for SQLite, PostgreSQL, MySQL, and Supabase. Query databases from agents with type-safe results.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🔗</span>

### SaaS Connectors

Pre-built integrations for GitHub, Slack, Notion, Jira, Stripe, Gmail, Google Sheets, HubSpot, Salesforce, and Zendesk.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">📊</span>

### Dashboard

Full-featured FastAPI dashboard with REST endpoints for agents, sessions, webhooks, workflows, audit logs, billing, and more.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🛡️</span>

### Resilience

Retry with exponential backoff, circuit breakers, rate limiters, request deduplication, and semantic caching for robust gateway communication.

</div>

</div>

<!-- Deploy -->
<div class="oc-sec oc-center" markdown>

<div class="oc-tag">Deployment</div>

## Runs Everywhere

</div>

<div class="oc-deploy" markdown>

<div class="oc-dep" markdown>
<span class="oc-dep-icon">🖥️</span>

#### Desktop

<p>Shell, files, browser, screenshots</p>

</div>

<div class="oc-dep" markdown>
<span class="oc-dep-icon">📱</span>

#### Android

<p>SMS, camera, GPS, contacts, voice</p>

</div>

<div class="oc-dep" markdown>
<span class="oc-dep-icon">🐳</span>

#### Docker

<p>Sandboxed, scalable, no Node.js</p>

</div>

<div class="oc-dep" markdown>
<span class="oc-dep-icon">🔌</span>

#### IoT / Pi

<p>GPIO, home automation, always-on</p>

</div>

</div>

<!-- Use Cases -->
<div class="oc-sec oc-center" markdown>

<div class="oc-tag">What You Can Build</div>

## Endless Possibilities

<div class="oc-desc">
If you can describe it, an OpenClaw agent can do it.
</div>

</div>

<div class="oc-mosaic" markdown>

<div class="oc-tile" markdown>
<span class="oc-tile-tag">Autonomous Assistant</span>

#### Desktop Jarvis

Morning briefings, file management, code generation, task automation, web research, email triage — with full OS access. A personal AGI that lives on your machine.

</div>

<div class="oc-tile" markdown>
<span class="oc-tile-tag">SaaS Platform</span>

#### Agent Builder

Build a platform where users create and manage AI agents through a web UI. Multi-tenant isolation, quotas, billing — built in.

</div>

<div class="oc-tile" markdown>
<span class="oc-tile-tag">Support</span>

#### Customer Agents

Multi-tier: cheap model handles 80%, smart model handles the rest. 12x cost reduction.

</div>

<div class="oc-tile" markdown>
<span class="oc-tile-tag">Ops & Infrastructure</span>

#### DevOps Automation

Monitor servers, manage deployments, diagnose issues, auto-remediate. Scheduled health checks every 15 minutes via Slack, PagerDuty, or any channel.

</div>

<div class="oc-tile" markdown>
<span class="oc-tile-tag">Content Pipeline</span>

#### Research & Writing

Researcher finds data, writer creates content, editor polishes. Multi-agent pipeline with automatic handoffs.

</div>

<div class="oc-tile" markdown>
<span class="oc-tile-tag">Enterprise</span>

#### Multi-Tenant SaaS

Isolated workspaces per company. Each tenant gets their own agents, quotas, and audit logs. Full namespace isolation, per-tenant usage reporting, and configurable rate limits.

</div>

</div>

<!-- Comparison -->
<div class="oc-sec oc-center" markdown>

<div class="oc-tag">Why OpenClaw</div>

## Side-by-Side Comparison

</div>

<div class="oc-comparison">
<table class="oc-table">
<thead>
<tr>
<th>Feature</th>
<th>🦜 LangChain</th>
<th>🤝 CrewAI</th>
<th>🔮 Dify</th>
<th>🤖 AutoGen</th>
<th>🐸 <strong>OpenClaw</strong></th>
</tr>
</thead>
<tbody>
<tr><td>Agent creation</td><td>✅</td><td>✅</td><td>✅</td><td>✅</td><td>✅</td></tr>
<tr><td>Dynamic tools</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td></tr>
<tr><td>OS / Shell control</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td></tr>
<tr><td>Browser automation</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td></tr>
<tr><td>Self-improving</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td></tr>
<tr><td>10+ Channels</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td></tr>
<tr><td>Skills marketplace</td><td>❌</td><td>❌</td><td>✅</td><td>❌</td><td>✅</td></tr>
<tr><td>Pipelines</td><td>✅</td><td>✅</td><td>✅</td><td>✅</td><td>✅</td></tr>
<tr><td>Structured output</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td></tr>
<tr><td>Cost tracking</td><td>❌</td><td>❌</td><td>✅</td><td>✅</td><td>✅</td></tr>
<tr><td>Guardrails</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td></tr>
<tr><td>Multi-tenancy</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td></tr>
<tr><td>Free &amp; open-source</td><td>✅</td><td>⚠️</td><td>⚠️</td><td>✅</td><td>✅</td></tr>
</tbody>
</table>
</div>

<!-- Ecosystem -->
<div class="oc-sec oc-center" markdown>

<div class="oc-tag">Ecosystem</div>

## Beyond OpenClaw

<div class="oc-desc">
The *Claw ecosystem is growing. Future SDK versions will support these variants as drop-in gateway backends.
</div>

</div>

<div class="oc-eco" markdown>

<div class="oc-eco-item" markdown>
<span class="oc-eco-tag">Core</span>

#### OpenClaw

The original autonomous AI agent framework. Node.js, 50+ modules, 10+ channels.

<span class="oc-eco-badge now">Supported</span>

</div>

<div class="oc-eco-item" markdown>
<span class="oc-eco-tag">Lightweight</span>

#### NanoClaw

500-line container-based alternative. Security-focused, runs on Anthropic's Agents SDK.

<span class="oc-eco-badge soon">Coming Soon</span>

</div>

<div class="oc-eco-item" markdown>
<span class="oc-eco-tag">Lightweight</span>

#### Microclaw

Apple container optimized. WhatsApp integration, memory, scheduled jobs, filesystem isolation.

<span class="oc-eco-badge soon">Coming Soon</span>

</div>

<div class="oc-eco-item" markdown>
<span class="oc-eco-tag">Ultra-Light</span>

#### PicoClaw

Minimal footprint variant. Speed, simplicity, and portability as core principles.

<span class="oc-eco-badge soon">Coming Soon</span>

</div>

<div class="oc-eco-item" markdown>
<span class="oc-eco-tag">Enterprise</span>

#### IronClaw

Modular framework for teams. Structured autonomy, reusable components, production-grade workflows.

<span class="oc-eco-badge soon">Coming Soon</span>

</div>

<div class="oc-eco-item" markdown>
<span class="oc-eco-tag">Security</span>

#### TrustClaw

OAuth support, sandboxed execution, secure cloud actions. For security-first deployments.

<span class="oc-eco-badge soon">Coming Soon</span>

</div>

<div class="oc-eco-item" markdown>
<span class="oc-eco-tag">Performance</span>

#### ZeroClaw

Rust-based implementation. Built for raw speed and minimal resource usage.

<span class="oc-eco-badge soon">Coming Soon</span>

</div>

<div class="oc-eco-item" markdown>
<span class="oc-eco-tag">Cloud</span>

#### Cloud-Claw

Cloudflare container deployment. One-click deploy, edge computing, global distribution.

<span class="oc-eco-badge soon">Coming Soon</span>

</div>

</div>

<!-- Integrations -->
<div class="oc-sec oc-center" markdown>

<div class="oc-tag">Integrations</div>

## Drop Into Your Stack

</div>

<div class="oc-grid oc-grid-3" markdown>

<div class="oc-card" markdown>
<span class="oc-card-icon">⚡</span>

### FastAPI

Three pre-built routers: agent execution, channel management, admin endpoints.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🧪</span>

### Flask

Blueprint-based integration with agent and channel endpoints.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🎸</span>

### Django

URL patterns + views for agent execution. CSRF-exempt API endpoints.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🎨</span>

### Streamlit

One-line chat widget: `st_openclaw_chat(agent)`. Thinking display, token tracking.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">📓</span>

### Jupyter

Magic commands: `%openclaw ask "query"`. Interactive notebook exploration.

</div>

<div class="oc-card" markdown>
<span class="oc-card-icon">🥬</span>

### Celery

Queue long-running agent tasks with `execute_agent.delay()`. Background processing at scale.

</div>

</div>

<!-- CTA -->
<div class="oc-cta" markdown>

## Build Something Impossible

<div class="oc-cta-sub">
Five lines of Python. One autonomous agent. Infinite possibilities.
</div>

<div class="oc-btns">
<a href="getting-started/installation/" class="oc-btn oc-btn-1">Install SDK</a>
<a href="getting-started/quickstart/" class="oc-btn oc-btn-2">Quickstart</a>
</div>

</div>

<div class="oc-foot" markdown>

**OpenClaw SDK** is MIT-licensed and free forever.
You only pay for LLM API calls — or use free local models via Ollama.

</div>

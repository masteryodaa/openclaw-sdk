# OpenClaw SDK Documentation Website — Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Build a full documentation website using MkDocs Material with auto-generated API reference, deploy-ready to GitHub Pages.

**Architecture:** MkDocs Material + mkdocstrings[python] for auto-generated API docs. Markdown content organized into Getting Started, Guides, API Reference, and Examples sections. GitHub Pages deployment via `mkdocs gh-deploy`.

**Tech Stack:** MkDocs Material >= 9.5, mkdocstrings[python] >= 0.24, Python 3.11+

---

## Site Structure

```
OpenClaw SDK Docs
├── Home (index.md) — hero banner + feature grid
├── Getting Started
│   ├── Installation
│   ├── Quickstart
│   └── Configuration
├── Guides (15 topic guides)
│   ├── Agents & Execution
│   ├── Streaming
│   ├── Structured Output
│   ├── Pipelines
│   ├── Callbacks & Observability
│   ├── Tool Policy
│   ├── MCP Servers
│   ├── Skills & ClawHub
│   ├── Channels
│   ├── Scheduling
│   ├── Caching
│   ├── Cost Tracking
│   ├── Evaluation
│   ├── Prompt Templates
│   └── FastAPI Integration
├── API Reference (auto-generated from docstrings)
│   ├── Client
│   ├── Agent
│   ├── Types
│   ├── Config
│   ├── Gateway
│   ├── Managers
│   ├── Pipeline
│   ├── Callbacks
│   ├── Tools & MCP
│   └── Evaluation & Tracing
├── Examples (10 annotated scripts)
└── Changelog
```

## Key Decisions

1. Guides are tutorial-style with runnable code
2. API reference fully auto-generated via mkdocstrings
3. Material theme with dark mode, search, code copy
4. GitHub Pages deployment (free)
5. Existing quickstart.md and README content reused

## Dependencies

- `mkdocs-material>=9.5`
- `mkdocstrings[python]>=0.24`

## Hosting

GitHub Pages via `mkdocs gh-deploy` command.

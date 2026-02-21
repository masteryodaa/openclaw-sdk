from __future__ import annotations

from typing import Any

from openclaw_sdk.core.config import AgentConfig
from openclaw_sdk.tools.policy import ToolPolicy

TEMPLATES: dict[str, dict[str, Any]] = {
    "assistant": {
        "system_prompt": "You are a helpful AI assistant. Answer questions clearly and accurately.",
        "tool_policy": ToolPolicy.coding(),
    },
    "customer-support": {
        "system_prompt": (
            "You are a friendly customer support agent. Help users resolve issues "
            "with patience and professionalism. Escalate complex issues when needed."
        ),
        "tool_policy": ToolPolicy.minimal(),
        "channels": ["whatsapp", "telegram"],
    },
    "data-analyst": {
        "system_prompt": (
            "You are a data analyst. Analyze data, generate insights, and create "
            "visualizations. Write clean, documented code."
        ),
        "tool_policy": ToolPolicy.coding(),
    },
    "code-reviewer": {
        "system_prompt": (
            "You are a code reviewer. Review code for bugs, security issues, "
            "performance problems, and style. Provide actionable feedback."
        ),
        "tool_policy": ToolPolicy.coding(),
    },
    "researcher": {
        "system_prompt": (
            "You are a research analyst. Find accurate, current information from "
            "multiple sources. Cite sources and note confidence levels."
        ),
        "tool_policy": ToolPolicy.full(),
    },
    "writer": {
        "system_prompt": (
            "You are a content writer. Write clear, engaging, SEO-optimized content. "
            "Adapt tone and style to the audience."
        ),
        "tool_policy": ToolPolicy.minimal(),
    },
    "devops": {
        "system_prompt": (
            "You are a DevOps engineer. Monitor systems, manage deployments, "
            "diagnose issues, and automate operations. Always confirm before "
            "destructive actions."
        ),
        "tool_policy": ToolPolicy.full(),
        "permission_mode": "confirm",
    },
    "mobile-jarvis": {
        "system_prompt": (
            "You are Jarvis, a mobile AI assistant running on Android via Termux. "
            "You can send SMS, take photos, check location, manage notifications, "
            "and control phone hardware. Always ask before sending messages."
        ),
        "tool_policy": ToolPolicy.full(),
        "permission_mode": "confirm",
        "enable_memory": True,
    },
}


def get_template(name: str) -> AgentConfig:
    """Get a pre-built AgentConfig by template name.

    Args:
        name: Template name (e.g., "customer-support", "data-analyst").

    Returns:
        AgentConfig with the template settings applied.

    Raises:
        KeyError: If the template name is not found.
    """
    if name not in TEMPLATES:
        available = ", ".join(sorted(TEMPLATES))
        raise KeyError(f"Unknown template '{name}'. Available: {available}")

    config_data = dict(TEMPLATES[name])
    config_data.setdefault("agent_id", name)
    return AgentConfig(**config_data)


def list_templates() -> list[str]:
    """Return a sorted list of available template names."""
    return sorted(TEMPLATES)

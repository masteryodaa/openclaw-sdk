"""Templates controller — pre-built project templates."""

from __future__ import annotations

import logging

from app.helpers import database

log = logging.getLogger(__name__)

# ClawForge templates mapped to SDK agent template archetypes
TEMPLATES = [
    {
        "id": "landing-page",
        "name": "Landing Page",
        "description": "A modern, responsive landing page with hero section, features, and CTA",
        "category": "web",
        "difficulty": "easy",
        "tags": ["html", "css", "responsive"],
        "sdk_template": "writer",
    },
    {
        "id": "rest-api",
        "name": "REST API",
        "description": "A FastAPI REST API with CRUD endpoints, validation, and error handling",
        "category": "backend",
        "difficulty": "medium",
        "tags": ["python", "fastapi", "api"],
        "sdk_template": "assistant",
    },
    {
        "id": "data-dashboard",
        "name": "Data Dashboard",
        "description": "Interactive data visualization dashboard with charts and filters",
        "category": "data",
        "difficulty": "medium",
        "tags": ["python", "data", "visualization"],
        "sdk_template": "data-analyst",
    },
    {
        "id": "cli-tool",
        "name": "CLI Tool",
        "description": "Command-line application with argument parsing, colors, and help text",
        "category": "tools",
        "difficulty": "easy",
        "tags": ["python", "cli", "automation"],
        "sdk_template": "devops",
    },
    {
        "id": "chatbot",
        "name": "Chatbot",
        "description": "AI-powered chatbot with conversation history and custom personality",
        "category": "ai",
        "difficulty": "medium",
        "tags": ["ai", "chat", "nlp"],
        "sdk_template": "customer-support",
    },
    {
        "id": "full-stack-app",
        "name": "Full-Stack App",
        "description": "Complete web application with frontend, backend, and database",
        "category": "web",
        "difficulty": "hard",
        "tags": ["fullstack", "react", "fastapi", "sqlite"],
        "sdk_template": "researcher",
    },
]


def list_templates() -> list[dict]:
    """Return all available templates."""
    log.debug("Listing %d templates", len(TEMPLATES))
    return TEMPLATES


def get_template(template_id: str) -> dict | None:
    """Get a template by ID."""
    for t in TEMPLATES:
        if t["id"] == template_id:
            log.debug("Found template %s", template_id)
            return t
    log.warning("Template %r not found", template_id)
    return None


async def create_from_template(template_id: str, name: str = "") -> dict | None:
    """Create a project pre-filled from a template."""
    log.info("Creating project from template=%s name=%r", template_id, name)
    template = get_template(template_id)
    if not template:
        return None
    project_name = name or f"{template['name']} Project"
    result = await database.create_project(
        project_name,
        template["description"],
        template=template_id,
    )
    log.info("Project created from template: id=%s", result["id"][:8])
    return result

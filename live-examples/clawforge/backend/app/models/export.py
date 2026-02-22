"""Export-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


class ExportGitHubRequest(BaseModel):
    project_id: str
    repo_name: str
    github_token: str
    description: str = ""

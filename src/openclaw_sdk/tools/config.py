from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from openclaw_sdk.core.constants import ToolType


class ToolConfig(BaseModel):
    tool_type: ToolType
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class DatabaseToolConfig(ToolConfig):
    tool_type: ToolType = ToolType.DATABASE
    connection_string: str
    allowed_tables: list[str] = Field(default_factory=list)
    read_only: bool = True


class FileToolConfig(ToolConfig):
    tool_type: ToolType = ToolType.FILES
    output_dir: str = "/outputs"
    allowed_formats: list[str] = Field(
        default_factory=lambda: ["csv", "json", "xlsx", "txt", "md"]
    )
    max_file_size_mb: int = 100


class BrowserToolConfig(ToolConfig):
    tool_type: ToolType = ToolType.BROWSER
    headless: bool = True
    allowed_domains: list[str] = Field(default_factory=list)  # Empty = all domains
    timeout_seconds: int = 30


class ShellToolConfig(ToolConfig):
    tool_type: ToolType = ToolType.SHELL
    # None = all commands allowed; [] = no commands allowed (use [] for untrusted agents)
    allowed_commands: list[str] | None = None
    working_directory: str | None = None


class WebSearchToolConfig(ToolConfig):
    tool_type: ToolType = ToolType.WEB_SEARCH
    search_engine: Literal["google", "bing", "duckduckgo"] = "google"
    max_results: int = 10

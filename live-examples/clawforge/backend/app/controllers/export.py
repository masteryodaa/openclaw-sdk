"""Export controller — export project to GitHub."""

from __future__ import annotations

import logging

from app.helpers import database

log = logging.getLogger(__name__)


async def export_to_github(
    project_id: str,
    repo_name: str,
    github_token: str,
    description: str = "",
) -> dict:
    """Export project files to a GitHub repository.

    Uses the SDK's GitHubConnector if available, otherwise returns
    the files for manual export.
    """
    log.info("Exporting project %s to GitHub repo=%s", project_id[:8], repo_name)

    project = await database.get_project(project_id)
    if not project:
        log.error("Project %s not found for export", project_id[:8])
        raise ValueError("Project not found")

    files = await database.get_files(project_id)
    if not files:
        log.error("No files to export for project %s", project_id[:8])
        raise ValueError("No files to export")

    log.info("Exporting %d files to %s", len(files), repo_name)

    # Try using SDK's GitHubConnector
    try:
        from openclaw_sdk.integrations.connectors import GitHubConnector, ConnectorConfig

        config = ConnectorConfig(api_key=github_token)
        connector = GitHubConnector(config)

        # Create repo and upload files
        log.info("Creating GitHub repo %s via GitHubConnector", repo_name)
        result = await connector.execute({
            "action": "create_repo",
            "name": repo_name,
            "description": description or project["description"],
        })

        for f in files:
            log.debug("Uploading file %s", f["path"])
            await connector.execute({
                "action": "create_file",
                "repo": repo_name,
                "path": f["path"],
                "content": f["content"],
                "message": f"Add {f['name']}",
            })

        log.info("Export complete: %d files to %s", len(files), repo_name)
        return {
            "success": True,
            "repo_name": repo_name,
            "files_exported": len(files),
            "url": result.get("url", f"https://github.com/{repo_name}"),
        }
    except ImportError:
        log.warning("GitHubConnector not available — returning files for manual export")
        # GitHubConnector not available — return files for manual export
        return {
            "success": False,
            "message": "GitHubConnector not available. Files ready for manual export.",
            "repo_name": repo_name,
            "files": [{"name": f["name"], "path": f["path"], "size": f["size_bytes"]} for f in files],
        }
    except Exception as exc:
        log.error("GitHub export failed: %s", exc, exc_info=True)
        return {
            "success": False,
            "message": str(exc),
            "repo_name": repo_name,
        }

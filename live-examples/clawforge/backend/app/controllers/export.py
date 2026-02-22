"""Export controller — export project to GitHub."""

from __future__ import annotations

from app.helpers import database


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
    project = await database.get_project(project_id)
    if not project:
        raise ValueError("Project not found")

    files = await database.get_files(project_id)
    if not files:
        raise ValueError("No files to export")

    # Try using SDK's GitHubConnector
    try:
        from openclaw_sdk.integrations.connectors import GitHubConnector, ConnectorConfig

        config = ConnectorConfig(api_key=github_token)
        connector = GitHubConnector(config)

        # Create repo and upload files
        result = await connector.execute({
            "action": "create_repo",
            "name": repo_name,
            "description": description or project["description"],
        })

        for f in files:
            await connector.execute({
                "action": "create_file",
                "repo": repo_name,
                "path": f["path"],
                "content": f["content"],
                "message": f"Add {f['name']}",
            })

        return {
            "success": True,
            "repo_name": repo_name,
            "files_exported": len(files),
            "url": result.get("url", f"https://github.com/{repo_name}"),
        }
    except ImportError:
        # GitHubConnector not available — return files for manual export
        return {
            "success": False,
            "message": "GitHubConnector not available. Files ready for manual export.",
            "repo_name": repo_name,
            "files": [{"name": f["name"], "path": f["path"], "size": f["size_bytes"]} for f in files],
        }
    except Exception as exc:
        return {
            "success": False,
            "message": str(exc),
            "repo_name": repo_name,
        }

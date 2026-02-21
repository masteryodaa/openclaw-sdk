"""MCP server for searching and browsing OpenClaw SDK documentation.

Run with::

    python -m openclaw_sdk.mcp.docs_server

Configure in Claude Code::

    claude mcp add openclaw-docs -- python -m openclaw_sdk.mcp.docs_server

Configure in Claude Desktop (claude_desktop_config.json)::

    {
      "mcpServers": {
        "openclaw-docs": {
          "command": "python",
          "args": ["-m", "openclaw_sdk.mcp.docs_server"]
        }
      }
    }
"""

from __future__ import annotations

import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "OpenClaw SDK Docs",
    instructions=(
        "Search and browse the OpenClaw SDK documentation. "
        "Use search_docs to find relevant pages, then read_doc to get full content."
    ),
)

# Resolve docs directory — walk up from this file to find the project root
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent.parent  # src/openclaw_sdk/mcp -> project root
_DOCS_DIR = _PROJECT_ROOT / "docs"


def _find_docs_dir() -> Path:
    """Find the docs directory, trying multiple strategies."""
    if _DOCS_DIR.is_dir():
        return _DOCS_DIR
    # Fallback: check current working directory
    cwd_docs = Path.cwd() / "docs"
    if cwd_docs.is_dir():
        return cwd_docs
    raise FileNotFoundError(
        "Cannot find docs/ directory. Run this server from the openclaw-sdk project root."
    )


def _load_all_docs() -> dict[str, str]:
    """Load all markdown files from the docs directory into memory."""
    docs_dir = _find_docs_dir()
    pages: dict[str, str] = {}
    for md_file in sorted(docs_dir.rglob("*.md")):
        rel_path = md_file.relative_to(docs_dir).as_posix()
        pages[rel_path] = md_file.read_text(encoding="utf-8", errors="replace")
    return pages


# Cache docs in memory at startup
_DOCS_CACHE: dict[str, str] | None = None


def _get_docs() -> dict[str, str]:
    global _DOCS_CACHE
    if _DOCS_CACHE is None:
        _DOCS_CACHE = _load_all_docs()
    return _DOCS_CACHE


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("docs://pages")
def list_pages() -> str:
    """List all documentation pages with their paths."""
    docs = _get_docs()
    lines = [f"# OpenClaw SDK Documentation Pages ({len(docs)} files)\n"]
    for path in sorted(docs.keys()):
        # Extract first heading as title
        content = docs[path]
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path
        lines.append(f"- `{path}` — {title}")
    return "\n".join(lines)


@mcp.resource("docs://page/{path}")
def read_page(path: str) -> str:
    """Read a specific documentation page by its path."""
    docs = _get_docs()
    # Try exact match first
    if path in docs:
        return docs[path]
    # Try with .md extension
    if not path.endswith(".md"):
        path_md = path + ".md"
        if path_md in docs:
            return docs[path_md]
    # Try fuzzy match
    for doc_path in docs:
        if path in doc_path:
            return docs[doc_path]
    available = ", ".join(sorted(docs.keys())[:10])
    return f"Page not found: {path}\n\nAvailable pages (first 10): {available}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_docs(query: str, max_results: int = 5) -> str:
    """Search the OpenClaw SDK documentation for relevant content.

    Args:
        query: Search query — keywords, function names, or concepts.
        max_results: Maximum number of results to return (default 5).

    Returns:
        Matching documentation excerpts with page paths and context.
    """
    docs = _get_docs()
    query_lower = query.lower()
    query_words = query_lower.split()

    scored: list[tuple[float, str, str]] = []

    for path, content in docs.items():
        content_lower = content.lower()
        # Score: count keyword matches
        score = 0.0
        for word in query_words:
            count = content_lower.count(word)
            if count > 0:
                score += count
                # Boost for matches in headings
                for line in content.split("\n"):
                    if line.startswith("#") and word in line.lower():
                        score += 5.0
                # Boost for matches in code blocks
                if f"`{word}`" in content_lower:
                    score += 3.0

        if score > 0:
            # Extract relevant snippet
            snippet = _extract_snippet(content, query_words)
            scored.append((score, path, snippet))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max_results]

    if not top:
        return f"No results found for: {query}"

    results = [f"# Search Results for: {query}\n"]
    for i, (score, path, snippet) in enumerate(top, 1):
        results.append(f"## {i}. `{path}`\n")
        results.append(snippet)
        results.append("")

    return "\n".join(results)


@mcp.tool()
def read_doc(path: str) -> str:
    """Read the full content of a documentation page.

    Args:
        path: Path to the doc page (e.g., 'guides/agents.md', 'api/client.md').

    Returns:
        Full markdown content of the page.
    """
    docs = _get_docs()
    if path in docs:
        return docs[path]
    if not path.endswith(".md"):
        path_md = path + ".md"
        if path_md in docs:
            return docs[path_md]
    # Fuzzy match
    matches = [p for p in docs if path in p]
    if matches:
        best = matches[0]
        return f"(Matched: {best})\n\n{docs[best]}"
    return f"Page not found: {path}"


@mcp.tool()
def list_doc_pages() -> str:
    """List all available documentation pages with titles.

    Returns:
        A formatted list of all doc pages and their titles.
    """
    docs = _get_docs()
    lines = [f"OpenClaw SDK Documentation — {len(docs)} pages\n"]
    by_section: dict[str, list[str]] = {}
    for path in sorted(docs.keys()):
        section = path.split("/")[0] if "/" in path else "root"
        content = docs[path]
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path
        by_section.setdefault(section, []).append(f"  - `{path}` — {title}")

    for section, pages in sorted(by_section.items()):
        lines.append(f"\n### {section}/")
        lines.extend(pages)
    return "\n".join(lines)


@mcp.tool()
def reload_docs() -> str:
    """Reload documentation from disk (use after docs are updated).

    Returns:
        Confirmation with the number of pages loaded.
    """
    global _DOCS_CACHE
    _DOCS_CACHE = None
    docs = _get_docs()
    return f"Reloaded {len(docs)} documentation pages."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_snippet(content: str, words: list[str], context_lines: int = 3) -> str:
    """Extract a relevant snippet around the first keyword match."""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(w in line_lower for w in words):
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            snippet_lines = lines[start:end]
            return "\n".join(snippet_lines)
    # Fallback: first 10 lines
    return "\n".join(lines[:10])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")

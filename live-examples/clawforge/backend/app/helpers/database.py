"""Async SQLite database helpers for ClawForge."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent.parent / "clawforge.db"


async def _get_db() -> aiosqlite.Connection:
    """Open a connection with row_factory enabled."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    """Create tables if they do not exist."""
    db = await _get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'created',
                template TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                total_cost_usd REAL DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                plan_json TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                thinking TEXT,
                tool_calls TEXT,
                files TEXT,
                token_usage TEXT,
                cost_usd REAL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS generated_files (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                content TEXT,
                size_bytes INTEGER DEFAULT 0,
                mime_type TEXT DEFAULT 'text/plain',
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        await db.commit()
    finally:
        await db.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: aiosqlite.Row) -> dict:
    """Convert a Row to a plain dict."""
    return dict(row)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

async def create_project(
    name: str,
    description: str,
    template: str | None = None,
) -> dict:
    """Create a new project and return it."""
    project_id = uuid.uuid4().hex
    now = _now()
    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO projects (id, name, description, template, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, name, description, template, now, now),
        )
        await db.commit()
    finally:
        await db.close()
    return {
        "id": project_id,
        "name": name,
        "description": description,
        "status": "created",
        "template": template,
        "created_at": now,
        "updated_at": now,
        "total_cost_usd": 0,
        "total_tokens": 0,
        "plan_json": None,
    }


async def get_project(project_id: str) -> dict | None:
    """Get a single project by ID."""
    db = await _get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["plan_json"] = json.loads(d["plan_json"]) if d["plan_json"] else None
        return d
    finally:
        await db.close()


async def list_projects() -> list[dict]:
    """List all projects, newest first."""
    db = await _get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = _row_to_dict(row)
            d["plan_json"] = json.loads(d["plan_json"]) if d["plan_json"] else None
            results.append(d)
        return results
    finally:
        await db.close()


async def update_project(project_id: str, **fields: object) -> dict | None:
    """Update project fields. Returns updated project or None if not found."""
    if not fields:
        return await get_project(project_id)
    fields["updated_at"] = _now()

    # Serialize plan_json if provided as dict
    if "plan_json" in fields and isinstance(fields["plan_json"], dict):
        fields["plan_json"] = json.dumps(fields["plan_json"])

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values())
    values.append(project_id)

    db = await _get_db()
    try:
        cursor = await db.execute(
            f"UPDATE projects SET {set_clause} WHERE id = ?",
            values,
        )
        await db.commit()
        if cursor.rowcount == 0:
            return None
    finally:
        await db.close()
    return await get_project(project_id)


async def delete_project(project_id: str) -> bool:
    """Delete project and cascade to messages + files."""
    db = await _get_db()
    try:
        await db.execute("DELETE FROM messages WHERE project_id = ?", (project_id,))
        await db.execute("DELETE FROM generated_files WHERE project_id = ?", (project_id,))
        cursor = await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

async def add_message(
    project_id: str,
    role: str,
    content: str,
    thinking: str | None = None,
    tool_calls: list[dict] | None = None,
    files: list[dict] | None = None,
    token_usage: dict | None = None,
    cost_usd: float = 0,
) -> dict:
    """Add a message to a project."""
    msg_id = uuid.uuid4().hex
    now = _now()
    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO messages
               (id, project_id, role, content, thinking, tool_calls, files, token_usage, cost_usd, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                msg_id,
                project_id,
                role,
                content,
                thinking,
                json.dumps(tool_calls) if tool_calls else None,
                json.dumps(files) if files else None,
                json.dumps(token_usage) if token_usage else None,
                cost_usd,
                now,
            ),
        )
        await db.commit()
    finally:
        await db.close()
    return {
        "id": msg_id,
        "project_id": project_id,
        "role": role,
        "content": content,
        "thinking": thinking,
        "tool_calls": tool_calls,
        "files": files,
        "token_usage": token_usage,
        "cost_usd": cost_usd,
        "created_at": now,
    }


async def get_messages(project_id: str) -> list[dict]:
    """Get all messages for a project, oldest first."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM messages WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = _row_to_dict(row)
            d["tool_calls"] = json.loads(d["tool_calls"]) if d["tool_calls"] else None
            d["files"] = json.loads(d["files"]) if d["files"] else None
            d["token_usage"] = json.loads(d["token_usage"]) if d["token_usage"] else None
            results.append(d)
        return results
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Generated Files
# ---------------------------------------------------------------------------

async def add_file(
    project_id: str,
    name: str,
    path: str,
    content: str,
    size_bytes: int = 0,
    mime_type: str = "text/plain",
) -> dict:
    """Add a generated file record."""
    file_id = uuid.uuid4().hex
    now = _now()
    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO generated_files
               (id, project_id, name, path, content, size_bytes, mime_type, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (file_id, project_id, name, path, content, size_bytes, mime_type, now),
        )
        await db.commit()
    finally:
        await db.close()
    return {
        "id": file_id,
        "project_id": project_id,
        "name": name,
        "path": path,
        "content": content,
        "size_bytes": size_bytes,
        "mime_type": mime_type,
        "created_at": now,
    }


async def get_files(project_id: str) -> list[dict]:
    """Get all generated files for a project."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM generated_files WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        await db.close()

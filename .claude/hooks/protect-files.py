#!/usr/bin/env python3
"""PreToolUse hook: block edits to protected files."""

import json
import sys

PROTECTED_PATTERNS = [
    ".claude/context/protocol-notes.md",
    "poetry.lock",
    ".env",
    ".git/",
    "device.json",
    "device-auth.json",
]


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    normalized = file_path.replace("\\", "/")
    for pattern in PROTECTED_PATTERNS:
        if pattern in normalized:
            print(f"BLOCKED: {file_path} matches protected pattern '{pattern}'", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()

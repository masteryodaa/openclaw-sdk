#!/usr/bin/env python3
"""PostToolUse hook: auto-format Python files with ruff after edits."""
import json
import subprocess
import sys

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        sys.exit(0)

    # Run ruff check --fix (auto-fixable issues) then ruff format
    subprocess.run(
        ["python", "-m", "ruff", "check", "--fix", "--quiet", file_path],
        capture_output=True,
        timeout=15,
    )
    subprocess.run(
        ["python", "-m", "ruff", "format", "--quiet", file_path],
        capture_output=True,
        timeout=15,
    )

    sys.exit(0)

if __name__ == "__main__":
    main()

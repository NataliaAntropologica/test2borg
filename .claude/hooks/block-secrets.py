#!/usr/bin/env python3
"""
PreToolUse hook — credential protection and dangerous command guard.
Delegates all sensitive-path and pattern matching to shared.py.
Exit code 2 = block. Exit code 0 = allow.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))

from shared import is_dangerous_command, is_sensitive_path

try:
    hook_input = json.load(sys.stdin)
except (json.JSONDecodeError, EOFError):
    sys.exit(0)

tool_name = hook_input.get("tool_name", "")
tool_input = hook_input.get("tool_input", {})


def block(reason: str):
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


# ---------------------------------------------------------------------------
# Block READ/WRITE access to sensitive credential files
# ---------------------------------------------------------------------------

FILE_TOOLS = {"Read", "Grep", "Glob", "Edit", "Write", "MultiEdit"}

if tool_name in FILE_TOOLS:
    path = tool_input.get("file_path", tool_input.get("path", tool_input.get("pattern", "")))
    if path and is_sensitive_path(str(path)):
        block(
            f"Access to sensitive file blocked: {path}. "
            "Credentials live in .env only — never accessed by Claude."
        )


# ---------------------------------------------------------------------------
# Block dangerous bash commands (patterns defined in shared.py)
# ---------------------------------------------------------------------------

if tool_name == "Bash":
    cmd = tool_input.get("command", "")
    if cmd:
        dangerous, pattern = is_dangerous_command(cmd)
        if dangerous:
            block(
                f"Bash blocked by security guardrail (matched: {pattern!r}). "
                "Run manually in the terminal if this is intentional."
            )


sys.exit(0)

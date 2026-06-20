#!/usr/bin/env python3
"""
PreToolUse hook — blocks the reflection agent from editing SOUL.md directly.
If the reflection wants to change agent identity or rules, it must write
suggestions to the daily log instead. Prevents "soul drift".

Only enforced when CLAUDE_INVOKED_BY == "memory_reflect".
All other callers (including Natalia directly) can edit SOUL.md normally.
"""

import json
import os
import sys

try:
    hook_input = json.load(sys.stdin)
except (json.JSONDecodeError, EOFError):
    sys.exit(0)

# Only enforce during automated reflection runs
if os.environ.get("CLAUDE_INVOKED_BY") != "memory_reflect":
    sys.exit(0)

tool_name = hook_input.get("tool_name", "")
tool_input = hook_input.get("tool_input", {})

WRITE_TOOLS = {"Edit", "Write", "MultiEdit"}

if tool_name in WRITE_TOOLS:
    path = tool_input.get("file_path", tool_input.get("path", ""))
    if path and "SOUL.md" in str(path):
        print(json.dumps({
            "decision": "block",
            "reason": (
                "SOUL.md write blocked during automated reflection. "
                "Write your suggestion to today's daily log instead: "
                "'SOUL.md suggestion: [your suggestion]'. "
                "Natalia will review and apply it manually."
            )
        }))
        sys.exit(2)

sys.exit(0)

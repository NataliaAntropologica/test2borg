#!/usr/bin/env python3
"""
SessionStart hook — inject Sintetica memory into every Claude Code session.
Reads SOUL.md, USER.md, MEMORY.md, recent daily logs, and BOOTSTRAP.md (if present).
Outputs a system context block for Claude Code to inject.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Recursion prevention: skip if we're inside an Agent SDK session
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

REPO_ROOT = Path(__file__).parent.parent.parent
VAULT = REPO_ROOT / "Sintetica" / "Memory"
DAILY = VAULT / "daily"


def read_file_safe(path: Path, label: str) -> str:
    try:
        content = path.read_text(encoding="utf-8").strip()
        return f"## {label}\n\n{content}" if content else ""
    except FileNotFoundError:
        return ""


def get_recent_daily_logs(n: int = 3) -> str:
    if not DAILY.exists():
        return ""
    logs = sorted(DAILY.glob("*.md"), reverse=True)[:n]
    if not logs:
        return ""
    sections = []
    for log in logs:
        content = log.read_text(encoding="utf-8").strip()
        if content:
            sections.append(f"### {log.stem}\n{content}")
    if not sections:
        return ""
    return "## Recent Daily Logs\n\n" + "\n\n".join(sections)


def build_context() -> str:
    parts = []

    # First-run onboarding takes priority
    bootstrap = VAULT / "BOOTSTRAP.md"
    if bootstrap.exists():
        parts.append(
            "## BOOTSTRAP — FIRST RUN ONBOARDING\n\n"
            + bootstrap.read_text(encoding="utf-8").strip()
            + "\n\n> Ask the first unanswered question now, one at a time."
        )

    parts.append(read_file_safe(VAULT / "SOUL.md", "SOUL — Agent Identity & Rules"))
    parts.append(read_file_safe(VAULT / "USER.md", "USER — Natalia's Profile & Config"))
    parts.append(read_file_safe(VAULT / "MEMORY.md", "MEMORY — Key Facts & Active Projects"))
    parts.append(get_recent_daily_logs(3))

    return "\n\n---\n\n".join(p for p in parts if p)


context = build_context()

if context:
    output = {
        "type": "system",
        "content": f"# Sintetica Strategic Brain — Session Context\n\n{context}"
    }
    print(json.dumps(output))

sys.exit(0)

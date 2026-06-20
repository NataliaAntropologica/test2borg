"""
Integration registry — tracks which integrations are configured and enabled.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent


def _env(key: str) -> bool:
    return bool(os.environ.get(key, "").strip())


def _file_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).exists()


INTEGRATIONS = {
    "gmail": {
        "description": "Gmail — read emails, detect replies, generate drafts",
        "is_configured": lambda: _file_exists(".claude/gmail_token.json"),
        "auth_hint": (
            "1. Download credentials.json from Google Cloud Console\n"
            "2. Place it at .claude/credentials.json\n"
            "3. Run: python .claude/scripts/integrations/gmail.py --auth"
        ),
    },
    "github": {
        "description": "GitHub — list PRs, issues, code review sweeps",
        "is_configured": lambda: _env("GITHUB_TOKEN"),
        "auth_hint": "Add GITHUB_TOKEN=ghp_... to .env",
    },
    "slack": {
        "description": "Slack — read messages (read-only, no sending)",
        "is_configured": lambda: _env("SLACK_BOT_TOKEN") and _env("SLACK_APP_TOKEN"),
        "auth_hint": (
            "Add SLACK_BOT_TOKEN=xoxb-... and SLACK_APP_TOKEN=xapp-... to .env\n"
            "See api.slack.com/apps for token setup"
        ),
    },
    "obsidian": {
        "description": "Obsidian — read/search local vault files (no API needed)",
        "is_configured": lambda: True,
    },
}


def status() -> dict[str, dict]:
    result = {}
    for name, meta in INTEGRATIONS.items():
        configured = meta["is_configured"]()
        result[name] = {
            "description": meta["description"],
            "configured": configured,
            "auth_hint": meta.get("auth_hint", "") if not configured else "",
        }
    return result


def print_status():
    for name, info in status().items():
        icon = "+" if info["configured"] else "-"
        print(f"  [{icon}] {name:12} {info['description']}")
        if info["auth_hint"]:
            for line in info["auth_hint"].splitlines():
                print(f"              {line}")

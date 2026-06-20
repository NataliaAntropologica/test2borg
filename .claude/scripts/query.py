#!/usr/bin/env python3
"""
Unified integration CLI for the Sintetica Strategic Brain.
Loads .env automatically. All credentials stay in Python — never passed to Claude.

Usage:
  python .claude/scripts/query.py status               # integration status
  python .claude/scripts/query.py gmail list            # unread emails
  python .claude/scripts/query.py gmail thread <id>     # email thread
  python .claude/scripts/query.py github prs <owner/repo> [<owner/repo> ...]
  python .claude/scripts/query.py github issues         # assigned issues
  python .claude/scripts/query.py github rate           # API rate limit
  python .claude/scripts/query.py slack unread          # messages since last 30min
  python .claude/scripts/query.py slack dms             # direct messages
  python .claude/scripts/query.py slack summary         # grouped digest
  python .claude/scripts/query.py obsidian domains      # list memory domains
  python .claude/scripts/query.py obsidian list <domain>
  python .claude/scripts/query.py obsidian read <path>
  python .claude/scripts/query.py obsidian search <query>
  python .claude/scripts/query.py obsidian logs         # recent daily logs
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
INTEGRATIONS = REPO_ROOT / ".claude" / "scripts" / "integrations"
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))
sys.path.insert(0, str(INTEGRATIONS))


def load_env():
    """Load .env file into environment if it exists."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def cmd_status(_args):
    from integrations.registry import print_status
    print("Integration status:")
    print_status()


def cmd_gmail(args):
    from integrations.gmail import get_service, list_unread, get_thread, format_for_context
    svc = get_service()
    sub = args[0] if args else "list"

    if sub == "list":
        max_r = int(args[1]) if len(args) > 1 else 20
        emails = list_unread(svc, max_results=max_r)
        print(format_for_context(emails))
    elif sub == "thread" and len(args) > 1:
        import json
        msgs = get_thread(svc, args[1])
        print(json.dumps(msgs, indent=2, ensure_ascii=False))
    else:
        print("Usage: query.py gmail [list [max]] [thread <id>]")


def cmd_github(args):
    from integrations.github_integration import (
        get_client, list_open_prs, list_assigned_issues,
        get_rate_limit, format_prs_for_context, format_issues_for_context,
    )
    g = get_client()
    sub = args[0] if args else "prs"

    if sub == "prs":
        repos = args[1:] if len(args) > 1 else []
        if not repos:
            print("Usage: query.py github prs <owner/repo> [<owner/repo> ...]")
            return
        prs = list_open_prs(g, repos)
        print(format_prs_for_context(prs))
    elif sub == "issues":
        issues = list_assigned_issues(g)
        print(format_issues_for_context(issues))
    elif sub == "rate":
        print(get_rate_limit(g))
    else:
        print("Usage: query.py github [prs <repos>] [issues] [rate]")


def cmd_slack(args):
    from integrations.slack import (
        get_client, get_unread_messages, get_dms, list_channels,
        resolve_usernames, format_for_context, summarize_by_channel,
    )
    client = get_client()
    sub = args[0] if args else "unread"
    since = None
    if "--since" in args:
        idx = args.index("--since")
        since = args[idx + 1] if idx + 1 < len(args) else None

    if sub == "unread":
        channels = list_channels(client)
        all_ids = [c["id"] for c in channels]
        msgs = get_unread_messages(client, all_ids, since_ts=since)
        msgs = resolve_usernames(client, msgs)
        print(format_for_context(msgs))
    elif sub == "dms":
        msgs = get_dms(client, since_ts=since)
        msgs = resolve_usernames(client, msgs)
        print(format_for_context(msgs))
    elif sub == "summary":
        channels = list_channels(client)
        all_ids = [c["id"] for c in channels]
        msgs = get_unread_messages(client, all_ids, since_ts=since)
        msgs = resolve_usernames(client, msgs)
        print(summarize_by_channel(msgs))
    else:
        print("Usage: query.py slack [unread|dms|summary] [--since <ts>]")


def cmd_obsidian(args):
    from integrations.obsidian_integration import (
        list_domains, list_notes, read_note,
        keyword_search, recent_daily_logs,
    )
    sub = args[0] if args else "logs"

    if sub == "domains":
        for d in list_domains():
            notes = list_notes(d)
            print(f"  {d:20} ({len(notes)} notes)")
    elif sub == "list":
        domain = args[1] if len(args) > 1 else None
        notes = list_notes(domain)
        for n in notes:
            print(f"  {n.relative_path}: {n.title}")
    elif sub == "read":
        path = args[1] if len(args) > 1 else None
        if not path:
            print("Usage: query.py obsidian read <relative-path>")
            return
        content = read_note(path)
        print(content if content else f"Not found: {path}")
    elif sub == "search":
        query = " ".join(args[1:]) if len(args) > 1 else ""
        if not query:
            print("Usage: query.py obsidian search <query>")
            return
        results = keyword_search(query)
        if not results:
            print(f"No results for '{query}'")
        for r in results[:10]:
            print(r.to_context())
            print()
    elif sub == "logs":
        n = int(args[1]) if len(args) > 1 else 3
        for date, content in recent_daily_logs(n):
            print(f"\n=== {date} ===")
            print(content[:600])
    else:
        print("Usage: query.py obsidian [domains|list [domain]|read <path>|search <q>|logs [n]]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COMMANDS = {
    "status": cmd_status,
    "gmail": cmd_gmail,
    "github": cmd_github,
    "slack": cmd_slack,
    "obsidian": cmd_obsidian,
}

if __name__ == "__main__":
    load_env()

    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("Commands:", ", ".join(COMMANDS))
        sys.exit(1)

    cmd = sys.argv[1]
    rest = sys.argv[2:]
    try:
        COMMANDS[cmd](rest)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)

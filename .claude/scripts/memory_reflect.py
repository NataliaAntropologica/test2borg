#!/usr/bin/env python3
"""
Daily reflection — promotes yesterday's important log entries to MEMORY.md.
Runs daily at 8 AM COT (scheduled in Phase 9).

The reflection agent has a PreToolUse hook (soul-write-protect.py) that blocks
any attempt to edit SOUL.md directly. Suggestions for SOUL.md changes are
written to the daily log instead (prevents "soul drift").
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

# Recursion prevention
os.environ["CLAUDE_INVOKED_BY"] = "memory_reflect"

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from shared import (
    VAULT_PATH, append_to_daily_log, atomic_write, file_lock, today_log_path,
)

COT_OFFSET = datetime.timezone(datetime.timedelta(hours=-5))


def log(msg: str):
    ts = datetime.datetime.now(tz=COT_OFFSET).strftime("%H:%M")
    print(f"[{ts} COT] {msg}")


def yesterday_log() -> tuple[str, str]:
    """Return (date_str, content) for yesterday's daily log, or ('', '') if missing."""
    yesterday = (datetime.datetime.now(tz=COT_OFFSET) - datetime.timedelta(days=1))
    date_str = yesterday.strftime("%Y-%m-%d")
    log_path = VAULT_PATH / "daily" / f"{date_str}.md"
    if not log_path.exists():
        return date_str, ""
    return date_str, log_path.read_text(encoding="utf-8")


def run_reflection_agent(log_date: str, log_content: str) -> str:
    """
    Use Claude Agent SDK to identify what deserves promotion to MEMORY.md.
    allowed_tools=["Read", "Edit"] — needs Edit for MEMORY.md, but SOUL.md is protected.
    """
    memory_path = VAULT_PATH / "MEMORY.md"
    current_memory = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""

    system_prompt = f"""You are the Sintetica Strategic Brain daily reflection agent.

Your task: review yesterday's daily log and update MEMORY.md with items worth retaining.

## Rules
- MEMORY.md loads into every Claude session — keep it concise (under 300 lines total)
- Promote: key decisions made, important lessons, new client facts, critical action items
- Skip: routine tasks, mechanical notes, anything already in MEMORY.md
- If you think SOUL.md should change, write the suggestion to today's daily log instead
  (you are blocked from editing SOUL.md directly — this is by design)
- Write changes to MEMORY.md using the Edit tool

## Current MEMORY.md
{current_memory[:2000]}

## Yesterday's log ({log_date})
{log_content[:4000]}

## Instructions
1. Read through yesterday's log carefully
2. Identify 0-5 items worth promoting to MEMORY.md
3. For each item, decide which section of MEMORY.md it belongs in
4. Edit MEMORY.md to add the new items (do not duplicate existing entries)
5. If nothing is worth promoting, output: REFLECTION_OK — nothing to promote
6. If you want to suggest a SOUL.md change, write it to today's daily log as:
   "SOUL.md suggestion: [your suggestion]"

Today's MEMORY.md path: {memory_path}
Today's daily log path: {today_log_path()}
"""

    try:
        from claude_agent_sdk import ClaudeAgentClient, ClaudeAgentOptions

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=["Read", "Edit"],
        )
        client = ClaudeAgentClient(options)
        result = client.query(
            prompt=f"Please reflect on yesterday's log ({log_date}) and update MEMORY.md as needed."
        )
        return result or "REFLECTION_OK"

    except ImportError:
        return "(claude-agent-sdk not installed — install to enable reflection)"
    except Exception as exc:
        return f"(reflection agent error: {exc})"


def run():
    log("=== Daily reflection start ===")

    log_date, log_content = yesterday_log()

    if not log_content.strip():
        log(f"No daily log found for {log_date}. Nothing to reflect on.")
        return

    log(f"Reflecting on {log_date} ({len(log_content)} chars)...")
    result = run_reflection_agent(log_date, log_content)
    log("Reflection complete.")

    # Log outcome to today's daily log
    ts = datetime.datetime.now(tz=COT_OFFSET).strftime("%H:%M")
    append_to_daily_log(
        f"### Morning Reflection ({log_date})\n"
        f"{result[:300] if result != 'REFLECTION_OK' else 'Nothing new to promote to MEMORY.md.'}"
    )

    log("=== Reflection complete ===")


if __name__ == "__main__":
    run()

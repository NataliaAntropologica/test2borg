#!/usr/bin/env python3
"""
Background memory flush — spawned by pre-compact and session-end hooks.
Uses Claude Agent SDK (allowed_tools=[]) to extract what's worth remembering
from the conversation and appends a bullet-point summary to today's daily log.

Usage: python memory_flush.py <path-to-context-tmp-file>
"""

import json
import os
import sys
import time
from pathlib import Path

# Recursion prevention — must be set before any Agent SDK import
os.environ["CLAUDE_INVOKED_BY"] = "memory_flush"

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from shared import (
    DATA_PATH,
    append_to_daily_log,
    atomic_write_json,
    file_lock,
    read_json_safe,
    today_log_path,
)

FLUSH_STATE_PATH = DATA_PATH / "state" / "flush-state.json"
DEDUP_WINDOW_SECONDS = 60


def already_flushed_recently() -> bool:
    """Skip if same session flushed within the dedup window."""
    state = read_json_safe(str(FLUSH_STATE_PATH))
    last_flush = state.get("last_flush_ts", 0)
    return (time.time() - last_flush) < DEDUP_WINDOW_SECONDS


def record_flush():
    state = read_json_safe(str(FLUSH_STATE_PATH))
    state["last_flush_ts"] = time.time()
    FLUSH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(str(FLUSH_STATE_PATH), state)


def run_flush(context_data: dict) -> str:
    """
    Call Claude Agent SDK with allowed_tools=[] to extract memorable content.
    Returns either a bullet-point summary string or "FLUSH_OK" if nothing to save.
    """
    conversation = context_data.get("conversation", "")
    if not conversation:
        return "FLUSH_OK"

    system_prompt = """You are the memory distiller for Sintetica's Strategic Brain.

Your task: read a conversation and extract ONLY what is genuinely worth remembering
for future sessions. Be selective — most conversations produce 0-3 bullet points.

Extract only:
- Strategic decisions made (with brief rationale)
- Lessons learned or mistakes to avoid
- New client or project facts
- Action items with owners and deadlines
- Important context that will be needed later

Do NOT extract:
- Casual discussion or thinking-out-loud
- Information already obvious from file names or structure
- Tool usage details
- Anything that can be re-derived from the codebase

Output format:
If nothing is worth saving, output exactly: FLUSH_OK

Otherwise output bullet points starting with "- ", for example:
- Decided to use SQLite for Phase 3 (simpler than Postgres for single-user local setup)
- Client X prefers async communication; avoid scheduling calls before 10 AM COT
- Action: Natalia to review draft proposal for Y by 2026-06-25"""

    try:
        from claude_agent_sdk import ClaudeAgentClient, ClaudeAgentOptions

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=[],
        )
        client = ClaudeAgentClient(options)

        if isinstance(conversation, list):
            prompt = json.dumps(conversation, ensure_ascii=False)
        else:
            prompt = str(conversation)

        result = client.query(prompt=f"Extract what is worth remembering:\n\n{prompt}")
        return result.strip() if result else "FLUSH_OK"

    except ImportError:
        # Agent SDK not yet installed — write a placeholder
        return "- [memory_flush] Agent SDK not installed; install claude-agent-sdk to enable intelligent summarization"
    except Exception as exc:
        return f"- [memory_flush error] {exc}"


def main():
    if len(sys.argv) < 2:
        print("Usage: memory_flush.py <context-tmp-file>", file=sys.stderr)
        sys.exit(1)

    tmp_path = Path(sys.argv[1])
    if not tmp_path.exists():
        sys.exit(0)

    try:
        context_data = json.loads(tmp_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        tmp_path.unlink(missing_ok=True)
        sys.exit(0)

    # Clean up temp file immediately
    tmp_path.unlink(missing_ok=True)

    if already_flushed_recently():
        sys.exit(0)

    record_flush()

    summary = run_flush(context_data)

    if summary == "FLUSH_OK" or not summary.strip():
        sys.exit(0)

    # Append to today's daily log under a flush section
    source = context_data.get("source", "flush")
    header = f"### Memory Flush ({source})"
    with file_lock(str(today_log_path())):
        log_path = today_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{header}\n{summary}\n")


if __name__ == "__main__":
    main()

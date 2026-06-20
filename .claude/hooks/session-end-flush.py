#!/usr/bin/env python3
"""
SessionEnd hook — extract conversation context on session end,
then spawn memory_flush.py as a background process.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Recursion prevention: skip if we're inside an Agent SDK session
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_PATH = REPO_ROOT / ".claude" / "data"
DATA_PATH.mkdir(parents=True, exist_ok=True)

try:
    hook_input = json.load(sys.stdin)
except (json.JSONDecodeError, EOFError):
    hook_input = {}

conversation = hook_input.get("conversation", hook_input.get("messages", ""))
if not conversation:
    sys.exit(0)

tmp_file = DATA_PATH / f"flush-context-{int(time.time())}.tmp"
tmp_file.write_text(
    json.dumps({"source": "session-end", "conversation": conversation}, ensure_ascii=False),
    encoding="utf-8"
)

flush_script = REPO_ROOT / ".claude" / "scripts" / "memory_flush.py"
subprocess.Popen(
    [sys.executable, str(flush_script), str(tmp_file)],
    start_new_session=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

sys.exit(0)

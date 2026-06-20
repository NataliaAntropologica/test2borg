"""
Shared utilities used across all Sintetica Brain scripts.
Import with: from shared import file_lock, with_retry, atomic_write, DANGEROUS_BASH_PATTERNS
"""

import contextlib
import fcntl
import json
import os
import re
import time
from pathlib import Path

VAULT_PATH = Path(__file__).parent.parent.parent / "Sintetica" / "Memory"
DATA_PATH = Path(__file__).parent.parent / "data"
STATE_PATH = DATA_PATH / "state"


# ---------------------------------------------------------------------------
# File locking (macOS / Linux via fcntl)
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def file_lock(path: str):
    """Exclusive file lock. Required for any file written by multiple processes."""
    lock_path = str(path) + ".lock"
    with open(lock_path, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------

def with_retry(fn, max_retries: int = 3, base_delay: float = 1.0):
    """Wrap external API calls. Retries on any exception with exponential backoff."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
    raise last_exc


# ---------------------------------------------------------------------------
# Atomic file writes
# ---------------------------------------------------------------------------

def atomic_write(path: str, content: str):
    """Write to .tmp then os.replace() — safe against crash mid-write."""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


def atomic_write_json(path: str, data: dict):
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False))


def read_json_safe(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


# ---------------------------------------------------------------------------
# Daily log helpers
# ---------------------------------------------------------------------------

def today_log_path() -> Path:
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_path = VAULT_PATH / "daily" / f"{today}.md"
    return log_path


def append_to_daily_log(entry: str):
    """Append a timestamped entry to today's daily log with file lock."""
    import datetime
    log_path = today_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%H:%M")
    line = f"\n- {timestamp} COT — {entry.strip()}\n"
    with file_lock(str(log_path)):
        with open(log_path, "a", encoding="utf-8") as f:
            if not log_path.exists() or log_path.stat().st_size == 0:
                f.write(f"# Daily Log — {datetime.datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(line)


# ---------------------------------------------------------------------------
# Dangerous bash patterns (used by block-secrets.py)
# ---------------------------------------------------------------------------

DANGEROUS_BASH_PATTERNS = [
    # Destructive filesystem
    r"rm\s+-[rRf]*f[rRf]*\s",
    r"\brm\b.*\s/",
    r"\bdd\b.*if=",
    r"\bmkfs\b",
    r":\(\)\s*\{.*\|.*&",          # fork bomb
    r"\bshred\b",
    r"\bwipe\b",
    r"\btruncate\b.*--size\s*0",

    # Credential / environment exfiltration
    r"cat\s+\.env",
    r"cat\s+.*token",
    r"cat\s+.*credentials",
    r"\bprintenv\b",
    r"env\s*$",
    r"echo\s+\$[A-Z_]*(TOKEN|KEY|SECRET|PASSWORD|PASS|API)[A-Z_]*",
    r"python.*os\.environ",
    r"python.*getenv",

    # Network exfiltration (non-allowlisted outbound curl/wget)
    r"curl\s+.*\|\s*(sh|bash|python|perl)",
    r"wget\s+.*\|\s*(sh|bash|python|perl)",
    r"curl\s+.*-d\s+.*\$",         # posting env vars

    # Package installation (requires explicit permission)
    r"\bpip\s+install\b",
    r"\bnpm\s+install\b",
    r"\bbrew\s+install\b",
    r"\bapt(-get)?\s+install\b",
    r"\byum\s+install\b",

    # Privilege escalation
    r"\bsudo\b",
    r"\bsu\s+-\b",
    r"\bchmod\s+[0-7]*7[0-7][0-7]\b",   # world-writable
    r"\bchown\s+root\b",

    # Git destructive
    r"git\s+push\s+.*--force",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[fdx]+",
    r"git\s+branch\s+-[Dd]",

    # Subshell injection markers (content re-checked recursively)
    r"\$\([^)]+\)",
    r"`[^`]+`",

    # Binary path bypass attempts
    r"/(?:usr/(?:local/)?)?bin/rm\b",
    r"/(?:usr/(?:local/)?)?bin/dd\b",
    r"/(?:usr/(?:local/)?)?bin/shred\b",
]

SENSITIVE_FILE_PATTERNS = [
    r"\.env$",
    r"\.env\.",
    r"_token\.json$",
    r"credentials\.json$",
    r"client_secrets\.json$",
    r"google_token\.json$",
    r"slack_token\.json$",
    r"github_token\.json$",
    r"\.pem$",
    r"\.key$",
    r"\.p12$",
    r"\.pfx$",
    r"id_rsa",
    r"id_ed25519",
    r"authorized_keys",
    r"\.ssh/",
]


def extract_subshells(cmd: str) -> list:
    """Extract content from $(...) and backtick constructs recursively."""
    results = []
    for m in re.finditer(r'\$\(([^)]+)\)', cmd):
        results.append(m.group(1))
        results.extend(extract_subshells(m.group(1)))
    for m in re.finditer(r'`([^`]+)`', cmd):
        results.append(m.group(1))
    return results


def strip_binary_paths(cmd: str) -> str:
    """Remove common binary path prefixes before pattern matching."""
    return re.sub(r'/(?:usr/(?:local/)?)?bin/', '', cmd)


def is_dangerous_command(cmd: str) -> tuple:
    """Returns (is_dangerous: bool, matched_pattern: str)."""
    candidates = [cmd, strip_binary_paths(cmd)] + extract_subshells(cmd)
    for candidate in candidates:
        for pattern in DANGEROUS_BASH_PATTERNS:
            if re.search(pattern, candidate, re.IGNORECASE):
                return True, pattern
    return False, ""


def is_sensitive_path(path: str) -> bool:
    """Returns True if the path matches a sensitive file pattern."""
    for pattern in SENSITIVE_FILE_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return True
    return False

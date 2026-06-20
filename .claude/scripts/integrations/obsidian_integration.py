"""
Obsidian integration — read and search the local Sintetica vault.
No API needed. Direct filesystem access to markdown files.
The vault is at ~/Sintetica/ (or VAULT_ROOT env var for overrides).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))

from shared import VAULT_PATH, append_to_daily_log, file_lock

# Support override via env var for VPS deployments
VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(VAULT_PATH)))


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class VaultNote:
    relative_path: str
    title: str
    content: str
    domain: str  # decisions, clients, trends, etc.

    def to_context(self) -> str:
        preview = self.content[:300].replace("\n", " ")
        return f"[{self.domain}] {self.title}\n  Path: {self.relative_path}\n  {preview}"


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _domain_from_path(path: Path) -> str:
    """Infer memory domain from the file's parent directory."""
    parts = path.relative_to(VAULT_ROOT).parts
    return parts[0] if len(parts) > 1 else "root"


def _title_from_content(content: str, filename: str) -> str:
    """Extract title from first H1 heading or filename."""
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return Path(filename).stem.replace("-", " ").replace("_", " ").title()


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def list_notes(domain: Optional[str] = None) -> list[VaultNote]:
    """List all notes, optionally filtered by domain folder."""
    root = VAULT_ROOT / domain if domain else VAULT_ROOT
    if not root.exists():
        return []
    notes = []
    for p in sorted(root.rglob("*.md")):
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            notes.append(VaultNote(
                relative_path=str(p.relative_to(VAULT_ROOT)),
                title=_title_from_content(content, p.name),
                content=content,
                domain=_domain_from_path(p),
            ))
        except Exception:
            continue
    return notes


def read_note(relative_path: str) -> Optional[str]:
    """Read a specific note by its relative path within the vault."""
    p = VAULT_ROOT / relative_path
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")


def keyword_search(query: str, domain: Optional[str] = None) -> list[VaultNote]:
    """Simple case-insensitive keyword search across vault notes."""
    terms = query.lower().split()
    results = []
    for note in list_notes(domain):
        text = (note.title + " " + note.content).lower()
        if all(t in text for t in terms):
            results.append(note)
    return results


def recent_daily_logs(n: int = 7) -> list[tuple[str, str]]:
    """Return the n most recent daily log entries as (date, content) tuples."""
    daily_dir = VAULT_ROOT / "daily"
    if not daily_dir.exists():
        return []
    logs = sorted(daily_dir.glob("*.md"), reverse=True)[:n]
    return [(p.stem, p.read_text(encoding="utf-8", errors="replace")) for p in logs]


def append_note(relative_path: str, content: str):
    """Append content to a vault file with file lock."""
    p = VAULT_ROOT / relative_path
    p.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(str(p)):
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)


def list_domains() -> list[str]:
    """List all top-level memory domain directories."""
    if not VAULT_ROOT.exists():
        return []
    return [d.name for d in sorted(VAULT_ROOT.iterdir()) if d.is_dir() and not d.name.startswith(".")]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Obsidian vault integration")
    parser.add_argument("--domains", action="store_true", help="List memory domains")
    parser.add_argument("--list", metavar="DOMAIN", help="List notes in a domain")
    parser.add_argument("--read", metavar="PATH", help="Read a specific note")
    parser.add_argument("--search", metavar="QUERY", help="Keyword search")
    parser.add_argument("--recent-logs", type=int, default=3, help="Show recent daily logs")
    args = parser.parse_args()

    if args.domains:
        for d in list_domains():
            notes = list_notes(d)
            print(f"  {d:20} ({len(notes)} notes)")
    elif args.list:
        notes = list_notes(args.list)
        for n in notes:
            print(f"  {n.relative_path}: {n.title}")
    elif args.read:
        content = read_note(args.read)
        print(content if content else f"Note not found: {args.read}")
    elif args.search:
        results = keyword_search(args.search)
        if not results:
            print(f"No results for '{args.search}'")
        for r in results[:10]:
            print(r.to_context())
            print()
    else:
        logs = recent_daily_logs(args.recent_logs)
        for date, content in logs:
            print(f"\n=== {date} ===\n{content[:500]}")

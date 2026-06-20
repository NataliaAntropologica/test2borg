#!/usr/bin/env python3
"""
Rapid capture script — creates a new note in the specified memory domain.

Usage:
  python capture.py decisions "Switch to async-first client communication"
  python capture.py trends "AI regulation wave in Latin America" --tags "AI,policy,latam"
  python capture.py --list-domains
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))
from shared import VAULT_PATH

VALID_DOMAINS = [
    "decisions", "clients", "research", "trends", "signals",
    "projects", "lessons", "hypotheses", "opportunities",
    "scenarios", "team", "capabilities", "innovation",
]


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug[:60]


def make_filename(domain: str, title: str) -> str:
    today = datetime.date.today().strftime("%Y-%m-%d")
    slug = slugify(title)
    # Clients and research don't need dates in filenames
    if domain in ("clients", "research", "capabilities"):
        return f"{slug}.md"
    return f"{today}-{slug}.md"


def make_frontmatter(domain: str, title: str, tags: list[str]) -> str:
    today = datetime.date.today().isoformat()
    tag_str = "[" + ", ".join(tags) + "]" if tags else "[]"
    return f"""---
title: "{title}"
date: {today}
domain: {domain}
status: active
tags: {tag_str}
---

"""


def make_body_template(domain: str, title: str) -> str:
    templates = {
        "decisions": (
            "## Context\n\n\n\n"
            "## Decision\n\n\n\n"
            "## Rationale\n\n\n\n"
            "## Alternatives Considered\n\n\n\n"
            "## Expected Outcomes\n\n\n\n"
            "## Review Date\n\n"
        ),
        "clients": (
            "## Overview\n\n\n\n"
            "## Key Contacts\n\n\n\n"
            "## Preferences & Working Style\n\n\n\n"
            "## Active Engagements\n\n\n\n"
            "## Intelligence & Notes\n\n"
        ),
        "trends": (
            "## Summary\n\n\n\n"
            "## Evidence\n\n\n\n"
            "## Implications for Sintetica\n\n\n\n"
            "## Horizon\n\n0-1yr / 1-3yr / 3-5yr / 5yr+\n\n"
            "## Sources\n\n"
        ),
        "signals": (
            "## Signal\n\n\n\n"
            "## Source\n\n\n\n"
            "## Why notable\n\n\n\n"
            "## Strength\n\nWeak / Emerging / Confirmed\n\n"
            "## Watch for\n\n"
        ),
        "hypotheses": (
            "## Hypothesis\n\n\n\n"
            "## Rationale\n\n\n\n"
            "## Evidence FOR\n\n\n\n"
            "## Evidence AGAINST\n\n\n\n"
            "## Falsification condition\n\n(This hypothesis is wrong if...)\n\n"
            "## Status\n\nTracking / Validated / Invalidated\n"
        ),
        "opportunities": (
            "## Opportunity\n\n\n\n"
            "## Why now\n\n\n\n"
            "## Fit for Sintetica\n\n\n\n"
            "## Next action\n\n\n\n"
            "## Status\n\nNew / Evaluating / Pursuing / Passed\n"
        ),
        "scenarios": (
            "## Scenario\n\n\n\n"
            "## Key Drivers\n\n\n\n"
            "## Trigger Conditions\n\n(What would make this scenario more likely?)\n\n"
            "## Implications\n\n\n\n"
            "## Strategic Response\n\n"
        ),
        "lessons": (
            "## Context\n\n(Where/when did this apply?)\n\n"
            "## Lesson\n\n\n\n"
            "## Transferable principle\n\n(On projects with X, do Y.)\n\n"
            "## Counter-examples\n\n"
        ),
    }
    return templates.get(domain, "## Notes\n\n\n")


def create_note(domain: str, title: str, tags: list[str], open_after: bool = False) -> Path:
    domain_path = VAULT_PATH / domain
    domain_path.mkdir(parents=True, exist_ok=True)

    filename = make_filename(domain, title)
    filepath = domain_path / filename

    if filepath.exists():
        print(f"Note already exists: {filepath}")
        return filepath

    content = make_frontmatter(domain, title, tags) + make_body_template(domain, title)
    filepath.write_text(content, encoding="utf-8")
    print(f"Created: {filepath.relative_to(VAULT_PATH.parent)}")
    return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rapid strategic capture")
    parser.add_argument("domain", nargs="?", help=f"Memory domain: {', '.join(VALID_DOMAINS)}")
    parser.add_argument("title", nargs="?", help="Note title")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--list-domains", action="store_true", help="List valid domains")
    args = parser.parse_args()

    if args.list_domains:
        for d in VALID_DOMAINS:
            count = len(list((VAULT_PATH / d).glob("*.md"))) if (VAULT_PATH / d).exists() else 0
            print(f"  {d:20} ({count} notes)")
        sys.exit(0)

    if not args.domain or not args.title:
        parser.print_help()
        sys.exit(1)

    if args.domain not in VALID_DOMAINS:
        print(f"Unknown domain: {args.domain}")
        print(f"Valid: {', '.join(VALID_DOMAINS)}")
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
    create_note(args.domain, args.title, tags)

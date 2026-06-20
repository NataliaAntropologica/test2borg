"""
GitHub integration — list open PRs, assigned issues, generate code review summaries.
Auth: Personal Access Token loaded from GITHUB_TOKEN env var. Never passed to Claude.

Setup: Add GITHUB_TOKEN=ghp_... to .env
Required scopes: contents:read, pull_requests:read, issues:read, metadata:read

Fine-grained PAT recommended (Settings -> Developer settings -> Personal access tokens).
Rate limit: 5,000 requests/hour for authenticated users.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))

from shared import with_retry


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_client():
    """Return an authenticated PyGithub client. Token loaded from environment."""
    from github import Github

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN not set. Add it to .env and re-open your terminal."
        )
    return Github(token)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PRSummary:
    number: int
    title: str
    author: str
    url: str
    base_branch: str
    head_branch: str
    files_changed: int
    additions: int
    deletions: int
    file_list: list[str] = field(default_factory=list)
    high_risk_files: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    draft: bool = False

    def to_context(self) -> str:
        risk = f"\n  High-risk files: {', '.join(self.high_risk_files)}" if self.high_risk_files else ""
        return (
            f"PR #{self.number}: {self.title}\n"
            f"  Author: {self.author} | {self.base_branch} <- {self.head_branch}\n"
            f"  Changes: +{self.additions}/-{self.deletions} across {self.files_changed} files"
            f"{risk}\n"
            f"  URL: {self.url}"
        )


@dataclass
class IssueSummary:
    number: int
    title: str
    author: str
    url: str
    state: str
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    body_preview: str = ""

    def to_context(self) -> str:
        return (
            f"Issue #{self.number}: {self.title}\n"
            f"  State: {self.state} | Author: {self.author}\n"
            f"  Labels: {', '.join(self.labels) or 'none'}\n"
            f"  {self.body_preview[:150]}"
        )


# ---------------------------------------------------------------------------
# High-risk file detection
# ---------------------------------------------------------------------------

HIGH_RISK_EXTENSIONS = {".sql", ".sh", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini"}
HIGH_RISK_PATHS = {"migrations/", "schema", "auth", "security", "deploy", "infra", "secrets"}


def is_high_risk(filename: str) -> bool:
    p = Path(filename)
    if p.suffix.lower() in HIGH_RISK_EXTENSIONS:
        return True
    lower = filename.lower()
    return any(pat in lower for pat in HIGH_RISK_PATHS)


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def list_open_prs(
    g,
    repos: list[str],
    max_per_repo: int = 10,
) -> list[PRSummary]:
    """List open PRs across repos with diff summary for code review sweep."""
    results = []
    for repo_name in repos:
        try:
            repo = with_retry(lambda r=repo_name: g.get_repo(r))
            prs = with_retry(lambda: list(repo.get_pulls(
                state="open", sort="updated", direction="desc"
            )[:max_per_repo]))
            for pr in prs:
                files = with_retry(lambda p=pr: list(p.get_files()))
                high_risk = [f.filename for f in files if is_high_risk(f.filename)]
                results.append(PRSummary(
                    number=pr.number,
                    title=pr.title,
                    author=pr.user.login,
                    url=pr.html_url,
                    base_branch=pr.base.ref,
                    head_branch=pr.head.ref,
                    files_changed=pr.changed_files,
                    additions=pr.additions,
                    deletions=pr.deletions,
                    file_list=[f.filename for f in files],
                    high_risk_files=high_risk,
                    labels=[lbl.name for lbl in pr.labels],
                    draft=pr.draft,
                ))
        except Exception as exc:
            print(f"  Warning: could not fetch PRs for {repo_name}: {exc}", file=sys.stderr)
    return results


def list_assigned_issues(g, username: Optional[str] = None) -> list[IssueSummary]:
    """List open issues assigned to the authenticated user."""
    user = with_retry(g.get_user) if not username else with_retry(lambda: g.get_user(username))
    login = user.login
    issues = with_retry(lambda: list(g.search_issues(
        f"assignee:{login} is:open is:issue"
    )[:20]))
    return [
        IssueSummary(
            number=i.number,
            title=i.title,
            author=i.user.login,
            url=i.html_url,
            state=i.state,
            labels=[lbl.name for lbl in i.labels],
            assignees=[a.login for a in i.assignees],
            body_preview=(i.body or "")[:200],
        )
        for i in issues
    ]


def get_rate_limit(g) -> str:
    rl = with_retry(g.get_rate_limit)
    return (
        f"Core: {rl.core.remaining}/{rl.core.limit} requests remaining "
        f"(resets at {rl.core.reset})"
    )


def format_prs_for_context(prs: list[PRSummary]) -> str:
    if not prs:
        return "No open PRs found."
    lines = [f"Open PRs ({len(prs)}):"]
    for pr in prs:
        lines.append(f"\n{pr.to_context()}")
    return "\n".join(lines)


def format_issues_for_context(issues: list[IssueSummary]) -> str:
    if not issues:
        return "No assigned issues found."
    lines = [f"Assigned issues ({len(issues)}):"]
    for issue in issues:
        lines.append(f"\n{issue.to_context()}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GitHub integration")
    parser.add_argument("--prs", nargs="+", metavar="OWNER/REPO", help="List open PRs")
    parser.add_argument("--issues", action="store_true", help="List assigned issues")
    parser.add_argument("--rate-limit", action="store_true", help="Show API rate limit")
    args = parser.parse_args()

    # Load .env if present
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    g = get_client()

    if args.prs:
        prs = list_open_prs(g, args.prs)
        print(format_prs_for_context(prs))
    elif args.issues:
        issues = list_assigned_issues(g)
        print(format_issues_for_context(issues))
    elif args.rate_limit:
        print(get_rate_limit(g))
    else:
        parser.print_help()

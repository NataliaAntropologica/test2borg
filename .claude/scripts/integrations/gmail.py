"""
Gmail integration — read emails, detect thread replies, list unread messages.
Auth: OAuth2 (Authorization Code Flow). Credentials never passed to Claude.

First-time setup:
  1. Download credentials.json from Google Cloud Console (Desktop App type)
  2. Place at .claude/credentials.json
  3. Run: python .claude/scripts/integrations/gmail.py --auth
     (opens browser, saves token to .claude/gmail_token.json)

Scopes:
  - gmail.readonly  — read messages
  - gmail.modify    — mark as read / detect sent replies
"""

from __future__ import annotations

import base64
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPTS = REPO_ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from shared import with_retry

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]
TOKEN_PATH = REPO_ROOT / ".claude" / "gmail_token.json"
CREDS_PATH = REPO_ROOT / ".claude" / "credentials.json"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_service():
    """Return an authenticated Gmail service. Refreshes token automatically."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError(
                "Gmail not authenticated. Run: "
                "python .claude/scripts/integrations/gmail.py --auth"
            )
        TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def run_auth():
    """Interactive OAuth2 flow — opens browser, saves token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CREDS_PATH.exists():
        print(f"ERROR: {CREDS_PATH} not found.")
        print("Download it from Google Cloud Console (OAuth2 Desktop App credentials).")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    print(f"Auth complete. Token saved to {TOKEN_PATH}")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Email:
    msg_id: str
    thread_id: str
    subject: str
    sender: str
    snippet: str
    date: str
    labels: list[str] = field(default_factory=list)
    body_text: str = ""

    def to_context(self) -> str:
        return (
            f"From: {self.sender}\n"
            f"Subject: {self.subject}\n"
            f"Date: {self.date}\n"
            f"ID: {self.msg_id}\n"
            f"Preview: {self.snippet[:200]}"
        )


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def _header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def list_unread(service, max_results: int = 20, query: str = "") -> list[Email]:
    """List unread emails matching the query (default: non-promotional unread)."""
    q = query or "is:unread -category:promotions -category:social -category:updates"

    def _fetch():
        return service.users().messages().list(
            userId="me", q=q, maxResults=max_results
        ).execute()

    result = with_retry(_fetch)
    messages = result.get("messages", [])
    emails = []
    for m in messages:
        msg = with_retry(lambda mid=m["id"]: service.users().messages().get(
            userId="me", id=mid, format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute())
        emails.append(Email(
            msg_id=msg["id"],
            thread_id=msg["threadId"],
            subject=_header(msg, "Subject"),
            sender=_header(msg, "From"),
            snippet=msg.get("snippet", ""),
            date=_header(msg, "Date"),
            labels=msg.get("labelIds", []),
        ))
    return emails


def get_thread(service, thread_id: str) -> list[dict]:
    """Get all messages in a thread."""
    def _fetch():
        return service.users().threads().get(
            userId="me", id=thread_id, format="metadata"
        ).execute()
    return with_retry(_fetch).get("messages", [])


def check_replied(service, source_msg_id: str) -> Optional[str]:
    """
    Check if the user has sent a reply to source_msg_id.
    Returns the sent reply's message ID, or None if no reply yet.
    """
    def _fetch():
        return service.users().messages().list(
            userId="me",
            q=f"in:sent",
            maxResults=50,
        ).execute()

    result = with_retry(_fetch)
    for m in result.get("messages", []):
        msg = with_retry(lambda mid=m["id"]: service.users().messages().get(
            userId="me", id=mid, format="metadata",
            metadataHeaders=["In-Reply-To", "References"]
        ).execute())
        in_reply_to = _header(msg, "In-Reply-To")
        references = _header(msg, "References")
        if source_msg_id in in_reply_to or source_msg_id in references:
            return msg["id"]
    return None


def mark_as_read(service, msg_id: str):
    with_retry(lambda: service.users().messages().modify(
        userId="me", id=msg_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute())


def format_for_context(emails: list[Email]) -> str:
    if not emails:
        return "No unread emails."
    lines = [f"Unread emails ({len(emails)}):"]
    for e in emails:
        lines.append(f"\n  [{e.msg_id}] {e.subject}")
        lines.append(f"  From: {e.sender} | {e.date}")
        lines.append(f"  {e.snippet[:150]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gmail integration")
    parser.add_argument("--auth", action="store_true", help="Run OAuth2 setup flow")
    parser.add_argument("--list", action="store_true", help="List unread emails")
    parser.add_argument("--max", type=int, default=20, help="Max results")
    parser.add_argument("--thread", help="Get thread by ID")
    args = parser.parse_args()

    if args.auth:
        run_auth()
    elif args.list:
        svc = get_service()
        emails = list_unread(svc, max_results=args.max)
        print(format_for_context(emails))
    elif args.thread:
        svc = get_service()
        msgs = get_thread(svc, args.thread)
        print(json.dumps(msgs, indent=2))
    else:
        parser.print_help()

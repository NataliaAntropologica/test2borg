"""
Slack integration — read messages (read-only). No sending, per security boundaries.
Auth: Bot Token + App Token (Socket Mode — no public URL needed).

Setup:
  1. Create a Slack App at api.slack.com/apps
  2. Enable Socket Mode -> generates App Token (xapp-...)
  3. Add Bot Token scopes: channels:history, channels:read, groups:history,
     im:history, mpim:history, users:read
  4. Install app to workspace -> get Bot Token (xoxb-...)
  5. Add to .env: SLACK_BOT_TOKEN=xoxb-... and SLACK_APP_TOKEN=xapp-...

IMPORTANT: Do NOT add chat:write scope. This integration is read-only by design.
Natalia's security policy prohibits sending Slack messages without explicit approval.
"""

from __future__ import annotations

import os
import sys
import time
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
    """Return an authenticated Slack WebClient."""
    from slack_sdk import WebClient

    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError(
            "SLACK_BOT_TOKEN not set. Add it to .env."
        )
    return WebClient(token=token)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SlackMessage:
    ts: str
    channel_id: str
    channel_name: str
    user: str
    text: str
    thread_ts: Optional[str] = None
    is_dm: bool = False

    @property
    def is_thread_reply(self) -> bool:
        return self.thread_ts is not None and self.thread_ts != self.ts

    def to_context(self) -> str:
        dm_tag = " [DM]" if self.is_dm else ""
        thread_tag = " [thread]" if self.is_thread_reply else ""
        return f"#{self.channel_name}{dm_tag}{thread_tag} @{self.user}: {self.text[:200]}"


# ---------------------------------------------------------------------------
# Channel helpers
# ---------------------------------------------------------------------------

def list_channels(client) -> list[dict]:
    """List all channels the bot is a member of."""
    def _fetch():
        return client.conversations_list(types="public_channel,private_channel,mpim,im").data
    result = with_retry(_fetch)
    return result.get("channels", [])


def resolve_channel_name(client, channel_id: str, cache: dict) -> str:
    if channel_id in cache:
        return cache[channel_id]
    try:
        info = with_retry(lambda: client.conversations_info(channel=channel_id).data)
        name = info["channel"].get("name", channel_id)
    except Exception:
        name = channel_id
    cache[channel_id] = name
    return name


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def get_unread_messages(
    client,
    channel_ids: list[str],
    since_ts: Optional[str] = None,
    max_per_channel: int = 20,
) -> list[SlackMessage]:
    """
    Fetch messages since since_ts (Unix timestamp string) across channels.
    If since_ts is None, returns messages from the last 30 minutes.
    """
    if since_ts is None:
        since_ts = str(time.time() - 1800)  # last 30 min

    name_cache: dict[str, str] = {}
    results: list[SlackMessage] = []

    for channel_id in channel_ids:
        try:
            def _fetch(cid=channel_id):
                return client.conversations_history(
                    channel=cid,
                    oldest=since_ts,
                    limit=max_per_channel,
                ).data

            resp = with_retry(_fetch)
            messages = resp.get("messages", [])
            channel_name = resolve_channel_name(client, channel_id, name_cache)

            for msg in messages:
                if msg.get("subtype"):
                    continue  # skip bot messages, joins, etc.
                results.append(SlackMessage(
                    ts=msg["ts"],
                    channel_id=channel_id,
                    channel_name=channel_name,
                    user=msg.get("user", "unknown"),
                    text=msg.get("text", ""),
                    thread_ts=msg.get("thread_ts"),
                ))
        except Exception as exc:
            print(f"  Warning: could not fetch {channel_id}: {exc}", file=sys.stderr)

    return sorted(results, key=lambda m: m.ts)


def get_dms(client, since_ts: Optional[str] = None) -> list[SlackMessage]:
    """Fetch direct messages since since_ts."""
    channels = list_channels(client)
    dm_channels = [c["id"] for c in channels if c.get("is_im") or c.get("is_mpim")]
    return get_unread_messages(client, dm_channels, since_ts=since_ts)


def resolve_usernames(client, messages: list[SlackMessage]) -> list[SlackMessage]:
    """Replace user IDs with display names."""
    user_cache: dict[str, str] = {}
    for msg in messages:
        uid = msg.user
        if uid not in user_cache:
            try:
                info = with_retry(lambda u=uid: client.users_info(user=u).data)
                user_cache[uid] = info["user"].get("display_name") or info["user"].get("real_name", uid)
            except Exception:
                user_cache[uid] = uid
        msg.user = user_cache[uid]
    return messages


def format_for_context(messages: list[SlackMessage]) -> str:
    if not messages:
        return "No new Slack messages."
    lines = [f"New Slack messages ({len(messages)}):"]
    for m in messages:
        lines.append(f"  {m.to_context()}")
    return "\n".join(lines)


def summarize_by_channel(messages: list[SlackMessage]) -> str:
    """Group messages by channel for a digest view."""
    if not messages:
        return "No new Slack messages."
    by_channel: dict[str, list[SlackMessage]] = {}
    for m in messages:
        by_channel.setdefault(m.channel_name, []).append(m)
    lines = []
    for ch, msgs in sorted(by_channel.items()):
        lines.append(f"\n#{ch} ({len(msgs)} messages):")
        for m in msgs[:5]:
            lines.append(f"  @{m.user}: {m.text[:100]}")
        if len(msgs) > 5:
            lines.append(f"  ... and {len(msgs) - 5} more")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Slack integration (read-only)")
    parser.add_argument("--channels", nargs="+", help="Channel IDs to read")
    parser.add_argument("--dms", action="store_true", help="Fetch direct messages")
    parser.add_argument("--since", help="Unix timestamp (default: last 30 min)")
    parser.add_argument("--summary", action="store_true", help="Group by channel")
    args = parser.parse_args()

    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    client = get_client()

    if args.dms:
        msgs = get_dms(client, since_ts=args.since)
    elif args.channels:
        msgs = get_unread_messages(client, args.channels, since_ts=args.since)
    else:
        channels = list_channels(client)
        all_ids = [c["id"] for c in channels]
        msgs = get_unread_messages(client, all_ids, since_ts=args.since)

    msgs = resolve_usernames(client, msgs)

    if args.summary:
        print(summarize_by_channel(msgs))
    else:
        print(format_for_context(msgs))

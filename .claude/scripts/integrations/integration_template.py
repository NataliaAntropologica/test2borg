"""
Integration template — copy this file and replace TODOs to add a new integration.

Usage:
  cp integration_template.py my_service.py
  # Fill in the TODOs below
  # Register in registry.py
  # Add a subcommand in query.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))
from shared import with_retry

# TODO: set the env var name for this integration's API token
TOKEN_ENV_VAR = "MY_SERVICE_TOKEN"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_client():
    """TODO: return an authenticated client. Load token from env, never from vault."""
    token = os.environ.get(TOKEN_ENV_VAR, "")
    if not token:
        raise RuntimeError(f"{TOKEN_ENV_VAR} not set. Add it to .env.")
    # TODO: return the SDK client
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MyServiceItem:
    """TODO: define the fields that matter for context injection."""
    item_id: str
    title: str
    summary: str

    def to_context(self) -> str:
        return f"{self.title}: {self.summary[:150]}"


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def list_items(client, max_results: int = 20) -> list[MyServiceItem]:
    """TODO: fetch items from the service. Use with_retry() for all API calls."""
    def _fetch():
        raise NotImplementedError
    result = with_retry(_fetch)
    return []


def format_for_context(items: list[MyServiceItem]) -> str:
    if not items:
        return "No items found."
    lines = [f"Items ({len(items)}):"]
    for item in items:
        lines.append(f"  {item.to_context()}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TODO: my service integration")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        client = get_client()
        items = list_items(client)
        print(format_for_context(items))

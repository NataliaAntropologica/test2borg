#!/bin/bash
# Vault sync setup — run once per machine (macOS and VPS).
# Configures the concat-both git merge driver and checks for git-sync.
set -e

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
cd "$REPO_ROOT"

echo "Sintetica vault sync setup"
echo "=========================="
echo "Repo root: $REPO_ROOT"
echo ""

# ── Step 1: concat-both merge driver ─────────────────────────────────────
echo "Step 1: Registering concat-both merge driver..."

git config merge.concat-both.driver "./git-merge-concat %O %A %B"
git config merge.concat-both.name "Append-only daily log merge"

if [ ! -x "$REPO_ROOT/git-merge-concat" ]; then
    chmod +x "$REPO_ROOT/git-merge-concat"
    echo "  chmod +x git-merge-concat"
fi

echo "  ✓ merge.concat-both registered in $(git config --show-origin merge.concat-both.name | head -1 | awk '{print $1}')"

# ── Step 2: verify .gitattributes ────────────────────────────────────────
echo ""
echo "Step 2: Verifying .gitattributes..."

if grep -q "merge=concat-both" "$REPO_ROOT/.gitattributes" 2>/dev/null; then
    echo "  ✓ .gitattributes has concat-both rule"
else
    echo "  ✗ .gitattributes missing concat-both rule — was it committed?"
fi

# ── Step 3: git-sync check ───────────────────────────────────────────────
echo ""
echo "Step 3: Checking for git-sync..."

if command -v git-sync &>/dev/null; then
    echo "  ✓ git-sync found: $(command -v git-sync)"
    echo ""
    echo "  Recommended git-sync config (add to your git-sync config file):"
    echo "    PULL_BEFORE_PUSH=true"
    echo "    BRANCH=main"
    echo "    REMOTE=origin"
    echo ""
    echo "  Manual test run:"
    echo "    git-sync $REPO_ROOT"
    echo ""
    echo "  To add to launchd (macOS), run:"
    echo "    python .claude/scripts/scheduler_setup.py install"
    echo "  (git-sync plist is separate — see https://github.com/simonthum/git-sync)"
else
    echo "  git-sync not found. Install options:"
    echo ""
    echo "  macOS (Homebrew):"
    echo "    brew install git-sync"
    echo ""
    echo "  Linux / manual:"
    echo "    curl -o ~/bin/git-sync https://raw.githubusercontent.com/simonthum/git-sync/master/git-sync"
    echo "    chmod +x ~/bin/git-sync"
    echo ""
    echo "  After install, configure and add to launchd/systemd:"
    echo "    git-sync $REPO_ROOT   # test run"
fi

# ── Step 4: SSH key check (VPS only) ─────────────────────────────────────
echo ""
echo "Step 4: SSH key check..."

if [ -f "$HOME/.ssh/id_ed25519" ] || [ -f "$HOME/.ssh/id_rsa" ]; then
    echo "  ✓ SSH key found — ensure public key is authorized on the other machine"
else
    echo "  No SSH key found. Generate one if syncing to/from VPS:"
    echo "    ssh-keygen -t ed25519 -C 'sintetica-sync'"
    echo "    ssh-copy-id user@your-vps"
fi

# ── Step 5: .env reminder ────────────────────────────────────────────────
echo ""
echo "Step 5: Environment variables..."
echo "  IMPORTANT: .env is NOT synced via git (it's in .gitignore)."
echo "  Copy .env to the other machine manually over SSH:"
echo "    scp .env user@your-vps:$REPO_ROOT/.env"

echo ""
echo "Setup complete. Both machines must run this script."

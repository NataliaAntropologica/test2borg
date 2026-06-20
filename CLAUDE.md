# Sintetica Strategic Brain — Project Instructions

## What this is
An AI-powered Organizational Strategic Brain for Sintetica, built on Claude Code + Claude Agent SDK.
Captures institutional memory, surfaces strategic patterns, and proactively drafts communications.
Owner: Natalia Usme. Timezone: Colombia (COT, UTC-5).

## Key Paths

| Purpose | Path |
|---------|------|
| Memory vault | `Sintetica/Memory/` |
| Daily logs | `Sintetica/Memory/daily/YYYY-MM-DD.md` |
| Active drafts | `Sintetica/Memory/drafts/active/` |
| Sent drafts (voice corpus) | `Sintetica/Memory/drafts/sent/` |
| Expired drafts | `Sintetica/Memory/drafts/expired/` |
| Memory domains | `Sintetica/Memory/{decisions,clients,trends,signals,hypotheses,...}/` |
| Hooks | `.claude/hooks/` |
| Scripts | `.claude/scripts/` |
| Integrations | `.claude/scripts/integrations/` |
| Skills | `.claude/skills/` |
| State / data | `.claude/data/` |
| Credentials | `.env` (never committed, never in vault) |
| PRD | `.agent/plans/second-brain-prd.md` |

## Memory Domains

| Domain | Path |
|--------|------|
| Projects | `Sintetica/Memory/projects/` |
| Decisions | `Sintetica/Memory/decisions/` |
| Clients | `Sintetica/Memory/clients/` |
| Research | `Sintetica/Memory/research/` |
| Capabilities | `Sintetica/Memory/capabilities/` |
| Team | `Sintetica/Memory/team/` |
| Lessons Learned | `Sintetica/Memory/lessons/` |
| Innovation | `Sintetica/Memory/innovation/` |
| Trend Observatory | `Sintetica/Memory/trends/` |
| Future Signals | `Sintetica/Memory/signals/` |
| Strategic Hypotheses | `Sintetica/Memory/hypotheses/` |
| Opportunities | `Sintetica/Memory/opportunities/` |
| Scenarios | `Sintetica/Memory/scenarios/` |

## Build Commands

```bash
# Phase 3 — memory indexing and search
python .claude/scripts/memory_index.py                          # index changed files
python .claude/scripts/memory_index.py --full                   # force full re-index
python .claude/scripts/memory_index.py --stats                  # show index stats
python .claude/scripts/memory_search.py "query"                 # hybrid search
python .claude/scripts/memory_search.py "query" --top-k 5       # limit results
python .claude/scripts/memory_search.py "query" --path-prefix clients   # scope to domain
python .claude/scripts/memory_search.py "query" --index-first   # index then search

# Phase 4 — integration queries
python .claude/scripts/query.py status                         # check all integration auth
python .claude/scripts/query.py gmail list                     # unread emails
python .claude/scripts/query.py gmail thread <id>              # email thread
python .claude/scripts/query.py github prs owner/repo          # open PRs + diff summary
python .claude/scripts/query.py github issues                  # assigned issues
python .claude/scripts/query.py slack unread                   # messages since 30min ago
python .claude/scripts/query.py slack summary                  # grouped digest by channel
python .claude/scripts/query.py obsidian domains               # list memory domains
python .claude/scripts/query.py obsidian search "query"        # keyword search vault
python .claude/scripts/query.py obsidian logs                  # recent daily logs

# Phase 6 — heartbeat and reflection
python .claude/scripts/heartbeat.py              # manual heartbeat run
python .claude/scripts/memory_reflect.py         # manual reflection run

# Phase 9 — deployment
python .claude/scripts/scheduler_setup.py install    # create + load macOS launchd plists
python .claude/scripts/scheduler_setup.py install --utc  # use UTC times (if system tz ≠ COT)
python .claude/scripts/scheduler_setup.py uninstall  # remove launchd plists
python .claude/scripts/scheduler_setup.py status     # show scheduler state + recent logs
python .claude/scripts/scheduler_setup.py systemd    # print Linux systemd unit files
bash .claude/scripts/sync_setup.sh                   # configure git-sync (run once per machine)

# Phase 8 — security tests
python .claude/scripts/security_test.py                      # full suite (48 tests)
python .claude/scripts/security_test.py --filter block-secrets   # one group
python .claude/scripts/security_test.py --verbose                # show all detail
```

## Conventions
- **Timezone:** Colombia (COT, UTC-5). All timestamps in COT.
- **Advisor mode:** Draft only. Never send, post, or delete autonomously.
- **No secrets in vault:** API tokens, OAuth credentials, and passwords live in `.env` only.
- **Checkbox syntax:** `- [x]` done, `- [ ]` pending, `- [~]` in progress
- **YAML frontmatter:** Required on all draft files (type, source_id, recipient, etc.)
- **PRD is source of truth:** Follow phases in order. Update this file after each phase.
- **All Agent SDK scripts** must set `CLAUDE_INVOKED_BY` env var to prevent hook recursion.

## Completed Phases

### Phase 1 — Foundation (2026-06-20)
Vault structure created at `Sintetica/Memory/`. Core files: SOUL.md, USER.md, MEMORY.md,
BOOTSTRAP.md, HEARTBEAT.md, HABITS.md, 13 domain subdirectories, drafts/ structure.
CLAUDE.md initialized. Run BOOTSTRAP.md in first session to complete onboarding.

### Phase 2 — Hooks (2026-06-20)
Lifecycle hooks wired in `.claude/settings.json`: SessionStart injects vault context,
PreCompact + SessionEnd spawn background `memory_flush.py`, PreToolUse runs `block-secrets.py`.
All Agent SDK scripts set `CLAUDE_INVOKED_BY` to prevent hook recursion.
`shared.py` provides file_lock, with_retry, atomic_write, DANGEROUS_BASH_PATTERNS (30+ patterns).
Note: `memory_flush.py` requires `pip install claude-agent-sdk` to enable intelligent summarization.

### Phase 3 — Memory Search (2026-06-20)
Hybrid RAG pipeline: FastEmbed (BAAI/bge-small-en-v1.5, 384-dim ONNX) + SQLite + sqlite-vec
(vector) + FTS5 (keyword). Hybrid merge via weighted RRF (0.7 vector + 0.3 keyword).
Incremental indexing via mtime tracking in `.claude/data/index-state.json`.
`--path-prefix` flag scopes search to any memory domain or drafts/sent for voice-matching.
Install: `pip install -r requirements.txt`

### Phase 4 — Integrations (2026-06-20)
Four integrations wired up with unified CLI at `.claude/scripts/query.py`.
- **Gmail**: OAuth2 setup → `.claude/credentials.json` + run `--auth` once
- **GitHub**: PAT via GITHUB_TOKEN in .env; PR diff summaries flag high-risk files
- **Slack**: Read-only (no chat:write scope). Bot Token + App Token (Socket Mode)
- **Obsidian**: Local file access, no API needed
`block-secrets.py` simplified to delegate all pattern matching to `shared.py`.
Next: Phase 5 (Skills).

### Phase 5 — Skills (2026-06-20)
Six strategic skills installed in `.claude/skills/`:
- `vault-structure` — memory domain map, naming conventions, filing guide
- `strategic-capture` — rapid capture into correct domain; `capture.py` CLI
- `decision-journal` — decision capture with full rationale; decision-template
- `trend-observatory` — signal vs trend lifecycle; signal taxonomy for Sintetica's sectors
- `client-intelligence` — client profile structure, meeting prep, attribution rules
- `future-scenarios` — 2x2 scenario method; single-scenario template; scenario-to-signal links
Invoke via `/skill-name` in any session, or auto-triggered by context phrases.
Next: Phase 6 (Heartbeat + Reflection).

### Phase 6 — Proactive Systems (2026-06-20)
5-stage heartbeat pipeline: gather → state diff → pre-flight guardrail → Agent SDK reasoning → notify.
`build_snapshot()` / `diff_snapshot()` in heartbeat.py prevent notification fatigue.
Draft lifecycle: active/ → sent/ (on reply detected) | expired/ (after 24h).
Voice-matching via `memory_search.py --path-prefix drafts/sent` for draft generation.
Daily reflection at 8 AM COT promotes daily log items to MEMORY.md.
`soul-write-protect.py` hook blocks reflection agent from editing SOUL.md directly.
HABITS.md: 3 pillars with auto-detection rules; heartbeat archives daily and nudges late-day.
`sanitize.py`: 3-layer defense (pattern detection + HTML escape + XML trust boundary).
Set GITHUB_REPOS=owner/repo,owner/repo2 in .env for PR monitoring.
Next: Phase 8 (Security Hardening).

### Phase 8 — Security Hardening (2026-06-20)
`security_test.py` validation suite — 48 tests, all passing.
Coverage: block-secrets (Read/Write/Grep on sensitive paths), bash guardrails (destructive ops,
credential reads, package installs, privilege escalation, git destructive, subshell/backtick/binary-
path bypasses), soul-write-protect (reflection cannot edit SOUL.md; interactive session can),
sanitize (injection detection, HTML escaping, trust-boundary wrapping), heartbeat state diffing
(new-only notifications, first-run all-new), pattern/path coverage (21 bash + 15 path samples),
and recursion prevention (CLAUDE_INVOKED_BY blocks all 3 lifecycle hooks).
Run: `python .claude/scripts/security_test.py`
Next: Phase 9 (Deployment — launchd/systemd schedulers, vault sync).

### Phase 9 — Deployment (2026-06-20)
`scheduler_setup.py` generates macOS launchd plists + Linux systemd units.
Heartbeat: every 30 min, 7 AM–8 PM COT (27 StartCalendarInterval slots). `--utc` flag
for systems running UTC instead of America/Bogota.
Reflection: daily at 8 AM COT (13:00 UTC).
Logs: `.claude/logs/heartbeat.log`, `.claude/logs/reflection.log`.
`git-merge-concat` merge driver handles concurrent writes to daily logs across machines.
`.gitattributes` registers concat-both for `Sintetica/Memory/daily/*.md`.
`sync_setup.sh` registers the merge driver, checks git-sync install, and verifies SSH keys.
Run `sync_setup.sh` on EACH machine before first vault sync.
VPS: copy `.env` manually over SSH — it is never synced via git.

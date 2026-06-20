---
name: vault-structure
description: Reference for how the Sintetica memory vault is organized. Use when creating, filing, or finding notes — to put things in the right domain and follow naming conventions.
---

# Vault Structure — Sintetica Memory Organization

The vault lives at `Sintetica/Memory/`. Everything is a markdown file. Obsidian opens `~/Sintetica/` as the vault root.

## Core Files (root of Memory/)

| File | Purpose | Loaded every session? |
|------|---------|----------------------|
| `SOUL.md` | Agent identity, behavioral rules, Sintetica values | Yes (via hook) |
| `USER.md` | Natalia's profile, integration config, team roster | Yes (via hook) |
| `MEMORY.md` | Live key decisions, lessons, active projects | Yes (via hook) |
| `HEARTBEAT.md` | What the heartbeat monitors | No |
| `HABITS.md` | Daily pillar tracker | No |
| `BOOTSTRAP.md` | First-run onboarding (deletes itself after) | Only if present |

**MEMORY.md rule:** Keep it under 300 lines. It loads into every session — every entry costs tokens. Full detail lives in domain folders and daily logs.

## Memory Domains

| Domain | Path | What belongs here |
|--------|------|-------------------|
| Projects | `projects/` | Engagement notes, status, milestones, deliverables |
| Decisions | `decisions/` | Strategic decisions + rationale + outcomes |
| Clients | `clients/` | Client intelligence, preferences, relationship history |
| Research | `research/` | Synthesis notes, literature, key findings |
| Capabilities | `capabilities/` | Team skills, tools, methodologies, frameworks |
| Team | `team/` | Who does what, working styles, preferences, timezones |
| Lessons | `lessons/` | What worked, what didn't, transferable lessons |
| Innovation | `innovation/` | Ideas, experiments, opportunities explored |
| Trends | `trends/` | Emerging signals, industry shifts, disruptions |
| Signals | `signals/` | Weak signals, early indicators, anomalies |
| Hypotheses | `hypotheses/` | Strategic bets tracked with evidence for/against |
| Opportunities | `opportunities/` | Identified opportunities, pipeline, status |
| Scenarios | `scenarios/` | Future scenarios, implications, trigger conditions |

## Transient Folders

| Path | Purpose |
|------|---------|
| `daily/YYYY-MM-DD.md` | Append-only session and heartbeat logs |
| `drafts/active/` | Email/message drafts awaiting review |
| `drafts/sent/` | Replied drafts (voice-matching corpus) |
| `drafts/expired/` | Drafts >24h with no action |

## File Naming Conventions

- **Decisions:** `YYYY-MM-DD-short-slug.md` (e.g., `2026-06-20-switch-to-sqlite.md`)
- **Clients:** `client-name.md` (lowercase, hyphenated)
- **Trends / Signals:** `YYYY-MM-DD-signal-title.md`
- **Research:** descriptive slug, no date needed
- **Scenarios:** `scenario-name.md`
- **Hypotheses:** `hyp-short-description.md`

## YAML Frontmatter

All domain files should include frontmatter:

```yaml
---
title: "Human-readable title"
date: 2026-06-20
domain: decisions          # matches the folder name
status: active             # active | archived | superseded | validated
tags: [strategy, client-x]
---
```

Drafts additionally require: `type`, `source_id`, `recipient`, `subject`, `created`, `status`.

## Where to put things (quick guide)

- "We decided to X because Y" → `decisions/`
- "Client said they prefer async communication" → `clients/client-name.md`
- "I noticed a trend in AI regulation" → `trends/` or `signals/` (weak signal → signals, confirmed pattern → trends)
- "This project taught us that..." → `lessons/`
- "Here's an opportunity in sector X" → `opportunities/`
- "What if X happens in 3 years?" → `scenarios/`
- "I think X will be true, watching for evidence" → `hypotheses/`

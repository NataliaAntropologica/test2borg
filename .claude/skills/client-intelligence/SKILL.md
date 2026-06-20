---
name: client-intelligence
description: Capture and retrieve client intelligence. Use when discussing a client, preparing for a meeting, writing a proposal, or when Natalia shares something she learned about a client.
---

# Client Intelligence

Client memory is Sintetica's most sensitive and valuable asset. Every engagement builds on what came before.

## When to trigger

- "The client said...", "In the meeting with X, I learned..."
- "Prepare my context for [client name]"
- "What do we know about [client]?"
- "Create a client profile for [organization]"
- After any client meeting, call, or email exchange

## Capture workflow

**New client:**
```
python .claude/skills/strategic-capture/scripts/capture.py clients "<Client Organization Name>"
```

**Add to existing client:**
Search and open the client file, append to the relevant section, then re-index:
```
python .claude/scripts/memory_search.py "<client name>" --path-prefix clients
```

## Client file structure

```yaml
---
title: "Client Organization Name"
date: YYYY-MM-DD        # first engagement date
domain: clients
status: active          # active | past | prospect | paused
tags: [industry, sector]
---
```

**Sections:**
- **Overview** — one paragraph: what they do, size, strategic context
- **Key Contacts** — name, role, decision-making authority, communication style
- **Preferences & Working Style** — async vs sync, formality level, what impresses them
- **Active Engagements** — current projects, scope, status
- **Intelligence & Notes** — timestamped observations, quotes, strategic context
- **Relationship History** — past engagements, outcomes, lessons

## Capturing client intelligence

Always attribute and timestamp observations:

```markdown
## Intelligence & Notes

**2026-06-20:** Mentioned in kickoff that they're under pressure from board to show
AI ROI by Q3. Decision-maker is CFO (Maria Santos), not the CTO we've been talking to.

**2026-05-15:** Prefers 1-page executive summaries over decks. Said explicitly:
"Give me the recommendation first, then the evidence."
```

## Privacy & confidentiality rules

- Client files are never synced to public repos
- Do not include competitor intelligence shared in confidence
- Do not record personal information beyond professional context
- Mark sensitive sections with `> CONFIDENTIAL:` blockquote

## Retrieval

```bash
# Full client context before a meeting
python .claude/scripts/memory_search.py "[client name]" --path-prefix clients

# Find all intelligence about a sector
python .claude/scripts/memory_search.py "financial services clients"

# Read a specific client file
python .claude/scripts/query.py obsidian read clients/client-name.md
```

## Meeting prep workflow

When Natalia has a client meeting:
1. Search client file: `memory_search.py "[client]" --path-prefix clients`
2. Search recent projects: `memory_search.py "[client] project" --path-prefix projects`
3. Search decisions: `memory_search.py "[client] decision" --path-prefix decisions`
4. Synthesize: what context is most relevant? What open questions exist?
5. After meeting: capture new intelligence back into the client file

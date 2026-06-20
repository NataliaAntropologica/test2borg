---
name: strategic-capture
description: Capture strategic intelligence into the right memory domain. Use when Natalia says "capture this", "remember that", "log this", or when the conversation contains a decision, lesson, insight, signal, or client fact worth preserving.
---

# Strategic Capture

Rapidly capture intelligence into the correct domain of the Sintetica vault.

## When to trigger

Auto-trigger on phrases like:
- "capture this", "remember that", "log this", "save this"
- "we decided to...", "the client said...", "I noticed that..."
- "lesson learned:", "key insight:", "important:"
- "I think X will happen" (→ hypothesis), "opportunity in..." (→ opportunity)

## Capture workflow

1. **Identify the domain** — use the routing guide below
2. **Draft the entry** — use the template for that domain
3. **Show Natalia** the draft before writing
4. **Write** with `python .claude/skills/strategic-capture/scripts/capture.py <domain> "<title>"`
5. **Index** run `python .claude/scripts/memory_index.py` (or it runs on next session)

## Domain routing guide

| Content type | Domain | Script flag |
|-------------|--------|-------------|
| Strategic decision + rationale | `decisions/` | `--domain decisions` |
| Client fact, preference, intel | `clients/` | `--domain clients` |
| Research finding or synthesis | `research/` | `--domain research` |
| Emerging trend (confirmed pattern) | `trends/` | `--domain trends` |
| Weak signal / early indicator | `signals/` | `--domain signals` |
| Project milestone or status | `projects/` | `--domain projects` |
| Lesson learned | `lessons/` | `--domain lessons` |
| Strategic hypothesis | `hypotheses/` | `--domain hypotheses` |
| Opportunity identified | `opportunities/` | `--domain opportunities` |
| Future scenario | `scenarios/` | `--domain scenarios` |
| Team member insight | `team/` | `--domain team` |
| Capability / method | `capabilities/` | `--domain capabilities` |
| Innovation / idea | `innovation/` | `--domain innovation` |

## Quick capture format (for daily log)

When speed matters, append to today's log first and promote later:

```
python .claude/scripts/memory_index.py  # re-index after capture
```

Append pattern:
```markdown
- HH:MM COT — [DOMAIN] Title: one-sentence summary. #tag
```

## Entry quality rules

- **Decisions:** Always include the rationale. A decision without a "because" is useless in 6 months.
- **Clients:** Attribute facts. "Preferred async communication (said in kickoff 2026-06-20)."
- **Signals:** Include the source and why it's notable. Strength: weak / emerging / confirmed.
- **Lessons:** Make it transferable. "On projects with X characteristic, do Y."
- **Hypotheses:** State the falsification condition. "This hypothesis is wrong if Z."

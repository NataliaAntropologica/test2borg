---
name: trend-observatory
description: Capture, classify, and track emerging trends and weak signals. Use when Natalia mentions a pattern she's noticing, an industry shift, a regulatory change, or asks to scan for signals on a topic.
---

# Trend Observatory

Sintetica's foresight practice depends on catching signals before they become obvious.
This skill handles the full signal lifecycle: capture → classify → track → synthesize.

## Signal vs. Trend distinction

| Concept | Description | Folder |
|---------|-------------|--------|
| **Signal** | Single observation, weak or ambiguous evidence, early indicator | `signals/` |
| **Trend** | Confirmed pattern with multiple converging data points | `trends/` |

When in doubt, start as a signal. Promote to trend when you see 3+ independent data points.

## Capture workflow

**New signal:**
```
python .claude/skills/strategic-capture/scripts/capture.py signals "<signal title>"
```

**New trend:**
```
python .claude/skills/strategic-capture/scripts/capture.py trends "<trend title>"
```

## Signal entry format

```yaml
---
title: "Brief signal description"
date: 2026-06-20
domain: signals
status: active
strength: weak        # weak | emerging | confirmed
horizon: 1-3yr        # 0-1yr | 1-3yr | 3-5yr | 5yr+
tags: [AI, latam, policy]
---
```

Body: Source → What was observed → Why it's notable → What to watch for

## Trend entry format

```yaml
---
title: "Trend name"
date: 2026-06-20
domain: trends
status: active
horizon: 1-3yr
maturity: emerging    # emerging | mainstream | declining
tags: []
---
```

Body: Summary → Evidence (bullet list of data points) → Implications for Sintetica → Sources

## Signal taxonomy

See `references/signal-taxonomy.md` for the full taxonomy of signal types.

Quick reference:
- **Regulatory** — new laws, policy proposals, enforcement patterns
- **Technological** — new tools, platforms, capabilities going mainstream
- **Behavioral** — shifts in how clients, users, or markets behave
- **Economic** — pricing, funding, business model shifts
- **Social** — cultural changes, values shifts, demographic movements
- **Competitive** — new entrants, exits, pivots in adjacent markets

## Scanning and synthesis

```bash
# Find signals on a topic
python .claude/scripts/memory_search.py "AI regulation Latin America" --path-prefix signals

# List all active trends
python .claude/scripts/query.py obsidian list trends

# Find related signals to promote to trend
python .claude/scripts/memory_search.py "design futures" --path-prefix signals --top-k 10
```

## Promoting a signal to a trend

When a signal gains 3+ corroborating data points from independent sources:
1. Create a new trend entry with `capture.py trends "<title>"`
2. Link the original signals in the Evidence section
3. Update the signal files' status to `superseded` and add `see: trends/trend-title.md`

## Questions this skill helps answer

- What emerging signals should we monitor? (`memory_search.py "signals" --path-prefix signals`)
- What trends are most relevant to [client industry]? (`memory_search.py "[industry] trends"`)
- What signals are gaining strength? (scan `signals/` by date, filter `strength: emerging`)

---
name: decision-journal
description: Capture and track strategic decisions with full rationale. Use when Natalia says "we decided", "I chose", "going with X", or asks to log or review a decision.
---

# Decision Journal

Decisions without rationale are useless in six months. This skill captures the full context.

## When to trigger

- "We decided to...", "I've chosen to...", "Going with X over Y"
- "Log this decision", "Create a decision entry"
- "Why did we decide X?" (→ search decisions/)
- "Review recent decisions" (→ list decisions/)

## Capture workflow

1. Ask: **What was the decision?** (one sentence)
2. Ask: **What context drove it?** (situation, constraints, timing)
3. Ask: **Why this over alternatives?** (the rationale — most important part)
4. Ask: **What outcomes do you expect?** (success criteria, review date)
5. Create the file:
   ```
   python .claude/skills/strategic-capture/scripts/capture.py decisions "<title>"
   ```
6. Fill in the generated template, then index:
   ```
   python .claude/scripts/memory_index.py
   ```

## Decision entry format

```yaml
---
title: "Short decision title"
date: 2026-06-20
domain: decisions
status: active       # active | superseded | validated | reversed
confidence: high     # high | medium | low
stakeholders: [Natalia]
tags: [strategy, client-x]
---
```

**Body sections:**
- **Context** — what situation created the need to decide
- **Decision** — the choice made, in one clear sentence
- **Rationale** — why this option over alternatives (most important)
- **Alternatives Considered** — what else was on the table and why rejected
- **Expected Outcomes** — what success looks like; measurable if possible
- **Review Date** — when to check if this decision held up

## Reviewing decisions

```bash
# Find decisions by topic
python .claude/scripts/memory_search.py "client communication decisions" --path-prefix decisions

# List all decision files
python .claude/scripts/query.py obsidian list decisions
```

## Decision quality checklist

Before filing, verify:
- [ ] Rationale is written (not just "it seemed better")
- [ ] At least one alternative is named and explained
- [ ] A review date or trigger condition is set
- [ ] Confidence level is honest
- [ ] Stakeholders who need to know are listed

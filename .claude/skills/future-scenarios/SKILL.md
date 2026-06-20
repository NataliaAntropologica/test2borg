---
name: future-scenarios
description: Build and maintain future scenarios for strategic planning. Use when Natalia asks about futures, wants to prepare clients for uncertainty, or says "what if X happens".
---

# Future Scenarios

Scenarios are coherent narratives about possible futures — not predictions, but tools for strategic preparation.

## When to trigger

- "What if X happens?", "What should our clients prepare for?"
- "Build a scenario for [topic]", "What are the plausible futures for [domain]?"
- "Stress-test our strategy against future scenarios"
- "What future scenarios should clients be preparing for?" (success question #8)

## Scenario development workflow

### Step 1 — Identify the focal question
What decision or strategy is this scenario set designed to inform?
_e.g., "What capabilities should Sintetica build for the next 3 years?"_

### Step 2 — Identify key drivers and uncertainties
2-3 critical factors that are both **important** and **uncertain**.
Drivers that are important but predictable go in assumptions, not axes.

### Step 3 — Define axes (for 2x2 matrix)
Pick 2 driving uncertainties, put them on axes.
Label each pole. This creates 4 scenario quadrants.

### Step 4 — Name and narrate each scenario
Each scenario gets:
- A memorable name (not "Scenario A")
- A 1-paragraph narrative of what this world looks like
- Key implications for Sintetica or the client
- Strategic response

### Step 5 — Create the file
```
python .claude/skills/strategic-capture/scripts/capture.py scenarios "<scenario-set-name>"
```

## Scenario file format

```yaml
---
title: "Scenario set title"
date: 2026-06-20
domain: scenarios
status: active
focal_question: "What capabilities will Sintetica need in 3 years?"
horizon: 3yr
tags: [strategy, foresight]
---
```

See `references/scenario-template.md` for the full structure.

## Quick single-scenario format

For a single "what if" scenario:

```yaml
---
title: "What if AI consultants commoditize strategy delivery"
date: 2026-06-20
domain: scenarios
status: active
horizon: 1-3yr
probability: medium     # low | medium | high (avoid false precision)
tags: []
---
```

**Body:** Drivers → Trigger conditions → World description → Implications → Strategic response

## Connecting scenarios to the vault

After building scenarios, link them to:
- **Signals:** which current signals point toward each scenario?
- **Hypotheses:** which of your hypotheses would this scenario validate?
- **Opportunities:** what opportunities open up or close in each scenario?

```bash
# Find signals relevant to a scenario
python .claude/scripts/memory_search.py "AI commoditization consulting" --path-prefix signals

# Find related hypotheses
python .claude/scripts/memory_search.py "AI strategy consulting" --path-prefix hypotheses
```

## Client scenario work

When building scenarios FOR a client (not for Sintetica itself):
- File in `scenarios/` but tag with `client: client-name`
- Keep client-specific scenarios out of Sintetica's internal strategic files
- Cross-reference in the client file: `clients/client-name.md`

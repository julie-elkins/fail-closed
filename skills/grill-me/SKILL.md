---
name: grill-me
description: >-
  Interrogate the request before building anything. Use when the user invokes it explicitly,
  or when a task is large, ambiguous or expensive enough that building the wrong thing costs
  more than a round of questions — a new MCP server, a workflow design, a document with an
  external audience, anything touching embargoed content or a legal/sign-off gate. It
  produces a short written brief the user confirms before any code or prose is written. It
  does NOT replace judgement: routine calls stay yours, and this skill is a failure if it
  asks questions you could have answered by reading the repo.
---

# Grill me

Ask the questions whose **different answers would change what you build**. Then write the
brief. Then stop and wait.

## The rule that makes this worth invoking

**Read first, ask second.** Before writing a single question, spend the effort to answer it
yourself: read the repo, the CLAUDE.md, any plan file the project keeps, the git log, the
existing tests. A question you could have answered by reading is a question that costs the
user time to tell you something they already wrote down — and it trains them to stop
invoking this.

Then ask only what survives that pass.

## How many, and which

**Target 4–8 questions. Never 15.** The count is not the point; coverage of the *decisions*
is. A question earns its place only if you can name two answers that lead to materially
different work.

Cover these axes, and drop any that the reading already settled:

| Axis | The question behind it |
|---|---|
| **Scope boundary** | What is explicitly NOT in this? Where does it stop? |
| **Audience** | Who reads or calls this — a person, an agent, a reviewer, an external party? |
| **Done** | What has to be true for this to be finished, in a form you could check? |
| **Constraints** | What must not change? What's load-bearing that I'd otherwise "tidy"? |
| **Prior art** | Which existing thing is this modelled on, or deliberately unlike? |
| **Failure** | What's the worst plausible wrong output, and who would it mislead? |
| **Gates** | Whose sign-off does this need, and does that gate the build or only the release? |

The **Gates** row is the one most often skipped and most expensive to skip. Work in this
role is regularly blocked on a named person rather than on engineering.

## Ask them well

- **Use `AskUserQuestion` when options are enumerable**, one question per decision, with a
  recommendation first and marked as such. Use prose only for genuinely open answers.
- **Batch them.** One round of questions, not a conversation. If you find yourself needing a
  second round, you under-read in the first place.
- **Never ask what you can assume safely.** State the assumption in the brief instead and
  let the user correct it. An assumption they can veto costs one word; a question costs a
  paragraph.

## Then write the brief

Short, and structured so disagreement is cheap:

```
## Building
<one sentence>

## Not building
<the boundary — this is the section that prevents scope drift>

## Assuming
<each assumption on its own line, so any one can be struck>

## Done when
<checkable conditions>

## Blocked on
<people, approvals, access — or "nothing">
```

**Then stop.** Do not begin work in the same turn as the brief. The whole value of this
skill is the pause, and a brief followed immediately by 400 lines of code has skipped it.

## What this skill cannot do

It cannot tell you whether the answers are *right* — the user may be wrong about their own
requirements, and if the brief contains something that won't work, say so in a sentence and
continue rather than building it silently.

It also cannot substitute for the domain standards. If the thing being built is an MCP
server or an orchestrator, load `/mcp-server-standard` or `/orchestration-standard` as
well, and if it is Python in one of these repos, `/coding-standards` — several of their
points are design-time decisions the brief should already reflect, and all three are
expensive to retrofit.

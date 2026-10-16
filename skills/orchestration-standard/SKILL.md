---
name: orchestration-standard
description: >-
  The 12-point house standard for multi-agent and multi-step agentic workflows — the
  layer that CALLS the tools, as opposed to the tools themselves. Apply it by default
  when designing, building or reviewing an orchestrator, a worker agent, a skill that
  drives an MCP server through a plan-decide loop, or any workflow that fans out and
  joins. Do not offer it as an option. Use it BEFORE writing any agent prose: points 3, 7
  and 8 determine what each step reads and writes and are expensive to retrofit. It tells
  you how to decompose and where the failures hide; it does NOT verify that a given
  pipeline is correct, and it cannot tell you whether a decomposition matches the domain.
  The companion standard for the TOOLS is `mcp-server-standard`.
---

# Multi-agent orchestration house standard

The failure this targets is the orchestration-level twin of the MCP one: **a pipeline
that ran four steps, had two fail, and presents a confident final report as if all four
succeeded.** Points 4, 11 and 12 are the load-bearing three.

Worked example, from a document-screening server — the MCP server holds the four
screening stages as tools, and a `.claude/skills/<name>/SKILL.md` is the orchestrator
that plans the per-item loop, decides on early exit, and assembles the report. Without a
checkout the points still stand: each names what the wrong decomposition cost.

## The twelve points

1. **Clear role boundaries.** One responsibility per agent. If it can't be described in
   one sentence, it's doing too much. Decompose by capability, not convenience.
   ✅ "runs DIF on a response matrix"
   ❌ "does item stats, DIF, standard setting, and writes the report".
2. **Orchestrator + workers.** One orchestrator plans, delegates and assembles; workers
   execute. The orchestrator decides WHAT and in what order; workers decide HOW. Workers
   never make strategic decisions.
3. **Explicit contracts between agents.** Typed input and output per worker, like an MCP
   tool schema. Vague handoffs are the #1 source of failures, and they fail SILENTLY when
   an output shape changes.
4. **Fail fast, don't cascade garbage.** If a worker refuses or returns low-confidence
   output, the orchestrator stops and reports rather than feeding it downstream. This is
   "refusal is a result" (MCP standard #6) raised to the orchestration level.
5. **Minimize agent-to-agent chatter.** Fat messages, few hops: full context out,
   complete result back. If two agents need to go back and forth, they should probably be
   one agent.
6. **Parallel when independent, sequential when dependent.** Map the dependency graph
   FIRST; fan out what only needs the shared input, join before anything that needs all
   of it.
7. **Shared state via files, not memory.** Agents don't share memory. Pass data through
   structured files in a workspace (`inputs/`, `intermediate/`, `outputs/`), so any
   intermediate can be inspected to find where it went wrong.
8. **Idempotent workers.** Same input, same output, every time. No hidden state. That is
   what makes retries safe, parallel runs safe, and single-worker debugging possible.
9. **Human-in-the-loop checkpoints.** High-stakes workflows get explicit approval gates
   before consequential steps — auto up to "present findings", pause, then auto again
   only after approval. Put the gate BEFORE the expensive fan-out, not after it.
10. **Observability — log every hop**, both directions:
    `Orchestrator → DIF Agent: 65 items, 2 groups, method=mantel_haenszel` and
    `DIF Agent → Orchestrator: 3 items flagged C`. When a 5-agent pipeline is wrong you
    need to know which agent broke and what it saw.
11. **Graceful degradation.** One worker failing still yields value from the rest: report
    partial results with the failed section explicitly marked unavailable, not
    "Error. Pipeline failed."
12. **Test the orchestration, not just the workers.** Integration tests that the
    orchestrator calls workers in the right order, that data flows between them, that a
    worker failure is handled, and that the final output assembles correctly.

## Resolving 4 against 11

Fail fast and degrade gracefully pull in opposite directions. Resolve by **where the
failure sits relative to the data flow**:

- **Upstream failure → stop.** Later steps would be computing on garbage.
- **Lateral failure → continue**, and mark that section unavailable by name.

A pipeline that cannot tell those apart has not mapped its dependency graph.

## Anti-patterns, and why each fails

| Anti-pattern | Why it fails |
|---|---|
| God orchestrator | can't parallelize, test or reuse |
| Chatty agents | slow, fragile, undebuggable |
| Implicit contracts | silent failure on shape change |
| Optimistic chaining | garbage cascades into the final report |
| Shared mutable state | race conditions |
| Over-decomposition | coordination overhead exceeds the task — 15 agents for a simple job |

## How to apply

Design the **dependency graph** and the **worker contracts** before writing any agent
prose. Points 3, 7 and 8 are hard to retrofit because they determine what each step reads
and writes.

Draw the graph explicitly in the skill or design doc, marking the sequential edges, the
fan-out points, the join, and every human gate — the way a good orchestrator skill does. A
graph that exists only in the orchestrator's prose is one nobody can check against the
code.

When reviewing an existing workflow, report per point: satisfied, breached, or not
checkable from here. An absent signal is not a satisfied point.

**This standard stops at the decomposition.** The file each worker becomes has its own
failure modes, and they are silent ones: a `description` that decides whether the agent is
ever selected and for what, a tool list that is the only real containment boundary, and an
output shape that either can or cannot distinguish *unchecked* from *clean*. A correct
dependency graph implemented as four vague prompts is four agents guessing. `agent-authoring`
covers that file.

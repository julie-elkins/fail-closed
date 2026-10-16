# Agent definitions — where they go and what the template assumes

`worker-agent.md.template` is one shape: **a worker in a fan-out.** It is the shape that has
been exercised, so it is the one shipped. The reasoning behind every section is in
`/agent-authoring`; this file is only the placement and the two traps that are about files
rather than content.

## Placement

| Path | Scope | Use for |
|---|---|---|
| `.claude/agents/<name>.md` in a repo | that repo only | any agent whose body names that repo's paths, schemas or conventions |
| `~/.claude/agents/<name>.md` | every session | an agent that is genuinely repo-independent |

Same name in both, the project one wins.

**Default to the repo.** A house-wide agent that references a path only one checkout has does
nothing on anyone else's machine and does not announce that — the same failure as a skill
carrying an absolute home directory. The kit's own invariant 3 exists for that reason.

`install.sh` does not place anything under `agents/`, and that is deliberate: which repo an
agent belongs to is a decision, and a worker copied into `~/.claude/agents/` by an installer is
a worker nobody chose the scope of.

## Fill it in, then grep for what you left

Fill-ins are `<ANGLE BRACKETS>`, uniformly, so one command finds every unreplaced one:

```
grep -n '<[A-Z]' .claude/agents/<name>.md
```

That has to come back empty before the agent is used. A half-filled agent definition does not
error — it runs, with the bracketed text read as instructions.

## The two fields to get right before the body

- **`name` must match the filename stem.** It is the address an orchestrator uses.
- **`tools` must list everything the body instructs and nothing else.** Omitting the field
  inherits the whole session's tool set, which is a large grant made by accident. A tool the
  body needs and the list omits fails in a way that reads like a bad prompt.

## What this template is not

- **Not an orchestrator.** An orchestrator is a skill, not an agent file — it needs the
  conversation's context, which a subagent cannot see. `/orchestration-standard` covers the
  layer; `/agent-authoring` covers choosing between the two.
- **Not a shape for an agent that writes outward.** Every section here assumes the worker
  writes one file into a workspace and sends nothing anywhere. An agent that posts is a
  different argument and should be made separately.

---
name: agent-authoring
description: >-
  How to write the agent definition file itself — where it lives, the frontmatter, the
  description field as routing logic, the tool list as a containment boundary, and the five
  sections a worker's body needs. Also covers the prior question: whether the job wants a
  subagent at all rather than a skill, an MCP tool or an orchestrator. Use before creating
  anything under `.claude/agents/`, and when a fan-out of one agent comes back inconsistent.
  It governs the FILE; `orchestration-standard` governs the decomposition — read that one
  first if you do not yet know how many agents there are. It does NOT judge whether a
  worker's domain verdicts are correct, and it names no runner flags beyond frontmatter.
---

# Agent authoring

`/orchestration-standard` tells you how many agents there are and what flows between them.
It says nothing about the file a worker turns into, and that file is where the decomposition
is either enforced or quietly lost. A correct dependency graph implemented as four vague
prompts is four agents guessing.

This skill covers one artifact: an agent definition under `.claude/agents/`. It is written
from one worker in production — a per-item question reviewer, fanned out twelve and
forty at a time — so the measurements are one instrument's, not a policy.

## First: is a subagent the right mechanism

Four surfaces, and the wrong choice is cheap to make and expensive to unwind:

- **A skill** — prose loaded into *this* conversation, applied with the full history in
  context.
- **A subagent** — a fresh context with its own tool allowlist, returning one result.
- **An MCP tool** — deterministic code behind a schema, for an operation that is the same
  every time and where a wrong answer should be a refusal rather than a judgement.
  `/mcp-server-standard`.
- **An orchestrator** — the plan-decide loop that calls the other three.
  `/orchestration-standard`.

**The test that separates the first two is not difficulty, it is context: does the job need
what has already been said?** If yes, a skill — a subagent cannot see it. If the
conversation is noise to the job, a subagent, and the fresh context is the feature rather
than a limitation to work around.

**The under-used reason to delegate is context economics, and it has nothing to do with
parallelism.** A subagent's tool output never enters the parent's context; only its final
message does. So a worker that loads a four-thousand-record store, calls five screening tools
and returns one fifteen-field verdict costs the parent the verdict. Run one, sequentially,
and the delegation has already paid. Reaching for a subagent only when you want N at once
means paying full context for every large intermediate you did not have to read.

## Where the file goes

- `~/.claude/agents/<name>.md` — every session, regardless of directory.
- `.claude/agents/<name>.md` in a repository — that repository only, and the right home for
  an agent that names that repo's paths, schemas or conventions.
- Same name in both: the project one wins.

**A house-wide agent that references a path only one checkout has is an agent that does
nothing on anyone else's machine, and it does not announce that.** Same failure class as a
skill carrying an absolute home directory. If the body names a repo, the file belongs in
that repo.

## Frontmatter: four fields, each a decision

```
---
name: <kebab-case-name>
description: >-
  <routing logic; see below>
tools: Read, Write, <the exact tools this agent needs and nothing else>
model: <only when the stakes differ from the session's; otherwise omit and inherit>
---
```

`name` matches the filename stem and is the address an orchestrator uses. `model` omitted
inherits, which is almost always right — set it only when this job is deliberately cheaper
or deliberately more careful than the session around it. If the agent edits files and you
want it working on an isolated copy of the tree, that is an isolation setting on the call
rather than something to fake inside the body.

## The `description` is routing logic, not a summary

**It is the only text read before the agent is chosen, and both ways of getting it wrong are
silent.** A vague description produces an agent that is never picked — indistinguishable
from an agent nobody needed. An over-broad one produces an agent that answers questions it
was not built for, confidently, in a fresh context with none of the caveats.

Four things, in this order:

1. **What it does, with the cardinality.** *"Reviews exactly ONE question and returns a
   typed verdict."* The word **one** is load-bearing; without it the parent hands it the
   batch.
2. **When to use it, naming the orchestrator.** *"...the `<orchestrator-name>` skill is the
   orchestrator that plans the loop and assembles the report; this is the worker."* A worker
   whose description does not name its orchestrator gets invoked directly.
3. **What to hand it.** *"Give it a store path, one item_id, that item's meta record and a
   digest of the reference document."* This is where the contract starts being enforced.
4. **What it does not decide.** *"It decides HOW to review one item; it never decides what
   the batch means."*

Then one containment line wherever the data class demands it: *"Give it PATHS, not pasted
item content."* Put it in the description and not only in the body, because the description
is what a caller reads while deciding what to pass.

Write it for a reader choosing between this agent and three others, not for one who has
already chosen.

## `tools:` is a containment boundary

Omitting it inherits everything the session has, which on a machine with fifteen MCP servers
is a very large grant made by accident. List the tools, and the list becomes part of the
design: an agent holding `Read`, `Write` and five domain tools **cannot** post to Slack,
cannot open a ticket and cannot reach a second data source. That is enforced rather than
remembered.

Two rules:

- **The allowlist must cover everything the body instructs.** An agent told to read its own
  meta record, without `Read`, fails in a way that reads like a bad prompt rather than a
  missing grant.
- **A worker gets no outward-facing tool.** It writes one file into a workspace
  (orchestration point 7) and nothing else — no Slack, no ticketing, no email. **Say so in
  the body as well**, because an absent tool is not an instruction the agent can reason
  about, and a future edit that adds the tool will not also add the judgement.

Worked example on an organisation's most restricted content class. The per-item reviewer holds `Read`,
`Write`, six screening tools from one MCP server and two documentation-search tools. No
`Bash`, no `Edit`, no messaging, no ticketing. It is handed paths rather than content, it
writes exactly one JSON file into a named workspace, and its last section states that it
sends nothing anywhere. **Three independent layers — the tool list, the input convention and
the body — and there are three because each one alone fails without a sound.**

## The five sections a worker's body needs

The body is the agent's entire system prompt. Second person, and in this order, because this
is the order someone reads it in when a run has gone wrong at 6pm:

1. **What you are given.** Field by field, with its type and where it comes from. And what to
   do when one is missing: **stop and name which one.** A worker that substitutes a
   neighbouring input rather than stopping produces a plausible answer to a different
   question, which is the most expensive output available.
2. **How you do the job.** Including any order that is load-bearing — and say *why* it is
   load-bearing. A rule with its reason attached survives the next edit; a bare rule gets
   optimised away by someone who cannot see what it was for.
3. **What is not yours to decide.** In a well-behaved worker this is the longest section.
   Enumerate every place it might reasonably overreach: deciding what the batch means,
   overriding a prior human note, reading a signal as a defect, letting a tool's routing
   recommendation outvote its own criteria.
4. **What you return.** A literal JSON block with every field present. This is the typed
   contract of orchestration point 3, and prose is not a substitute for it — a shape
   described in sentences drifts between workers in the same batch.
5. **Containment.** What it may write, where, and what must not appear in its final message.

## Absence has to be a value the worker can return

The failure mode from `/security-triage`, in its agent form: **a worker that cannot say "I
did not check this" reports an unchecked thing as a clean one, and nothing downstream can
tell the difference.** Three requirements follow:

- Every stage carries `skipped` and `refused` as values distinct from `pass`. Never pass
  `pass` for a stage that did not run.
- The output has a dedicated limitations array, and the body says **an empty array is a
  claim.**
- **A limitation written in prose is not counted; the field is.** Measured 2026-09-14 across
  twelve parallel workers on one batch: three of twelve stated an identical limitation inside
  a criterion note and then returned an empty limitations array. Seven put it in the field.
  That is roughly a 30% silent drop rate on the same gap, biased in the expensive direction,
  because an unreported limitation reads downstream as a stage that ran and came back clean.
  So the rule is stated with no threshold: **if it is worth a sentence in a note it is worth
  an entry in the field, and duplicating it is correct rather than redundant.**

## The general defect: a field whose permitted values cannot express the true state

The section above is the special case that gets noticed, because "unchecked versus clean" has
a name. **It is one instance of a much commoner defect, and the general form is worth stating
because the general form is findable by reading.** Measured across five workers built over
three weeks: **roughly 25 spec bugs, and the large majority were one species** — a field
whose enumerated values could not express something the worker actually found. Every one of
them cost a real run to discover, and almost every one was visible in the definition
beforehand.

**The procedure is cheap enough to just apply. For each enumerated field, name a true state
its value set cannot express. If you can name one, add a member.** That is the whole check,
and doing it while writing the return block costs minutes against a run that costs a browser
session, a live request or somebody's workbook.

What the species looks like in practice, because it wears several disguises:

- **A value that means two different things.** One field held "a source exists and I could
  not date it" and "there is no source to date" under a single `not_obtainable`. Two facts in
  one column, and a comparison table printed them as agreement.
- **A value set with no member for the commonest real case.** A duration enum covered
  fractions and decimals and had nothing for a whole number of hours, which is what most of
  the pages said. The worker picked the nearest member and wrote in its limitations that none
  fitted.
- **A single-valued field where reality is plural.** A "why this was not checkable" field
  took one sentence; the first real case failed on three independent grounds. The worker put
  one in the field and two in prose, and said itself they would be invisible to anything
  joining on the field.
- **A pair-level field where the read is per-side.** Two items, one flag: one item's panel
  rendered and the other returned an empty shell, so any single value was false about one of
  them. The asymmetry went into prose. **Note the two answers may need different evidence:**
  there, "yes, already recorded" was establishable from one side and "no" required both, so a
  half-failed read has to be `cannot_tell` and may never be `no`.
- **A field pinned to one location when the source has two.** One page stated an item's level
  in prose and again in a metadata facet, and they disagreed. A single verbatim string forced
  the worker to concatenate both with their locations, which is no longer verbatim anything.
- **A bound stated as a number rather than as an act.** "At most 300 characters" produced
  spans of 301, 337 and — after the rule was tightened once — 309, each time a span judged
  close enough or cut at the first tidy break past the limit. **A stated limit has to name its
  rounding direction, or the first clean break past it becomes the real limit.** Same shape as
  a character bound so high no input reaches it, which silently makes `truncated` unreachable.
- **A field the definition reasoned about at length and never created.** The most expensive
  version. One file spent a paragraph on why a distinction mattered and gave the worker
  nowhere to record the source's own answer to it, so the single most decisive fact in the
  record arrived as a limitation.

Three rules that fall out of the measurements rather than from taste:

- **Read a fix as unproven until a later run exercises it.** Two fields added on one run were
  filled coherently by the next, in cases the old shape could not have expressed — that, and
  not the reading, is the evidence a fix generalises rather than fitting one record.
- **A member name that misdescribes its own field is a milder but real defect.** One enum
  named `minutes_over_sixty` whose worked example was `45 minutes`. The worker read the
  example and picked correctly; the problem is that **the record travels further than the
  definition does**, so a later reader has every reason to call it a data error. Name the
  operation, not the magnitude.
- **A checker that demands a real field be blanked is worse than one missing the check.** A
  validation script invented a rule the definition never stated and fired against the most
  useful sentence in a record. The next reader goes after the worker instead of after the
  checker. When a checker and a worker disagree, establish which one the definition actually
  supports before fixing either.

And the structural one, which no grep catches: **procedure drifts into the wrong section
without leaving a trace.** In one file, 53 lines of "how to read the page" were appended after
a bullet in *What is not yours to decide*, orphaning that section's last two bullets so they
read as continuations of a paragraph about something else. Both house greps stayed clean and
the file read fine top to bottom in the session that broke it. **After an edit that appends to
a section, re-read the section's end, not just the inserted text.**

## Fan-out is how you find out what your definition actually says

When N copies of one agent run over N inputs, every sentence with two readings gets both,
and the disagreement is visible in a way a single run never makes it.

Measured 2026-09-14 on one batch: two workers split on the same fact. One searched, confirmed
a service name was current, and passed on that basis. The other made "this name is wrong"
its central finding while conceding in its own note that the newer name is real — and cited
that service's own user guide as its source. Nothing in the definition was incorrect. It
simply did not say which way to resolve the case.

Two consequences:

- **Read a fan-out's disagreements as a spec bug, not as worker variance.** The fix is a
  named rule in the "not yours to decide" section, with the date and the observation attached
  — because a rule stated as a measurement survives the next person's edit and a rule stated
  as a preference does not.
- **A false positive is the expensive error.** It costs the reviewer's trust in the whole
  layer, after which nothing the agent returns gets read. Where a rule has to break
  symmetrically, break it toward not-raising.

## Calibrate before you believe an improvement

A before-and-after on a small batch is unreadable unless you have priced the harness's own
movement first. Measured: on a twelve-item batch with **nothing changed between runs**,
eleven of twelve verdicts moved. That puts the instrument's agreement at roughly ±2 items at
n=12, which means no twelve-item comparison on it can support a claim about a prompt edit.

So run the null comparison — same definition, same inputs, twice — before attributing any
change to your edit, and state the noise floor next to the result. An unmeasured improvement
to an agent definition is indistinguishable from resampling.

## What this skill does not cover

- **Decomposition, dependency graphs, fan-out and join, human gates, degradation** —
  `/orchestration-standard`. If you do not yet know how many agents there are, that one comes
  first.
- **Tool surfaces, schemas, refusal shapes and payload design** — `/mcp-server-standard`.
- **Runner flags, invocation syntax and the harness's own options** beyond the frontmatter
  fields above. Those move, and a stale name in a skill reads as authoritative.
- **Whether a worker's domain judgement is right.** This skill can tell you the definition is
  ambiguous; only a labelled set tells you the verdicts are wrong.

## How to apply

Write the description and the return block **before** the body. Those two are the agent's
public surface — one decides whether it is ever called, the other decides whether its output
is usable — and both are expensive to change once an orchestrator and a report writer depend
on them.

When reviewing an existing agent, read it in this order and stop at the first failure: does
the description state cardinality and the not-mine boundary; does `tools` grant anything
outward-facing; can the output distinguish unchecked from clean. Those three are where the
silent failures live.

Then run the enumerated-field pass over the return block, because it is the one check that
pays before anything has been run: **field by field, name a true state the value set cannot
express.** On the measurements above that is where most of the bugs are, and a run costs far
more than the reading does.

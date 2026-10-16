# fail-closed

An opinionated Claude Code setup: six written standards for building agent tooling, five
working skills, a staging guard that actually ships armed, and the templates for the files a
repository needs before an agent can be trusted in it.

**The name is the thesis.** A control that only works when nothing goes wrong is not a
control. A guard whose registration fails open is not registered. A check that cannot detect
its own failure has not run. Every file here is downstream of that.

## Why this exists

The useful conventions for building agent tooling are not the obvious ones. They are things
like: an empty finding list means two different things and must say which; a refusal has to
name the cheapest remedy, not the rule; a coverage floor buys tests that execute lines rather
than tests that catch anything; a queue nobody could enter reads exactly like a queue
everybody passed.

Those took measurements to learn, and they usually live in one person's `~/.claude/`
directory. This is that content, generalized and installable.

It is **not** a best-practices document. Every non-obvious rule here says what the wrong
choice cost, with a date, because a rule you cannot argue with is a rule you cannot apply.

## Install

As a plugin:

```
/plugin install fail-closed
```

Or from a clone, which also places the user-level settings file and the staging hook:

```
git clone https://github.com/julie-elkins/fail-closed.git
cd fail-closed
./install.sh
```

`install.sh` **refuses to overwrite an existing `~/.claude/settings.json`**, with or without
`--force`, because that file holds your own credentials configuration and accumulated
permission grants. It is idempotent — a second run reports everything unchanged — and it backs
up anything it replaces to a timestamped directory it names. Run `./install.sh --dry-run`
first to see the plan.

There is nothing you have to edit afterwards, which was not true of earlier versions of this
file. The shipped settings file sets **no `env` block**: Claude Code keeps authenticating however it
already does, and nothing here reads a credential or a cloud profile from your machine. If you
route Claude Code through a cloud provider, add that provider's documented variables yourself —
`templates/settings.md` says which part of that block can never be copied from someone else.

Start a new session and confirm the skills loaded:

```
/coding-standards
```

## What the plugin runs

Stated explicitly, because a plugin that does not disclose what it executes should not be
trusted:

- **One `PreToolUse` hook**, `hooks/refuse-dangerous-staging.py`, matching `Bash`. It inspects
  the command and refuses blanket stages — `git add -A`, `git add .`, `git commit -a` and the
  ten further forms listed in its docstring. It exits 2 to refuse and 0 to allow, writes its
  reason to stderr, and sends nothing anywhere.
- **No network access, from anything.** No telemetry, no fetches, no uploads.
- **No MCP servers.** This plugin declares none.
- **Everything else is text.** Skills and templates are read by Claude; they execute nothing.

Two local tools under `tools/` are run by you, never automatically, and are described below.

## What you get

### Skills

| Skill | What it's for |
|---|---|
| `/mcp-server-standard` | The 15-point standard for building an MCP server, plus five things no tool complains about and two more if you publish to a registry. **Read it before starting a server, not as a review checklist** — three of the points change every payload's shape and cannot be retrofitted |
| `/orchestration-standard` | The 12-point companion, governing the layer that *calls* the tools |
| `/delivery-path-standard` | The 10-point standard for the path a change travels to production — build, branch protection, where the tests run, whether a drift check blocks, who the alarm reaches, and whether a second person could deploy or roll back. **Run this one FIRST**, at intake: unlike the others it needs no code reading, so every point is a yes/no, and a "no" costs one configuration change before the build exists |
| `/state-and-deletion-standard` | The 10-point standard for how a record is allowed to disappear and what its absence may mean — failed work writing a row, totals that reconcile, a prune guarded by the *input* and not the result, a cap that shows in the output. **Apply it at schema design**: three points decide what every row carries and cost a migration later. Every failure in this family is silent and flatters the system |
| `/content-egress-standard` | The 9-point standard for what may leave the process, for any build touching unpublished material. Names all nine egress channels including the four that get missed — log line, test fixture, error message, traceback — plus debugging flags as an egress channel, and why an unattended run with no stated stop condition gets no access at all. **Applies to builds with no delivery path**, so a one-off script is in scope |
| `/coding-standards` | Python conventions: dependencies and lockfiles, what a comment is for, test layout, mutation testing, sweeps, git. Includes the decisions that look like gaps — no linter, no CI, no coverage floor — and why each is a decision |
| `/agent-authoring` | The agent definition file, not the decomposition: where it lives, the frontmatter, the `description` as routing logic, `tools` as a containment boundary, and the five sections a worker's body needs. Read `/orchestration-standard` first if you do not yet know how many agents there are |
| `/security-triage` | Whether a build carries an application security review, what data class it handles, and what the review costs in *calendar* time — at intake, not at launch. Includes the failure mode that makes security work look finished when it is not: a control that never fires reads exactly like a healthy system |
| `/grill-me` | Adversarial review of your own work, before someone else does it |
| `/fact-check` | Verifies the checkable claims in a draft against the sources that hold the answer. Three verdicts, and it never reports the third as the first |
| `/humanizer` | Line-level pass that strips the tells |

### Tools — `tools/`

Run by you, never automatically. Both exist because of the same gap: configuration is easy to
check and effect is not.

| Tool | What it answers |
|---|---|
| `verify-hooks.py` | Which hooks your settings and installed plugins *register*, and whether each one could actually run. Registration fails open, so a hook whose script is missing or unreadable never warns and never fires. Exits non-zero when any is unreachable |
| `session-report.py` | What a finished session actually did — tools, counts, file paths, MCP servers, recorded cost, and **which guards refused a call.** Read its docstring before trusting a clean report: it reports calls, not effects, and a guard that ran and allowed leaves no record at all |

### Templates — `templates/`

Copy these per repository. `install.sh` places only two — `settings.json.template` and the
staging hook — both at user level, because both are about you rather than about a repo.

| File | Where it goes |
|---|---|
| `CLAUDE.md.template` | Repo root. Carries the splitting rule — the thing a template cannot show by example |
| `DESIGN_PRINCIPLES.md.template` | `docs/`, once CLAUDE.md's rules outgrow being read every session |
| `settings.json.template` + `settings.md` | `~/.claude/settings.json`. The template is strict JSON; the *why* for each block is in the `.md` |
| `project-settings.json.template` + `project-settings.md` | `.claude/settings.json` in a repo. Repo-scoped permissions, and a hook copy **only when that repo has hazards of its own to name** |
| `agents/worker-agent.md.template` + `agents/agents.md` | `.claude/agents/` in the repo the agent belongs to — **not** `~/.claude/agents/`, unless the body names no repo paths. One shape, the worker in a fan-out, because that is the one that has been exercised |
| `hooks/refuse-dangerous-staging.py` | `~/.claude/hooks/`, placed by `install.sh`. Identical to the copy the plugin registers. Copy it into a repo's `.claude/hooks/` as well only to fill in `REPO_HAZARDS` |

## Prove the guard is armed

Installing a guard and arming a guard are different claims, and only the second one matters.
The staging guard is the one thing here that can be probed directly, so probe it. Use
`printf '%s'` rather than `echo`: in zsh, `echo` expands `\n` even inside single quotes, which
puts a raw newline inside the JSON, makes the payload unparseable, and produces an exit 0 that
looks exactly like a considered allow.

```
printf '%s' '{"tool_input":{"command":"git add -A"}}' | /usr/bin/python3 hooks/refuse-dangerous-staging.py
printf '%s' '{"tool_input":{"command":"git add README.md"}}' | /usr/bin/python3 hooks/refuse-dangerous-staging.py
printf '%s' '{"tool_input":{"command":"echo probing\ngit add -A"}}' | /usr/bin/python3 hooks/refuse-dangerous-staging.py
printf '%s' '{"tool_input":{"command":"git add -- -A"}}' | /usr/bin/python3 hooks/refuse-dangerous-staging.py
printf '%s' '{"tool_input":{"command":"git add -- -u"}}' | /usr/bin/python3 hooks/refuse-dangerous-staging.py
```

Lines 1, 3 and 4 must exit 2 with a refusal on stderr. Lines 2 and 5 must exit 0 silently.

**The last three matter more than the first.** Line 3 is multi-line: a guard built on the same
tokenizer was bypassable by any multi-line script for twelve days, and it survived because
every probe anyone wrote was a single line. Lines 4 and 5 are the post-`--` pair — after the
end-of-options marker a dash-token is a filename, so `-A` is refused as a blanket *pathspec*
while `-u` is a named path and must be allowed. **Assert the refusal's reason text, not only
the exit code**: `git add -- .` exits 2 either way, and only the reason says whether it did so
for the right reason.

Then confirm it is registered where you think it is:

```
./tools/verify-hooks.py
```

## What this does NOT do

Stated plainly, because a kit that implies coverage it does not have is worse than a smaller
one:

- **It does not install MCP servers**, and declares none of its own.
- **It does not enforce a spend ceiling.** A `PreToolUse` hook can block a call; it cannot
  watch a budget. Spend limits belong at a gateway. What this offers instead is the
  observability third: `session-report.py` tells you what a finished session cost, afterwards.
- **It does not touch `~/.claude.json`.** That file holds account-scoped resources and
  per-machine paths; copying it wholesale produces connect timeouts that look like broken
  servers.
- **It does not ship `settings.local.json`.** Per-machine by design; transplanting it grants
  approvals you never gave.
- **It does not lint, format, type-check or run CI**, and `/coding-standards` explains why
  each is a decision rather than an omission. If you disagree, the skill says what to measure
  first.
- **It carries no linter or CI config of its own.** A config describing a standard the tree has
  never met is worse than none, because it implies a convention that is not in force.
- **The staging guard sees the Bash tool only** — not your terminal, not Write or Edit, and not
  `git add -f` against an unrecognised path. It narrows the surface; it does not close it, and
  `.gitignore` still has to be right underneath it.

## Status

Built from one person's accumulated `~/.claude/` setup and published as-is. `install.sh` has
been exercised against a scratch `CLAUDE_HOME` — idempotent, non-clobbering, substitution
correct, no absolute home paths in the installed skills. That is not the same as somebody else
getting a working session out of a clean machine, and its central claim — that it saves you
assembling this yourself — is the claim least tested.

## License

MIT. See `LICENSE`.

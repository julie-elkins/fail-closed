# Not covered

**Descriptive, not prescriptive.** Nothing on this page is a to-do. It is a list of things a
reader might reasonably expect the kit to handle, with what it actually does instead, so that
absence is never mistaken for coverage.

If you want to fix one, that is a decision to make on its merits — not a gap to close because
it is written down.

## Not verified by a second user

The kit was built in one pass on 2026-09-09 from one person's setup, and **no one but the
author has installed it.** `install.sh` has been exercised against a scratch `CLAUDE_HOME` —
idempotent, non-clobbering, substitution correct, no absolute home paths in the installed
skills. That is not the same as a colleague getting a working session out of a clean machine.

Its central claim, that it fixes a bus factor of one, is the claim least tested.

## Not distributed

No package in any internal build system and no named backup owner. `.claude-plugin/plugin.json`
now registers one hook, so the plugin and `install.sh` deliver overlapping but not identical
sets: the plugin gives you the skills and the staging guard, `install.sh` additionally writes a
user-level `settings.json`. Two channels that disagree is worse than one channel, so check
`tools/verify-hooks.py` after either.

## One test file, no linter, no CI

**This section was headed "No test suite, no linter, no CI", and the first third of that was
wrong.** `CLAUDE.md` has always named the exception — `tests/test_session_report.py` travels
with the one tool complex enough to need it — and this page did not, so the two disagreed. A
reader trusting this page would have concluded there was nothing to run.

There is. It carries 14 tests, and **it needs no dependency**, which matters because every
other instruction here pins `/usr/bin/python3`:

```
python3 tests/test_session_report.py
```

That prints a line per test and a total. `python3 -m pytest tests/test_session_report.py -q`
works too where pytest is installed, and the macOS system Python does not have it — so the bare
form above is the one that always works, and nothing in this repository requires pytest. The
load-bearing test is the one its own docstring names, `test_sentinel_never_escapes`: it checks
that the report is not itself the leak.

What is genuinely absent is a *suite* — broad coverage, a runner config, a gate — plus any
linter, formatter or type-checker, and that part is deliberate. The reasoning is in
`/coding-standards` rather than here. Short form: a config describing a standard the tree has
never met is worse than no config, because it implies a convention that is not in force. One
internal package measured this — black, isort, flake8 and mypy all declared and configured,
never invoked, `black --check` reporting 162 of 192 files would be reformatted.

The consequence you should hold onto: **the invariants in `CLAUDE.md` are enforced by hand.**
Re-verify them after touching `install.sh`.

## The hook's coverage is narrow, on purpose

`templates/hooks/refuse-dangerous-staging.py` sees the Bash tool. It does not see your own
terminal, does not see Write or Edit, and cannot stop `git add -f` against a path it does not
recognise. `REPO_HAZARDS` ships empty — the per-repo half is yours to fill in.

Installed at user level as of 2026-09-19, so the *directory* gap is closed: it is no longer
only the repos you remembered to configure.

**`git -C <dir> add -A` is refused by neither layer.** Measured 2026-09-19, both directions.
The hook's `BLANKET_STAGE` patterns require `git` and `add` to be adjacent (`\bgit\s+add`), and
`permissions.deny` is prefix-anchored, so a command that puts `-C <dir>` between them escapes
both. The `settings.md` coverage table has the full seven-command result, including the cases
each layer catches that the other misses — they are complementary, which is the argument for
running both, and this is the one shape that falls through the middle.

**Left open deliberately, for now.** Closing it means making the hook tokenize the command
rather than regex it, and the file's substring/regex matching is a stated decision — over-
refusal is the safe direction for a repo whose hazards the author cannot know, and a
token-based rewrite argues the opposite trade in the other direction. Appending a `git\s+-C`
pattern would close this one instance and leave every other separator (`--git-dir`, `-c
alias`, a shell function) in exactly the same state, which is a patch that makes the gap
harder to see rather than smaller. Fix it by re-making the matching decision, or not at all.

It narrows the surface. `.gitignore` still has to be right underneath it.

## Nothing here records what a run actually did

**Every control the kit installs fires BEFORE an action and leaves no trace of the runs it
allowed.** The `permissions.deny` floor and the `PreToolUse` hook are both bouncers at the
door, and neither one writes down who got in. So the kit hands a colleague a setup that is
strong at blocking and silent afterwards, and that asymmetry is worth stating plainly rather
than discovering.

The consequence is specific: **if unpublished content ever did leave the tree, an install
of this kit gives you nowhere to look.** The refusal is loud and the permission is invisible.

**A `PreToolUse` hook cannot close this, and that is the part most likely to be got wrong.** A
hook blocks a call; it has no way to observe one. Adding a fifth hook grows the layer that
already works and leaves this one exactly where it is. The data needed already exists — every
session writes a JSONL transcript under `~/.claude/projects/` — and nothing in the kit reads it.

Measured on the author's own machine 2026-09-28, which is the setup this kit was cut from: 88
retained sessions, **$4,292.41 in recorded cost with single sessions at $453.05**, 1,242
distinct files written, and **12 denials of kind `permission-rule`** — passive evidence the
deny floor fires, read out of the record rather than produced by tripping a rule on purpose.
None of that was visible before something read the transcripts.

Two readers' tools exist outside the kit and are **not installed by it**:
`session-report.py` (what a finished session did) and `memory-audit.py` (which memory files
reference things that no longer exist). Whether they belong in the kit is an open decision, not
a gap to close on sight — shipping a transcript reader to a colleague means shipping something
that reads their whole session history, and that is a choice to make deliberately. Note also
what a reader cannot do: **hook output is absent from the transcripts**, so no such tool can
ever prove a guard fired, and its output names file paths, which means a path can disclose what
form. Any report it produces is local-only.

## Windows and Linux are untested

`install.sh` assumes a macOS layout: `/usr/bin/python3`, BSD `cp -R`, `~/.claude/`. The Python
hook is portable. The shell scripts have not been run anywhere else.

## Not covered by any skill in the kit

Named because a reader will look for each one:

- **Your build system.** Nothing here knows about it. Package creation in particular tends to
  have non-obvious prerequisites and fatal-looking errors that are false alarms; that knowledge
  belongs in individual repos' CLAUDE.md files, not in a portable kit.
- **Application security review mechanics — partly covered, and the split matters.**
  `/security-triage` packages the portable part: data class, whether a build carries a review at
  all, what the review costs in calendar time, and the controls that commonly come back as
  findings. What is **not** in here is your organisation's mechanics — which review type
  applies, which team owns it, how a finding is dispositioned, what an acceptable deferral looks
  like. Those move, and a stale process name in a skill reads as authoritative.
- **Agent runtime deployment.** `/mcp-server-standard` covers what to *build*; deploy paths,
  runtime resource policies and registry publish sequences are touched only where they produced
  a measurement worth recording.
- **Domain work of any kind.** Deliberately absent. A standard that carries one domain's
  vocabulary stops being portable, and the tools that do domain work usually handle material
  that should not be installed casually.

## One agent shape, and no orchestrator template

`/agent-authoring` and `templates/agents/` cover **the worker in a fan-out** — one unit in, one
typed result out, one file written into a workspace. That is the shape that has been run at
twelve and forty copies, so it is the one with measurements behind it.

Not covered: an agent that holds a conversation, an agent that writes outward, and the
orchestrator itself. The orchestrator is a skill rather than an agent file, because it needs
the conversation's context; `/orchestration-standard` covers the layer, and **there is no
template for it.** Also absent by choice: the runner's own invocation flags and options, which
move often enough that a stale name in a skill would read as authoritative.

## No versioning or upgrade path for the templates

Once you have copied `CLAUDE.md.template` into a repo, there is no mechanism that tells you the
template changed. The skills update through the plugin channel; the templates do not update at
all. Treat a copied template as yours from the moment you copy it.

## Not a steering set for another assistant

If your repo also carries instruction files for a different coding assistant, Claude Code does
not read them and that tool does not read `~/.claude/skills/`. A repo carrying both needs the
content in one place and a pointer in the other, or they disagree within a month. This kit does
not generate the other side.

## Nothing here posts anything

By design, across every skill: `/fact-check` is read-only, and `/humanizer` returns a draft. Outward-facing text — Slack messages, ticket and review comments, wiki edits,
shared-config changes — is drafted for you to send, even where the write tool exists and works.
**The tool succeeding is not authorization.** If you want an agent that posts, that is a
different kit and it should be argued for separately.

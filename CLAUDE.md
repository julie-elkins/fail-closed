# fail-closed

A small, opinionated Claude Code configuration. Six written standards for building agent
tooling, four working skills, two hooks, and the templates a repository needs before an agent
is trusted in it. `install.sh` places the skills and `settings.json`; everything else is copied
per repository by hand, on purpose.

The name is the thesis. A control that only works when nothing goes wrong is not a control: a
guard whose registration fails open is not registered, and a check that cannot detect its own
failure has not run. Every file here is downstream of that.

**It dogfoods `templates/CLAUDE.md.template`.** If a section here is doing something the
template does not describe, one of the two is wrong — and it is more often this file, because
this one gets edited while the template does not.

## Read order

1. This file.
2. `skills/coding-standards/SKILL.md` — the conventions this repo is itself held to.
3. `docs/not-covered.md` — named gaps. **Descriptive, not prescriptive.** Do not treat an
   entry there as a to-do.

## Status

Built in one pass from one person's accumulated `~/.claude/` setup. **No one but the author has
installed it.**

`install.sh` has been exercised against a scratch `CLAUDE_HOME` — idempotent, non-clobbering,
substitution correct, no absolute home paths in the installed skills. That is not the same as
somebody else getting a working session out of a clean machine. Its central claim, that it
saves you assembling this yourself, is the claim least tested.

## Environment

No build, no virtualenv, no dependencies. Bash and Python 3 from `/usr/bin/python3`.

```
./install.sh --dry-run
```

Verify a change to the staging hook by running it directly, from the repo root. **Use
`printf '%s'` and not `echo`**: zsh's `echo` expands `\n` even inside single quotes, which puts
a raw newline inside the JSON string, makes the payload unparseable, and gets an exit 0 that
looks exactly like a considered allow.

```
printf '%s' '{"tool_input":{"command":"git add -A"}}' | /usr/bin/python3 templates/hooks/refuse-dangerous-staging.py
printf '%s' '{"tool_input":{"command":"git add README.md"}}' | /usr/bin/python3 templates/hooks/refuse-dangerous-staging.py
printf '%s' '{"tool_input":{"command":"echo probing\ngit add -A"}}' | /usr/bin/python3 templates/hooks/refuse-dangerous-staging.py
printf '%s' '{"tool_input":{"command":"git add -- -A"}}' | /usr/bin/python3 templates/hooks/refuse-dangerous-staging.py
printf '%s' '{"tool_input":{"command":"git add -- -u"}}' | /usr/bin/python3 templates/hooks/refuse-dangerous-staging.py
```

Lines 1, 3 and 4 must exit 2 with a refusal on stderr; lines 2 and 5 must exit 0 silently.

**The last three are the ones worth keeping, and each covers something a one-line `git add -A`
probe does not.** Line 3 is multi-line: a hook built on the same tokeniser elsewhere was
bypassable by any multi-line script for twelve days, and it survived because every probe
anyone wrote was a single line. Lines 4 and 5 are the post-`--` pair — after the end-of-options
marker a dash-token is a filename, so `-A` is refused as a blanket *pathspec* while `-u` is a
named path and must be allowed. Mutation testing says nothing else in the hook's behaviour
distinguishes the `--` handling being present from it being absent. **Assert the refusal's
reason text and not only the exit code**: `git add -- .` exits 2 either way, and only the
reason string says whether it did so for the right reason.

## Invariants that results depend on

1. **`install.sh` never overwrites `~/.claude/settings.json`** — not with `--force`, not with
   anything. That file holds a user's own credentials configuration and accumulated permission
   grants. **Not enforced by a test**, because this repo has no suite. Verified by hand against
   a scratch `CLAUDE_HOME`.
2. **`install.sh` is idempotent.** A second run reports 0 installed and the full skill list
   unchanged. **Not enforced**; re-verify by hand after touching the copy logic.
3. **No path under `skills/` may contain an absolute home directory.** A vendored skill
   carrying `/Users/<someone>` is a skill that silently does nothing on any other machine.
   **Not enforced**; the check is `grep -rn '/Users/' skills/`.
4. **`<CLAUDE_HOME>` in `settings.json.template` must be substituted to an absolute path**,
   never left as `~` or `$HOME`. That field is not shell-expanded and a `~` there does not
   error — the hook simply never runs, which is the fail-open case this repo is named after.
   It must stay a placeholder distinct from `$HOME`, because `install.sh` is tested against a
   `CLAUDE_HOME` override and collapsing the two writes a scratch run's hook path into the
   real home. A second placeholder, `<HOME>`, was removed on 2026-10-15 along with the
   marketplace block that was its only use; `install.sh` no longer substitutes it.
   **Not enforced**; the check is `grep -rn '<[A-Z]' "$CLAUDE_HOME/settings.json"` after an
   install, which must find nothing.
5. **`skills/mcp-server-standard/` is a vendored copy. Its canonical home is
   `github.com/julie-elkins/mcp-server-design-guide`**, where it is published as prose. Two
   public copies can drift, and the drift is silent because neither knows about the other.
   Editing that standard is a two-place change, canonical first. **Not enforced**; the check is
   a diff against the canonical README.
6. **Every `PreToolUse` registration in this repository must set `"onFailure": "block"`, and
   there are FOUR of them.** `hooks/hooks.json` (what the plugin registers), `.claude/settings.json`
   (what this repo runs on itself), `templates/settings.json.template` and
   `templates/project-settings.json.template`. **Without that key a guard fails OPEN:** a hook
   whose script is missing or broken is a *non-blocking* error, so Claude Code reports it and runs
   the command anyway. Shipping a refusal guard without it is this repository contradicting its own
   name in the one file that configures it — which is exactly what it did until 2026-10-16, while
   the author's own four live guards all had it set. **Not enforced**; the check is
   `grep -L onFailure hooks/hooks.json .claude/settings.json templates/*.json.template`, which must
   print nothing. Do **not** set it on `SessionStart` — that event cannot block.

## Things measured untrustworthy

- **The staging guard's coverage.** It sees the Bash tool only — not your terminal, not
  Write/Edit, and not `git add -f` against an unrecognised path. It narrows the surface; it
  does not close it. `.gitignore` still has to be right underneath it. Two further gaps, both
  deliberate and both in the file's docstring: the blanket half does **not** read heredoc
  bodies, so `bash <<'EOF'` with `git add -A` inside is not inspected — that is the price of
  not refusing the commit message that documents the rule — and `REPO_HAZARDS` matches the raw
  string, so it **over**-refuses a mere mention. The second is the safe direction and is not a
  bug to fix.
- **`install.sh`'s `--dry-run`.** Every mutation goes through one `run()` wrapper so dry-run
  cannot miss one, *except* the `sed` that writes `settings.json`, which is special-cased.
  Adding a mutation outside `run()` would be invisible to `--dry-run`. Route new ones through
  it.
- **`tools/session-report.py` reports calls, not effects.** A guard that blocked is visible in
  a transcript; a guard that ran and allowed leaves no record at all. So a report showing no
  refusals cannot distinguish "nothing was refused" from "nothing was attempted". Read its
  docstring before trusting a clean report.

## Conventions

General Python and prose conventions: `skills/coding-standards/SKILL.md`. Local deltas only:

- **Templates use `<ANGLE BRACKETS>` for fill-ins**, uniformly, so `grep -rn '<[A-Z]' ` finds
  every unreplaced one. Never `TODO`, never `FIXME`, never a plausible-looking placeholder
  value — a placeholder that looks like a real value ships as one.
- **`.json.template` files are strict JSON with no comments.** Claude Code parses these files
  as JSON; a commented template either breaks when copied verbatim or teaches hand-stripping.
  The annotations live in a sibling `.md` with the same stem.
- **ASCII `--` in shipped shell and Python**, em dash in Markdown prose. Nothing here should
  depend on an encoding surviving a copy-paste into a terminal.
- **Every skill's `description` is written to gate loading**, not to summarize. It is the only
  text read before the skill is chosen; a vague one costs context in every session where the
  skill is irrelevant.

## Git

**THIS REPOSITORY IS PUBLIC. That is the inversion to hold in mind, because every file here
was written for a private one.**

- **Nothing private may enter this tree — not in a file, not in a commit message, not in
  history.** The standards were originally written with worked examples drawn from private
  repositories, and those examples are what made them concrete. They have been replaced.
  **A replacement that reads like a real system is worse than a generic one**, because it
  invites a reader to go looking for it.
- **The check is a measured sweep, not careful reading.** Before any push, grep the whole tree
  for private identifiers and triage every hit as prose, identifier, or wire value — a short
  acronym is usually a substring of an ordinary English word, and "undetectable" is not a role
  name. **Scan for shapes, not for a word list, and never tighten a pattern to reduce noise:**
  on 2026-10-15 adding `\b` boundaries to drop substring noise made the sweep unable to match
  an internal plugin name of the form `<Employer><Product>-core@<marketplace>`, because the
  character following the employer name is a word character and the trailing boundary never
  fires. It rated the file clean while that name was in it. Careful
  writing is not the control; a file can be reviewed, headed "safe", and still carry a name.
- **History is permanent. Rewriting it changes commit hashes and does not unpublish anything
  already pushed.** Get the tree clean before `git init`, not after.
- **Stage by path. Never `git add -A`.** The repo ships the hook that refuses this; a kit that
  does not follow its own control is not distributable. Installed at
  `.claude/hooks/refuse-dangerous-staging.py`, registered by the tracked
  `.claude/settings.json`. **It now exists in THREE places and all three must be
  byte-identical**: `hooks/` is the copy the plugin registers and ships to installers,
  `templates/hooks/` is the copy people copy per repository, and `.claude/hooks/` is the copy
  this repo runs on itself. Three copies is a three-place change, and nothing enforces it —
  the check is `cmp hooks/refuse-dangerous-staging.py templates/hooks/refuse-dangerous-staging.py`
  and the same against `.claude/hooks/`. A drifted copy is a guard nobody is testing.
  `REPO_HAZARDS` is empty because this repo holds no secret material, which is the honest
  content of that list rather than an unfinished stub. Exercise it in both directions before committing, with the
  five-line recipe under **Environment**; a two-line version once passed against a guard that
  admitted eight real blanket stages.
- **Commit messages are a published surface.** No private identifiers, no account ids, no
  credential values or cookie names.
- **No employer, programme or product is named anywhere in this repository**, including in
  the author field and commit metadata. The standards are the author's; the organisation they
  were written at is not part of the artifact.

## Deliberately out of scope

- **A test suite.** A handful of shell and Python artifacts with hand-verifiable behaviour,
  and the invariants above name what to re-check. A suite here would be the linter-config
  failure in another costume: infrastructure implying a rigour the repo does not have.
  `tests/test_session_report.py` is the one exception and travels with the one tool complex
  enough to need it.
- **Per-point assessments of anyone's existing server.** The standards carry *measurements*
  from real systems; they do not carry findings against a named person's code. A kit that
  opens with what somebody's server got wrong is a code review with a distribution list.
- **Vendor-owned skills.** Redistributing someone else's skill is not ours to do.
- **Enforcing a spend ceiling.** A `PreToolUse` hook can block a call; it cannot watch a
  budget. Spend limits belong at a gateway, and the platform documents them there. What this
  repo offers instead is the observability third: `tools/session-report.py` tells you what a
  finished session cost, after the fact.

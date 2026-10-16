# `.claude/settings.json` — per-repository settings and a repo-specific hook copy

This is the **project** settings file, committed inside a repository. It is a different file
from `~/.claude/settings.json` (see `settings.md`) and carries the things that belong to the
repo rather than to you.

## Read this first: you probably do not need the hook here

**The blanket-staging guard is installed once, at user level, by `install.sh`** — the hook at
`~/.claude/hooks/refuse-dangerous-staging.py`, registered by `~/.claude/settings.json`,
alongside a `permissions.deny` floor. That covers every directory, including the repo you
cloned this morning and have not configured. See `settings.md`.

That is a deliberate change from how this kit first shipped, and the reason is the failure
mode it had: a per-repo-only guard protects the repos you remembered, and the first
`git add -A` in an unconfigured repo is precisely the case the hook exists for. A control you
have to install per repository is a control with a to-do list.

**So a per-repo copy is now for one thing: `REPO_HAZARDS`.** The list near the top of the
hook is where a repo names the files that must never be staged *in that repo* — a live
export, a real records file, a `.mhtml` scrape, anything whose committable form is a synthetic
fixture instead. Those patterns cannot live in the user-level copy, because they are
statements about one repository and a false refusal in every other one is a guard people
learn to route around.

Two consequences worth stating plainly:

- **A repo with no hazards of its own needs no copy here.** An empty `REPO_HAZARDS` in a
  committed per-repo hook is duplication that reads as extra protection, and the next person
  to edit one of the two copies will not know the other exists. (This kit's own repo is the
  exception that proves the rule: it ships a copy with an empty list *because it dogfoods the
  template*, and its `CLAUDE.md` says so out loud.)
- **The per-repo copy is additive, never a replacement.** Both hooks fire. Do not delete the
  user-level registration because a repo has its own.

## Install

Only if this repo has hazards to name. From the repository root:

```
mkdir -p .claude/hooks
cp <kit>/templates/project-settings.json.template .claude/settings.json
cp <kit>/templates/hooks/refuse-dangerous-staging.py .claude/hooks/refuse-dangerous-staging.py
chmod +x .claude/hooks/refuse-dangerous-staging.py
git add .claude/settings.json .claude/hooks/refuse-dangerous-staging.py
```

Then fill in `REPO_HAZARDS` in the copy you just made. That is the reason you made it; a
copy installed and left as a stub is the duplication warned about above.

If the repo already has a `.claude/settings.json`, merge the `hooks` block into it rather
than overwriting — that file may already carry permissions you want.

## Why the wiring looks like this

**`"matcher": "Bash"`** — the hook fires before the Bash tool only. It does not see Write,
Edit, or your own terminal. That is the whole surface, and the hook's docstring says so out
loud so it does not get over-trusted.

**`$CLAUDE_PROJECT_DIR`** rather than a relative path or an absolute one. Relative paths
resolve against the process cwd, which is not reliably the repo root; an absolute path
containing your home directory works on exactly one machine and silently does nothing on
anyone else's — a missing hook command is not an error you get told about.

**`/usr/bin/python3`** rather than `python3` from `PATH`. The system interpreter is the one
guaranteed to exist. A `PATH` python3 may be a project venv that is not active, or absent,
and the failure again presents as a hook that quietly did not run.

## Commit it as `settings.json`, not `settings.local.json`

A guard that lives in `settings.local.json` protects one laptop. The purpose here is a
control that holds for whoever picks the repo up next, which includes you after you have
forgotten the reason. Committed is the point.

## Verify it before trusting it

A hook that is misconfigured behaves exactly like a hook that is working — nothing happens
and every command is allowed. Check both directions once, from the repo root:

```
echo '{"tool_input":{"command":"git add -A"}}' | /usr/bin/python3 .claude/hooks/refuse-dangerous-staging.py; echo "exit=$?"
echo '{"tool_input":{"command":"git add README.md"}}' | /usr/bin/python3 .claude/hooks/refuse-dangerous-staging.py; echo "exit=$?"
```

The first must print `exit=2` with a refusal on stderr; the second must print `exit=0` and
nothing else. Add a third line naming one of this repo's own hazards and check it refuses
too — the universal patterns are not what you installed this copy for.

Then ask an agent in that repo to confirm the session refuses it: the direct invocation
proves the script, and only the session proves the wiring.

**Make that session check a hazard from `REPO_HAZARDS`, not `git add -A`.** The user-level
`permissions.deny` floor is prefix-anchored and matches the bare blanket forms first, so a
refusal there may never have reached any hook — it tests the deny list and tells you nothing
about whether this file is wired up. A path only this repo's list names is matched by nothing
else in the stack, so a refusal on that is unambiguously yours. `templates/settings.md` has
the measured coverage table for the two universal layers.

## What else belongs in this file

`permissions` scoped to the repo: a build command, a test runner, a script only this
project has. Keep the same rule as the user-level file — reads and local commands, never an
outward-facing write.

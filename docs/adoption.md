# Adoption — day one, week one, and what to change first

The kit is designed to be adopted in pieces. Nothing below depends on the step before it
except where it says so, so a stall in one place does not block the rest.

## Day one (20 minutes)

**1. Install and fix the one line.**

```
./install.sh
```

Then replace `<YOUR_BEDROCK_PROFILE>` in `~/.claude/settings.json` with your own AWS profile
name. Nothing else works until this is right, and the failure looks like a Claude Code bug
rather than a config error.

**2. Start a fresh session and confirm the skills are there.** Run `/coding-standards`. If it
does not load, the skills did not install — check `ls ~/.claude/skills/`.

**3. Add exactly one MCP server — whichever one your work actually needs.** Pick the single
highest-value entry for you: usually code search, or your ticket system, or your documentation.
One. If it needs an authentication step, do that first and confirm it works before adding the
server.

Stop there for the day. Resist installing twelve servers in one sitting — every server's tool
definitions enter the context of every session, and if two break you will not know which.

## Week one

**4. Add MCP servers one at a time.** Fresh session after each. In practice the order that pays
off fastest is code search first, then messaging and documentation, then whatever your current
work actually needs. Browser-automation and billing servers tend to have large tool
surfaces — add them when you need them and consider removing them when you don't.

**5. Put a `CLAUDE.md` in the repo you are working in right now**, from
`templates/CLAUDE.md.template`. Do not do all your repos. Do one, the one you touched today,
because you can fill in "Things measured untrustworthy" honestly for that one and you cannot
for the others.

Fill in `Status` and `Things measured untrustworthy` first. Those two carry most of the value
and are the two an agent cannot derive from the tree. `Invariants` can start with one entry.

**6. Verify the staging guard, which `install.sh` already placed.** It is at user level now —
the hook in `~/.claude/hooks/` plus a `permissions.deny` floor in `~/.claude/settings.json` —
so there is nothing to install per repo unless that repo has hazards of its own to name. What
there is to do is check it, in both directions, because a misconfigured hook behaves exactly
like a working one: nothing happens and every command is allowed. The probe and the reason it
has to use the `git -C` form are in `templates/settings.md`.

If `install.sh` reported `REFUSED settings.json` because you already had one, this step is not
optional — the hook is on disk with nothing registering it, and that is a machine that only
looks protected. Merge `permissions.deny` and `hooks` by hand.

**7. Record your own register.** Twenty minutes with three or four things you have written and
liked. Until you do, it is a list of prohibitions with no positive target, and `/humanizer` has
nothing to protect.

## What to change first

The kit is opinionated and some of the opinions are not yours. These are the ones most worth
overriding, and what to think about before you do:

**`permissions.allow`.** Ship-state is empty. Grow it from your own friction,
one entry at a time, and keep the rule: **never allow-list a write.** Anything that posts,
comments, edits a shared config or publishes stays behind a prompt permanently. The prompt is
the last place a wrong outward-facing action can be stopped.

**`enabledPlugins`.** Ship-state is empty. Add plugins one at a time, the
review agent if you drive security engagements. Notice what each costs you in context before
leaving it on.

**The model pins.** `ANTHROPIC_MODEL` and `ANTHROPIC_SMALL_FAST_MODEL` are pinned to specific
ids. Model ids move. Check the current best available rather than assuming these are still it.

**`/coding-standards`' no-linter position.** This is the one people most want to override, and
the skill states the terms: a linter config nobody runs is a *breach* of the standard, not
compliance with it, because it implies a convention that is not in force. If you want a linter,
adopt it properly — run it in a pipeline, fix the tree, keep it green. Half-adopting it is the
outcome the standard is arguing against.

## What not to do

**Do not copy `~/.claude.json` from anyone.** It holds account-scoped resources and absolute
per-machine paths. The resulting `CONNECT_TIMEOUT` wall looks like broken servers rather than
like a config that was never yours.

**Do not copy `settings.local.json`.** Per-machine by design. Transplanting it grants approvals
you never gave. Let it regenerate.

**Do not fill in a CLAUDE.md section you cannot fill in honestly.** A section carrying the
wrong kind of content is worse than an absent one, because it reads as covered. Delete it and
add it when you have something true to put there.

**Do not add the two standards to a public repository.** Their worked examples cite internal
systems and internal measurements. That is what makes them useful.

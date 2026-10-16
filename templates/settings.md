# `settings.json` — what each block is for

`settings.json.template` is **strict JSON with no comments**, deliberately. Claude Code
parses `~/.claude/settings.json` as JSON; a template carrying `//` comments would either
break when copied verbatim or teach you to hand-strip it, and a config that fails to parse
degrades quietly into "my settings did nothing". So the annotations live here instead.

One placeholder must be replaced. `install.sh` does it; if you copy by hand, do it yourself:

| Placeholder | Replace with |
|---|---|
| `<CLAUDE_HOME>` | the directory this file lives in, normally `/Users/<you>/.claude` |

**That path is not shell-expanded.** Not `~`, not `$HOME`, not `${HOME}`. A `~` there does not
error — it resolves to nothing, the hook is simply never registered, and nothing says so. That
is the fail-open case this kit is named after, in the one file that configures it.

It is a placeholder distinct from `$HOME` because the two are different directories as soon as
`CLAUDE_HOME` is overridden, which is how `install.sh` is tested. Collapsing them writes a
scratch install's hook path into the installer's real home: a file that inspects clean while
registering a hook that run never placed.

## `env`

**The shipped template sets no `env` block, deliberately.** Claude Code authenticates however
you already authenticate, and a template that presumes one provider is wrong for everyone
else. If you route Claude Code through a cloud provider, add that provider's documented
variables to an `env` block yourself — and note that whatever names a credential or a profile
there is read from *your* machine, so it is the one part of this file that can never be copied
from somebody else's.

If you do add an `env` block, `ANTHROPIC_MODEL` and `ANTHROPIC_SMALL_FAST_MODEL` pin the main
and the background model.
Pin them explicitly rather than relying on the default: the small/fast model is what runs
file summarization and other cheap background calls, and leaving it unset has at times
meant paying main-model rates for them. Model ids move — check the current ones before
assuming these are still the best available.

## `enableWorkflows`

Turns on the `Workflow` tool (multi-agent orchestration). Leave it on and read
`/orchestration-standard` before writing one — the standard governs the layer that calls
your tools, and several of its points change a workflow's shape rather than tidying it.

## `enabledPlugins`

The template enables no plugins. Add them once you know you
want them.

**This is a deliberate trim, not an oversight.** Each enabled plugin can register MCP
servers and subagents, and every registered server adds tool definitions to the context of
every session — including sessions where it is irrelevant. A config inherited with six
plugins on is a config you did not choose. Turn them on one at a time and notice what each
one costs you.

## `extraKnownMarketplaces`

Registers an extra marketplace as a plugin source, which is one way a kit installs
itself and how you get updates rather than a frozen copy.

The `path` is **absolute and not expanded** — no `~`, no `$HOME`, no `${HOME}`. A `~` here
does not error; it silently resolves to nothing and the marketplace is simply absent, which
presents as "the plugin does not exist" rather than as a bad path. This is the single most
common way this file is wrong after being copied between machines.

## `theme`, `model`

Preferences, no consequences. Change freely.

## `permissions.defaultMode` — pin it, because unset does not mean "default"

Set to `"default"`: reads run without asking, everything else prompts. **The reason this key
is in the template at all is that leaving it out stopped meaning what it reads as.** Claude
Code 2.1.283 *"changed interactive sessions on third-party providers or with telemetry off to
start in auto mode when no permission mode is configured"*. **Two ordinary choices put you in
that bucket**: routing Claude Code through a cloud provider, which is what an `env` block
usually does, or turning telemetry off. Either one, with this key unset, starts you in `auto` —
*"Claude Code runs everything, with
background safety checks"* — on a config whose whole `permissions.allow` discipline is built
around reads-only. The same release note confirms the fix: *"`permissions.defaultMode` still
overrides it."*

**Do not read that release as the date the behaviour arrived.** Measured across 82 session
transcripts on the authoring machine: sessions had been *starting* in `auto` from v2.1.250
onward, including 10 of 17 at v2.1.278 — weeks before the note that describes it. The mix is
not uniform either: the same version in the same directory started sometimes in `auto` and
sometimes in `default`, and nothing in any project or local settings file explains it. So the
provider clause is a sufficient reason to pin the key and **not** a sufficient explanation of
any one session's mode. If you want to know what yours actually did, the starting mode is
recorded as a `permission-mode` record at line index 1 of each transcript under
`~/.claude/projects/<slug>/*.jsonl`, before the first user message.

The values, from the settings reference: `"default"` runs only reads without asking;
`"acceptEdits"` adds file edits and common filesystem commands such as `mkdir` and `mv`;
`"plan"` blocks edits until a plan is approved; `"auto"` runs everything with background
safety checks; `"dontAsk"` auto-denies anything that would have prompted; `"bypassPermissions"`
runs everything without asking. `"manual"` is an alias for `"default"` from v2.1.200.

Two things worth knowing before you change it:

- **`auto` and `bypassPermissions` only take effect from the user-level `settings.json` or
  from managed settings** — set either in a project or local settings file and it is ignored,
  which reads as the setting not working. `--permission-mode` overrides for one session.
- **The mode does not touch `permissions.deny` or the `PreToolUse` hook.** Both still fire in
  every mode, including `auto`. What a permissive mode removes is the *prompt* layer, which is
  the layer that catches the outward-facing write nobody thought to deny. If you want auto mode
  off and not merely unselected, `"permissions": {"disableAutoMode": "disable"}` is the hard
  lever — note the value is the string `"disable"`, not a boolean.

## `permissions.allow`

Tool patterns that never prompt. The template's list is **read-only tools only**, and that
is the rule worth keeping:

- **Allow-list reads.** Documentation lookups, code search, ticket reads, wiki reads. These
  are the calls that make a session tedious when every one needs a click, and the worst
  case of a wrong one is a wasted call.
- **Never allow-list a write.** Anything that posts, comments, edits a shared config, files
  a ticket or publishes to a registry stays behind a prompt, permanently. The prompt is the
  last place a wrong outward-facing action can be stopped, and outward-facing writes should
  be drafted for you to send rather than sent by an agent anyway.
- **Do not allow-list a server you have not connected.** A pattern for a server that fails
  to start is dead weight that reads like coverage; when you later debug a permission
  prompt, that entry sends you looking in the wrong place.

Grow this list from your own friction, not from someone else's file. An inherited 40-entry
allow list is 40 decisions you did not make.

## `permissions.deny` — the blanket-staging floor

Twelve patterns, all of them a form of `git add -A`, `git add .`, `git add -u` or
`git commit -a`. **Keep these when you merge this file into a config you already have.**
They are the one part of the template that is not a preference.

The reason is not tidiness. A blanket stage commits whatever happens to be untracked at that
moment — a scratch file with credentials in it, a `.env`, an exported bank, a directory
somebody dropped in your repo — and a commit is a published surface the moment it is pushed.
Staging by path costs one extra argument and makes the mistake impossible rather than
unlikely. `.gitignore` is not a substitute: it is exactly the file that is wrong on the day
this matters.

**Deny is a floor, not a filter you argue with.** When it refuses, name the paths. Do not
reach for `git add -f`, and do not run the blanket form in your own terminal instead — your
terminal is outside every control in this file, which is the point of the next section.

## `hooks` — and why the hook is belt AND braces

One `PreToolUse` hook on the `Bash` matcher, running
`<CLAUDE_HOME>/hooks/refuse-dangerous-staging.py`. `install.sh` puts that file there and
substitutes the placeholder; the hook itself is `templates/hooks/refuse-dangerous-staging.py`,
and `templates/project-settings.md` covers the per-repository copy.

**`"onFailure": "block"` is the single most important key in this file, and leaving it out is
the mistake this whole kit is named after.** A hook that cannot start — missing path, wrong
interpreter, syntax error, no read permission — is a **non-blocking** error by default. Claude
Code surfaces a notice and then **proceeds with the command**. That is a guard failing OPEN: the
one moment you most need the refusal is the moment it is least likely to happen, and the notice
scrolls past in a transcript nobody re-reads.

With `onFailure: "block"`, a guard that cannot run refuses instead of allowing. The cost is real
and worth stating: break the script and you block your own `Bash` calls until you fix it. That is
the correct direction for a control whose entire purpose is refusal, and it is loud, which is
better than silent. **Set it on every `command` and `http` hook whose job is to refuse
something.**

Do **not** set it on `SessionStart`: that event cannot block, so the key has nothing to act on
there.

`"matcher": "Bash"` and `/usr/bin/python3` rather than a `PATH` python3 are both deliberate,
for the reasons in `project-settings.md` — the same wiring, one level up.

**The deny list and the hook cover different commands, in both directions.** `permissions.deny`
is prefix-anchored — `Bash(git add -A*)` matches a command that *starts* with `git add -A`.
The hook regex-matches `git add` anywhere in the string, but requires `git` and `add` to be
adjacent. Measured against both, 2026-09-19:

| command | deny floor | hook |
|---|---|---|
| `git add -A` | refused | refused |
| `cd /tmp; git add .` | — | refused |
| `echo hi && git add -A` | — | refused |
| `env FOO=1 git add -A` | — | refused |
| `git add -u` | refused | — |
| `git stage -A` | refused | — |
| `git -C /tmp add -A` | — | — |

So the deny floor carries `git add -u` and the `git stage` family, which the hook's patterns
do not match at all; the hook carries everything where the blanket stage is not the first
thing on the line. **Neither one catches `git -C <dir> add -A`** — that is a real gap, not a
simplification, and it is named in `docs/not-covered.md` rather than quietly patched, because
the hook's matching strategy is a decision with an argument attached and closing this needs
that argument re-made rather than a pattern appended.

The consequence for verification: **the direct stdin probe is the one that proves the hook.**

```
echo '{"tool_input":{"command":"git add -A"}}' | /usr/bin/python3 ~/.claude/hooks/refuse-dangerous-staging.py; echo "exit=$?"
echo '{"tool_input":{"command":"git add README.md"}}' | /usr/bin/python3 ~/.claude/hooks/refuse-dangerous-staging.py; echo "exit=$?"
```

First must be `exit=2` with a refusal on stderr; second `exit=0` and silent. Then ask an agent
to run `git add -A` and confirm the session refuses it. **That session check proves a refusal
arrived, not which layer produced it** — the deny floor matches that command first and the
hook may never have run. Which is fine as far as it goes: for the bare form, either layer
refusing is the outcome you wanted. Just do not read it as evidence the `hooks` block parsed.

**What neither block covers**, stated because a guard nobody knows the edge of gets
over-trusted: your own terminal, the Write and Edit tools, a script that shells out to git,
`git -C` as above, and `git add -f` against a path the hook does not recognise as a hazard. It
narrows the surface. It does not close it.

**If `install.sh` refused to write `settings.json`** because you already had one, neither of
these blocks landed. Merge them by hand. The hook file will be on disk and nothing will be
registering it, which presents as a machine that is protected.

## What this template does NOT ship

**`settings.local.json`.** It is per-machine by design — it accumulates project-scoped
permission grants as you approve them, and it is `.gitignore`d for a reason. There is
nothing in it worth transplanting, and transplanting it grants approvals you never gave.
Let it regenerate.

**`~/.claude.json`.** That is where MCP server entries live, and it holds account-scoped
URIs and per-machine paths. Add servers deliberately and one at a time
instead. Copying that file wholesale gives you a config pointing at resources you cannot
reach, and the resulting connect timeouts look like broken servers rather than a config
that was never yours.

**Project settings.** `.claude/settings.json` inside a repository is a separate file with a
separate purpose — repo-scoped permissions, and a hook copy carrying hazards specific to
that repo. It is **not** where the staging guard has to live any more; the blocks above
cover every directory. See `project-settings.md` for when a per-repo copy still earns its
place.

#!/usr/bin/env bash
#
# Install the fail-closed kit into ~/.claude/.
#
# THREE PROPERTIES, IN ORDER OF HOW MUCH THEY MATTER.
#
#   1. It refuses to clobber. An existing settings.json is YOUR config -- it holds your
#      authentication, your accumulated permission grants and your plugin choices. This
#      script will not overwrite it. It prints what it would have written and stops.
#   2. It is idempotent. Run it twice and the second run reports "unchanged" for
#      everything. A script you are afraid to re-run is a script you stop running.
#   3. It backs up anything it replaces, to a timestamped directory it names.
#
# Nothing here touches ~/.claude.json, where MCP server entries live. Server
# installation is deliberately manual and one-at-a-time, so you can tell which one broke.
#
# It installs the blanket-staging hook at USER level, into ~/.claude/hooks/, and the
# settings.json it writes registers it. A per-repository copy is still worth having when
# that repo has hazards of its own to name -- see templates/project-settings.md -- but the
# user-level one is what covers the repo you forgot to set up.
#
# Column note: the `say`/`note` lines below run slightly past 88 columns in SOURCE
# because of quoting overhead. What they PRINT is inside 88. Reflowing them would
# shorten the message rather than the line, so they are left as they are.
#
# Usage:
#   ./install.sh                 install; refuse on conflicts
#   ./install.sh --force         replace conflicting skills (still backs them up)
#   ./install.sh --dry-run       print what would happen, change nothing
#
# Override the target for testing:
#   CLAUDE_HOME=$(mktemp -d) ./install.sh

set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
BACKUP_DIR="$CLAUDE_HOME/.kit-backup-$(date +%Y%m%d-%H%M%S)"

FORCE=0
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --force)   FORCE=1 ;;
        --dry-run) DRY_RUN=1 ;;
        -h|--help) sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown argument: $arg (try --help)" >&2; exit 64 ;;
    esac
done

INSTALLED=()
UNCHANGED=()
REFUSED=()
BACKED_UP=0

say()  { printf '%s\n' "$*"; }
note() { printf '  %s\n' "$*"; }

run() {
    # Every mutation goes through here, so --dry-run cannot miss one.
    if [ "$DRY_RUN" -eq 1 ]; then
        note "would run: $*"
    else
        "$@"
    fi
}

backup() {
    # Called before any replacement. Creates the backup directory lazily, so a run that
    # replaces nothing does not leave an empty directory behind to be puzzled over.
    local src="$1"
    if [ "$DRY_RUN" -eq 1 ]; then
        note "would back up $src -> $BACKUP_DIR/"
        return
    fi
    mkdir -p "$BACKUP_DIR"
    cp -R "$src" "$BACKUP_DIR/"
    BACKED_UP=1
}

# ---------------------------------------------------------------------------------
# Preflight. Fail before changing anything rather than half-way through.
# ---------------------------------------------------------------------------------
if [ ! -d "$KIT_DIR/skills" ]; then
    say "FATAL: $KIT_DIR/skills is missing. Run this script from inside the kit checkout."
    exit 1
fi

HOOK_SRC="$KIT_DIR/templates/hooks/refuse-dangerous-staging.py"
if [ ! -f "$HOOK_SRC" ]; then
    say "FATAL: $HOOK_SRC is missing. The settings.json this script writes registers that"
    say "       hook, and a registered hook whose file is absent does not error -- it just"
    say "       allows everything. Refusing to write a config that only looks protected."
    exit 1
fi

run mkdir -p "$CLAUDE_HOME/skills"
run mkdir -p "$CLAUDE_HOME/hooks"

# ---------------------------------------------------------------------------------
# 1. Skills.
#
# Copied, not symlinked. A symlink into a checkout breaks the moment the checkout moves
# or is deleted, and a broken skill symlink does not announce itself -- the skill is
# simply absent from the listing, which reads like a kit that did not install.
# ---------------------------------------------------------------------------------
say "Skills -> $CLAUDE_HOME/skills/"
for skill_path in "$KIT_DIR"/skills/*/; do
    [ -d "$skill_path" ] || continue
    skill="$(basename "$skill_path")"
    dest="$CLAUDE_HOME/skills/$skill"

    if [ ! -e "$dest" ]; then
        run cp -R "$skill_path" "$dest"
        INSTALLED+=("$skill")
        note "installed  $skill"
        continue
    fi

    if diff -rq "$skill_path" "$dest" >/dev/null 2>&1; then
        UNCHANGED+=("$skill")
        note "unchanged  $skill"
        continue
    fi

    if [ "$FORCE" -eq 1 ]; then
        backup "$dest"
        run rm -rf "$dest"
        run cp -R "$skill_path" "$dest"
        INSTALLED+=("$skill")
        note "replaced   $skill (backed up)"
    else
        REFUSED+=("skills/$skill")
        note "REFUSED    $skill -- exists and differs. Re-run with --force to replace it."
    fi
done

# ---------------------------------------------------------------------------------
# 2. The blanket-staging hook, at user level.
#
# Installed BEFORE settings.json, because settings.json is what registers it and the
# wrong order leaves a window where the config names a file that is not there yet.
#
# Copied rather than symlinked, for the same reason as the skills: a symlink into a
# checkout that later moves leaves a hook command pointing at nothing, and a hook whose
# command does not exist is not an error -- the tool call simply proceeds.
# ---------------------------------------------------------------------------------
say ""
say "Staging hook -> $CLAUDE_HOME/hooks/refuse-dangerous-staging.py"
HOOK_DEST="$CLAUDE_HOME/hooks/refuse-dangerous-staging.py"

if [ ! -e "$HOOK_DEST" ]; then
    run cp "$HOOK_SRC" "$HOOK_DEST"
    run chmod +x "$HOOK_DEST"
    INSTALLED+=("hooks/refuse-dangerous-staging.py")
    note "installed  refuse-dangerous-staging.py"
elif cmp -s "$HOOK_SRC" "$HOOK_DEST"; then
    UNCHANGED+=("hooks/refuse-dangerous-staging.py")
    note "unchanged  refuse-dangerous-staging.py"
elif [ "$FORCE" -eq 1 ]; then
    backup "$HOOK_DEST"
    run cp "$HOOK_SRC" "$HOOK_DEST"
    run chmod +x "$HOOK_DEST"
    INSTALLED+=("hooks/refuse-dangerous-staging.py")
    note "replaced   refuse-dangerous-staging.py (backed up)"
else
    REFUSED+=("hooks/refuse-dangerous-staging.py")
    note "REFUSED    exists and differs. It may carry hazards you added. Diff it:"
    note "             diff \"$HOOK_DEST\" \"$HOOK_SRC\""
fi

# ---------------------------------------------------------------------------------
# 3. settings.json.
#
# Never overwritten, not even with --force. This file is where your authentication and
# your accumulated permission grants live; replacing it is the one action in this script that
# could cost you something you cannot get back by re-running anything.
# ---------------------------------------------------------------------------------
say ""
say "settings.json -> $CLAUDE_HOME/settings.json"
SETTINGS_DEST="$CLAUDE_HOME/settings.json"
SETTINGS_SRC="$KIT_DIR/templates/settings.json.template"

if [ -e "$SETTINGS_DEST" ]; then
    REFUSED+=("settings.json")
    note "REFUSED    exists. Not touching it, --force or no --force."
    note "           Compare by hand and merge what you want:"
    note "             diff \"$SETTINGS_DEST\" \"$SETTINGS_SRC\""
    note "           The blocks worth checking you have: env, permissions.deny"
    note "           and hooks. See templates/settings.md."
    note "           MERGE THESE TWO EVEN IF YOU MERGE NOTHING ELSE: permissions.deny and"
    note "           hooks. The hook above is now on disk but nothing registers it until"
    note "           one of them is in this file, and an unregistered hook is silent."
else
    if [ "$DRY_RUN" -eq 1 ]; then
        note "would write $SETTINGS_DEST from the template, substituting <CLAUDE_HOME>"
    else
        # Both placeholders must become absolute paths: these fields are not
        # shell-expanded, and a literal ~ resolves to nothing rather than erroring -- the
        # marketplace just silently does not exist, and the hook just silently never runs.
        #
        # They are two placeholders and not one because they name two different
        # directories the moment CLAUDE_HOME is overridden for testing. Substituting
        # $HOME into the hook command would point a scratch install's config at the
        # installer's REAL home -- a config that passes inspection while registering a
        # hook this run never wrote.
        sed -e "s|<CLAUDE_HOME>|$CLAUDE_HOME|g" \
            "$SETTINGS_SRC" > "$SETTINGS_DEST"
    fi
    INSTALLED+=("settings.json")
    note "installed  settings.json"
    note "NOTE: the settings.json written here sets no env block, so your existing"
    note "      authentication is unchanged. See templates/settings.md to add one."
fi

# ---------------------------------------------------------------------------------
# 4. Report.
#
# Printed as three explicit lists, including the empty ones. A silent success and a
# success that skipped everything look identical otherwise, and this script's whole
# value is that you can tell what it did.
# ---------------------------------------------------------------------------------
say ""
say "--------------------------------------------------------------------"
[ "$DRY_RUN" -eq 1 ] && say "DRY RUN -- nothing was changed."
say "installed/replaced: ${#INSTALLED[@]}  ${INSTALLED[*]:-(none)}"
say "unchanged:          ${#UNCHANGED[@]}  ${UNCHANGED[*]:-(none)}"
say "refused:            ${#REFUSED[@]}  ${REFUSED[*]:-(none)}"
[ "$BACKED_UP" -eq 1 ] && say "backups:            $BACKUP_DIR"
say ""

if [ "${#REFUSED[@]}" -gt 0 ]; then
    say "Some things were refused. That is the script working, not failing:"
    say "it will not overwrite a config you may have edited. Resolve them by hand,"
    say "or re-run with --force for the skills (settings.json is never forced)."
    say ""
fi

say "Not installed by this script, on purpose:"
say "  MCP servers        -- add one at a time, fresh session after each."
say "  Repo templates     -- copy per repository. See templates/."
say "  A per-repo hook copy -- only for a repo with hazards of its own to name."
say "                       The user-level one above already covers every directory."
say "                       See templates/project-settings.md."
say ""
say "VERIFY THE GUARD BEFORE TRUSTING IT. A misconfigured hook and a working one look"
say "identical -- nothing happens and everything is allowed. From any directory:"
say "  echo '{\"tool_input\":{\"command\":\"git add -A\"}}' | /usr/bin/python3 \"$CLAUDE_HOME/hooks/refuse-dangerous-staging.py\"; echo \"exit=\$?\""
say "That must print exit=2 with a refusal on stderr; the same probe with 'git add"
say "README.md' must print exit=0 and nothing else. Then ask an agent to run 'git add -A'"
say "and confirm the session refuses it -- but read that as 'a refusal arrived', not as"
say "proof the hook ran: the deny floor matches that command first. The two layers cover"
say "different commands and neither covers 'git -C <dir> add -A'. Coverage table and the"
say "reason that gap is left open: templates/settings.md and docs/not-covered.md."
say ""
say "Next: start a new Claude Code session and run /coding-standards to confirm skills load."
say "Then read docs/adoption.md."

exit 0

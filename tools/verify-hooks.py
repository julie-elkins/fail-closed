#!/usr/bin/env python3
"""Report which hooks are REGISTERED -- by settings and by installed plugins -- and
whether each one could actually run.

WHY THIS EXISTS. Hook registration fails open. If a hook is configured but its script is
missing, unreadable, or not executable when it needs to be, Claude Code does not refuse to
start and does not warn you -- the hook simply never fires, and a session with a broken
guard looks exactly like a session with a working one. So "I configured a guard" and "a
guard is armed" are two different claims, and only one of them is checkable from outside.

============================================================================
WHAT THIS CANNOT SHOW -- READ THIS BEFORE TRUSTING A CLEAN REPORT
============================================================================

1. It proves REGISTRATION and REACHABILITY, not BEHAVIOUR. A script that exists, is
   readable, and exits 0 on everything is reported here as fine. Whether it refuses what
   it should refuse is a question for that script's own probe -- run one, in BOTH
   directions. A guard that refuses everything passes any check that only looks for
   refusals.

2. A hook that RAN AND ALLOWED leaves no trace. Nothing in a transcript distinguishes
   "the guard permitted this" from "no guard was consulted". This tool reads
   configuration, not history, so it cannot close that gap either.

3. A CRASHED hook is invisible to this tool. It checks that a file is there and could be
   read or executed. A script that is reachable and raises on every payload registers
   here as fine and blocks nothing.

4. Settings files are merged by Claude Code, lowest precedence first. A hook registered
   in a file this run did not read is invisible. Pass each file you rely on.

PLUGIN HOOKS ARE INCLUDED, AND THAT IS THE POINT. A plugin registers hooks in its own
`hooks/hooks.json`, not in any settings file, so a tool that reads settings alone reports
"all clear" while being structurally blind to every guard a plugin installed. A check that
cannot see half the hooks is the failure this repository is named after. Plugin hooks are
also reported with whether the plugin is ENABLED: a `hooks.json` sitting in a disabled
plugin registers nothing, and looks identical to one that is live.

THIS OUTPUT IS LOCAL-ONLY. It prints absolute file paths and the raw matcher strings from
your configuration, and a matcher routinely names every MCP server a guard covers. That is
an inventory of your tooling and in some cases of your employer's internal systems. Read it
yourself; do not paste it into a bug report, a ticket, or an issue.

Exit codes: 0 = every registered hook is present and runnable. 1 = at least one is not.
2 = a settings file was named and could not be read or parsed. A non-zero exit is the
point; this is meant to run before an unattended session, not as a report nobody reads.

Usage:
    ./verify-hooks.py                     # ~/.claude/settings.json + installed plugins
    ./verify-hooks.py path/to/settings.json
    ./verify-hooks.py --no-plugins        # settings only
    CLAUDE_HOME=/tmp/scratch ./verify-hooks.py
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

# Interpreters and launchers are not the script whose reachability matters. A script run
# THROUGH one of these only needs to be readable; a script invoked directly needs +x.
_LAUNCHERS = {"python", "python3", "bash", "sh", "zsh", "node", "env", "uv", "uvx", "deno"}


def claude_home() -> Path:
    home = os.environ.get("CLAUDE_HOME")
    return Path(home).expanduser() if home else Path.home() / ".claude"


def script_from_command(command: str, plugin_root: Path | None = None,
                        project_dir: Path | None = None):
    """Return (path, needs_execute_bit) for a hook command, or None if unresolvable.

    `needs_execute_bit` is False when an interpreter precedes the script, because the
    interpreter reads the file and the execute bit is irrelevant. Requiring +x
    unconditionally reports the documented `python3 script.py` form as broken, which is a
    false alarm, and false alarms are how a check like this gets ignored.

    A hook command is a shell string: it may carry an interpreter, flags, a pipeline, or
    an inline expression. Anything that cannot be resolved is reported as unresolved
    rather than guessed at, because a wrong guess here reads as a passing check.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    launched = False
    for token in tokens:
        if token.startswith("-"):
            continue
        if Path(token).name in _LAUNCHERS:
            launched = True
            continue
        if "/" in token or token.endswith((".py", ".sh", ".js", ".ts", ".mjs")):
            if plugin_root is not None:
                token = token.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
                token = token.replace("$CLAUDE_PLUGIN_ROOT", str(plugin_root))
            # Claude Code sets CLAUDE_PROJECT_DIR in a hook's environment, but this tool
            # runs OUTSIDE a session, where it is unset. Left unexpanded, the path does
            # not exist and every project-scoped hook reports MISSING -- a false alarm
            # that teaches people to ignore this report, which is worse than no report.
            # For a project settings file the project dir is knowable: it is the
            # directory holding `.claude/`, so substitute that and say so.
            if project_dir is not None:
                token = token.replace("${CLAUDE_PROJECT_DIR}", str(project_dir))
                token = token.replace("$CLAUDE_PROJECT_DIR", str(project_dir))
            expanded = os.path.expandvars(token)
            if "$" in expanded:
                # Still a variable this tool cannot resolve. Reported as unchecked, never
                # as OK: a check that did not run is not a check that passed.
                return None
            return Path(expanded).expanduser(), not launched
    return None


def check(command: str, plugin_root: Path | None = None,
          project_dir: Path | None = None) -> tuple[str, str]:
    """Return (status, detail). status is OK, MISSING, UNREADABLE, NOEXEC or UNRESOLVED."""
    resolved = script_from_command(command, plugin_root, project_dir)
    if resolved is None:
        return "UNRESOLVED", command[:70]
    target, needs_x = resolved
    if not target.exists():
        return "MISSING", str(target)
    if needs_x and not os.access(target, os.X_OK):
        return "NOEXEC", str(target)
    if not os.access(target, os.R_OK):
        return "UNREADABLE", str(target)
    return "OK", str(target)


def collect_settings_hooks(path: Path) -> tuple[list, int]:
    """Return (rows, fatal). rows are (source, event, matcher, command, plugin_root)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"REFUSED -- no settings file at {path}", file=sys.stderr)
        return [], 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"REFUSED -- could not parse {path}: {exc}", file=sys.stderr)
        return [], 2
    rows = []
    for event, entries in sorted((data.get("hooks") or {}).items()):
        for entry in entries if isinstance(entries, list) else []:
            matcher = entry.get("matcher", "*")
            for hook in entry.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                rows.append((path.name, event, matcher, hook.get("command", ""), None))
    return rows, 0


def enabled_plugins(home: Path) -> dict:
    try:
        data = json.loads((home / "settings.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data.get("enabledPlugins") or {}


def collect_plugin_hooks(home: Path) -> list:
    """Find every installed plugin's hooks/hooks.json.

    Looks under the plugins tree and under any directory-source marketplace named in
    settings. A plugin found here may still be disabled -- that is reported, not assumed,
    because a hooks.json in a disabled plugin registers nothing while looking live.
    """
    roots = [home / "plugins" / "marketplaces"]
    try:
        data = json.loads((home / "settings.json").read_text(encoding="utf-8"))
        for mk in (data.get("extraKnownMarketplaces") or {}).values():
            src = (mk or {}).get("source") or {}
            if src.get("source") == "directory" and src.get("path"):
                roots.append(Path(src["path"]).expanduser())
    except (OSError, json.JSONDecodeError):
        pass

    enabled = enabled_plugins(home)
    rows = []
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        for hooks_json in sorted(root.glob("*/*/hooks/hooks.json")) + sorted(
            root.glob("*/hooks/hooks.json")
        ):
            plugin_root = hooks_json.parent.parent
            if plugin_root in seen:
                continue
            seen.add(plugin_root)
            name = plugin_root.name
            state = next(
                (v for k, v in enabled.items() if k.split("@")[0] == name or k == name),
                None,
            )
            label = "enabled" if state is True else "DISABLED" if state is False else "unlisted"
            try:
                data = json.loads(hooks_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                rows.append((f"plugin:{name} [{label}]", "?", "?", f"UNPARSEABLE {exc}", None))
                continue
            for event, entries in sorted((data.get("hooks") or {}).items()):
                for entry in entries if isinstance(entries, list) else []:
                    matcher = entry.get("matcher", "*")
                    for hook in entry.get("hooks", []):
                        if hook.get("type") != "command":
                            continue
                        rows.append(
                            (
                                f"plugin:{name} [{label}]",
                                event,
                                matcher,
                                hook.get("command", ""),
                                plugin_root,
                            )
                        )
    return rows


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--no-plugins"]
    with_plugins = "--no-plugins" not in argv[1:]
    home = claude_home()
    settings = Path(args[0]).expanduser() if args else home / "settings.json"

    # For a settings file inside a `.claude/` directory, CLAUDE_PROJECT_DIR is the
    # directory holding it. Derived rather than guessed, and reported below.
    project_dir = (
        settings.resolve().parent.parent if settings.parent.name == ".claude" else None
    )

    rows, fatal = collect_settings_hooks(settings)
    if fatal:
        return fatal
    if with_plugins:
        rows += collect_plugin_hooks(home)

    if not rows:
        print(f"{settings}: no hooks registered, and no plugin registers any.")
        print("  That is a finding, not a pass -- an absent guard and a broken one")
        print("  both produce no refusals.")
        return 0

    problems = 0
    disabled = 0
    last_source = None
    for source, event, matcher, command, plugin_root in rows:
        if source != last_source:
            print(f"\n{source}")
            last_source = source
        status, detail = check(command, plugin_root, project_dir)
        mark = "OK" if status == "OK" else "X "
        if status != "OK":
            problems += 1
        if "DISABLED" in source:
            disabled += 1
        print(f"  {mark} {event}[{matcher}] {status if status != 'OK' else ''} {detail}")

    print(f"\n{len(rows)} registered, {problems} unrunnable, {disabled} in a disabled plugin.")
    if project_dir is not None:
        print(f"CLAUDE_PROJECT_DIR read as {project_dir} (derived from the settings path,")
        print("because it is unset outside a session). A hook registered under a variable")
        print("this tool cannot resolve is reported UNRESOLVED, never OK.")
    if problems:
        print("An unrunnable hook does not warn and does not fire. Fix before relying on it.")
    if disabled:
        print("A hook in a DISABLED plugin is not registered at all. Enable it or stop")
        print("counting it as a control.")
    if not problems:
        print("Every registered hook is present and runnable. That is NOT the same as")
        print("armed -- run each script's own probe, in both directions, to check it")
        print("refuses what it should and allows what it should.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

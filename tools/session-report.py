#!/usr/bin/env python3
"""Report what a Claude Code session actually DID, from its transcript.

WHAT THIS IS FOR. A permission rule and a PreToolUse hook both fire BEFORE an action,
and neither leaves a record of the runs it allowed through. So if unpublished content
ever did leave, there is nowhere to look. This script reads the JSONL transcripts Claude Code already writes and
turns them into an after-the-fact record: which tools ran, which MCP servers were
touched, which skills fired, which files were written, what got denied, and what it
cost.

It is the OBSERVABILITY third of the three things a controlled run needs
(observability, rollback, a clear stop condition). It provides none of the other two.

============================================================================
WHAT THIS CANNOT SHOW -- READ THIS BEFORE TRUSTING A CLEAN REPORT
============================================================================

1. A GUARD THAT BLOCKED IS VISIBLE. A GUARD THAT ALLOWED IS NOT. Corrected 2026-10-02;
   the earlier claim here was that hooks were invisible entirely, and that was wrong.
   A refusal IS written to the transcript: a `type == "user"` record carries
   `toolDenialKind` and a `toolUseResult` string beginning
   `Error: PreToolUse:<Tool> hook error: [...]: REFUSED by ...`, which names the guard
   script. This script reads that and reports it per guard.

   **What is still invisible is the half that matters.** A guard that ran and PERMITTED
   the call leaves no record at all, so a report showing no refusals cannot distinguish
   "nothing was refused" from "nothing was attempted".

   **And a CRASHED guard is now MEASURED as invisible, which is worse than unmeasured.**
   Settled 2026-10-02 by a two-arm probe in a scratch `CLAUDE_CONFIG_DIR` -- never in
   `~/.claude/settings.json`:
     * ARM A, the control: a hook exiting 2 blocked the call and WAS recorded, with
       `toolDenialKind` and the hook-error line naming the script. So the instrument
       works, and a null in arm B is a real null rather than a broken harness.
     * ARM B: a hook raising an unhandled exception (exit 1) let the command RUN and
       wrote NOTHING -- no denial record, no `hookErrors`, no traceback, no system
       record of any kind. The transcript is identical to one from a session with no
       hook configured.
   `hookCount` / `hookInfos` / `hookErrors` / `preventedContinuation` do exist on
   `type == "system"` records, but every instance seen held only internal
   `{"command": "callback"}` entries with `hookErrors` empty. They are internal
   bookkeeping, not the guard channel. This script still counts them, against the day
   that changes, but **do not read a zero there as evidence no guard failed.**

   The operational consequence, and the reason this is in the docstring rather than a
   footnote: **guard registration fails OPEN and a disarmed guard is undetectable after
   the fact.** `verify-hooks.py` is the only thing here that can catch one, it reads
   registration directly rather than through a session, and it therefore has to be RUN --
   it deliberately leaves no transcript record of its own. The two tools answer different
   questions: that one asks "would a guard refuse?", this one asks "did one?". Neither
   asks "is a guard still armed?" passively, because nothing can.

2. A ZERO DENIAL COUNT IS AMBIGUOUS IN THE FLATTERING DIRECTION. `toolDenialKind`
   records user rejections, automode blocks and hook refusals. Zero can mean nothing
   was refused, or it can mean nothing was attempted -- and it says nothing whatever
   about the 114 deny rules, which have never once appeared in a transcript denial
   record. Measured 2026-10-02 over 387 transcripts: all 13 `permission-rule` records
   were PreToolUse HOOK refusals and none was a deny-list refusal, so do not read a
   `permission-rule` count as evidence about the deny list. A zero here is not a pass.

3. THE CORPUS TURNS OVER WHILE YOU WORK. Measured on this corpus: two reads minutes
   apart returning 1122 then 1099 typed prompts -- a 23-prompt difference, unexplained.
   Counts from this script are a statement about what is retained at read time. **Do
   not build a trend out of them** and do not treat a figure quoted last week as
   comparable to today's.

4. A DATE WINDOW MAY FILTER NOTHING. Measured: a `--since` window was inert on
   this corpus: 30, 60, 120, 365 and 3650 day windows all returned the same prompts,
   because the whole retained corpus falls inside 30 days. `--days` here has the same
   hazard. The report prints the oldest and newest timestamp it actually saw so you can
   tell whether the window bit.

5. IT SEES CALLS, NOT EFFECTS. A `Write` in the transcript means a write was
   attempted and recorded. It does not prove the bytes are on disk now, and a file
   written then deleted looks the same as a file written and kept.

6. SUBAGENT WORK IS UNDER-COUNTED. Records carry `isSidechain`; a subagent's own tool
   calls may live outside the parent transcript entirely. Treat tool counts as a lower
   bound when `Agent` or `Workflow` appears.

============================================================================
CONTAINMENT -- WHAT IS DELIBERATELY NOT PRINTED
============================================================================

The primary control is structural: **read named fields, not regexes over the text.**

  * NO tool RESULTS, with ONE named exception added 2026-10-02 and bounded three ways.
    Tool results are stored as `type == "user"` records and are where file contents and
    unpublished material live. The exception exists because a guard's refusal is recorded
    nowhere else, and an audit that cannot name the guard that fired is the gap this
    file was written to close. It is bounded by: (a) only a result that is a plain
    `str` is looked at -- a `dict` result, which is the shape Bash stdout and MCP
    payloads use, is never read; (b) the string must contain the literal
    `hook error:` before a regex is applied to it at all; (c) the ONLY things kept are
    the tool name and the guard's filename, both from capture groups. The matched text
    is never stored, never printed, and never reaches a counter key.
    **The reason for (c) rather than storing the reason string:** a guard composes its
    refusal text, so a guard that names only field labels is safe to read today -- but a
    future edit to any guard's message must not be able to turn this file into the leak.
    Keeping two tokens means it cannot.
  * NO tool INPUTS, except a hard allowlist: `file_path` / `notebook_path` (a path is
    an address, not content) and the FIRST TOKEN of a Bash `command` (the executable).
    A Bash command can carry a grep pattern containing the content itself; the rest of
    the line is dropped.
  * NO prompt text, no assistant text, no thinking blocks.
  * NO network calls. Reads the filesystem and writes stdout, or one file with --out.

**THE REPORT ITSELF IS LOCAL-ONLY.** It names file paths, and a path can disclose what
it points at ("Q3 Acquisition Model v2 CONFIDENTIAL.xlsx"). Filenames are what make the
audit useful, so they are kept -- which means the OUTPUT inherits the same handling as
the files it names. Never paste a report into a ticket, a commit message, Slack, a wiki or
anything outward-facing.

============================================================================
USAGE
============================================================================

    session-report.py                      # every retained session, newest first
    session-report.py --days 7             # see hazard 4 above
    session-report.py --session f35e9a3e   # one session, by id prefix
    session-report.py --project -Users-you
    session-report.py --tool Write         # only sessions that used a tool
    session-report.py --mcp github         # only sessions that touched an MCP server
    session-report.py --guard egress       # only sessions where a guard REFUSED a call
    session-report.py --summary            # one line per session, no detail
    session-report.py --out ~/report.txt

Exit status is 0 whether or not anything was found. A non-zero exit means the script
failed, never that the corpus was clean.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import pathlib
import re
import sys

PROJECTS_ROOT = pathlib.Path.home() / ".claude" / "projects"

# A PreToolUse hook refusal, as the transcript actually records it. Measured 2026-10-02:
#   Error: PreToolUse:Bash hook error: [/usr/bin/python3 /…/refuse-dangerous-staging.py]:
#   REFUSED by ~/.claude/hooks/refuse-dangerous-staging.py
# Two capture groups and nothing else leaves this regex -- see CONTAINMENT (c).
GUARD_REFUSAL = re.compile(r"PreToolUse:(\w+) hook error:.*?(refuse-[a-z0-9-]+\.py)",
                           re.DOTALL)

# Checked before the regex runs, so arbitrary tool output is never handed to a pattern.
HOOK_ERROR_MARKER = "hook error:"

# Tool inputs are dropped wholesale except these. See CONTAINMENT above.
PATH_FIELDS = ("file_path", "notebook_path")

# Tools whose only interesting payload is a path.
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Read")

# Tools that mutate the filesystem or the outside world. Separated because "what was
# written" is the question an audit asks, and "what was read" is a much longer list.
MUTATING_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def parse_iso(value):
    """Parse an ISO timestamp, tolerating a trailing Z. Returns None on anything else."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def first_token(command):
    """The executable name from a Bash command, and nothing else.

    Deliberately crude. `cd /x && grep <content>` yields "cd". Losing the rest is
    the point -- see CONTAINMENT. Returns None rather than guessing on odd input.
    """
    if not isinstance(command, str):
        return None
    stripped = command.strip()
    if not stripped:
        return None
    token = stripped.split()[0]
    # Strip an env-var prefix like FOO=bar so the report groups on the real binary.
    if "=" in token and "/" not in token:
        parts = stripped.split()
        for part in parts:
            if "=" not in part:
                token = part
                break
    return os.path.basename(token)[:40]


class SessionReport:
    """Everything this script is willing to say about one transcript."""

    def __init__(self, path):
        self.path = path
        self.session_id = path.stem
        self.project = path.parent.name
        self.tools = collections.Counter()
        self.mcp = collections.defaultdict(collections.Counter)
        self.skills = collections.Counter()
        self.binaries = collections.Counter()
        self.files_written = collections.Counter()
        self.files_read = collections.Counter()
        self.denials = collections.Counter()
        # Guard filename -> times it REFUSED a call. Absence is not innocence; a guard
        # that allowed leaves nothing. See hazard 1.
        self.guards_fired = collections.Counter()
        self.guard_tools = collections.Counter()
        # A `hook error:` that named no refuse-*.py. Counted so an unrecognised hook, or
        # a guard renamed out from under this regex, cannot vanish silently.
        self.unnamed_hook_errors = 0
        # From `type == "system"` records. Never yet observed non-empty; counted so that
        # the first crashed guard is not missed. This is the fails-open channel.
        self.hook_error_records = 0
        self.prevented_continuations = 0
        self.modes = []
        self.models = collections.Counter()
        self.branches = set()
        self.cwds = set()
        self.versions = set()
        self.compactions = 0
        self.sidechain_records = 0
        self.cost_usd = None
        self.lines_added = None
        self.lines_removed = None
        self.duration_ms = None
        self.first_ts = None
        self.last_ts = None
        self.malformed_lines = 0
        self.total_lines = 0
        self.user_turns = 0

    # -- ingest ----------------------------------------------------------------

    def observe_timestamp(self, record):
        stamp = parse_iso(record.get("timestamp"))
        if stamp is None:
            return
        if self.first_ts is None or stamp < self.first_ts:
            self.first_ts = stamp
        if self.last_ts is None or stamp > self.last_ts:
            self.last_ts = stamp

    def observe_tool_use(self, block):
        name = block.get("name")
        if not isinstance(name, str):
            return
        self.tools[name] += 1
        raw_input = block.get("input")
        if not isinstance(raw_input, dict):
            return

        if name == "Bash":
            binary = first_token(raw_input.get("command"))
            if binary:
                self.binaries[binary] += 1
            return

        for field in PATH_FIELDS:
            value = raw_input.get(field)
            if isinstance(value, str) and value:
                if name in MUTATING_TOOLS:
                    self.files_written[value] += 1
                elif name in FILE_TOOLS:
                    self.files_read[value] += 1

    def ingest(self, record):
        self.observe_timestamp(record)
        kind = record.get("type")

        if record.get("isSidechain"):
            self.sidechain_records += 1

        for attr, bucket in (("gitBranch", self.branches), ("cwd", self.cwds),
                             ("version", self.versions)):
            value = record.get(attr)
            if isinstance(value, str) and value:
                bucket.add(value)

        skill = record.get("attributionSkill")
        if skill:
            self.skills[str(skill)] += 1

        server = record.get("attributionMcpServer")
        tool = record.get("attributionMcpTool")
        if isinstance(server, str) and server:
            self.mcp[server][tool if isinstance(tool, str) else "<unnamed>"] += 1

        denial = record.get("toolDenialKind")
        if denial:
            self.denials[str(denial)] += 1

        # The one tool-result read in this file, bounded per CONTAINMENT. A dict result
        # -- Bash stdout, MCP payloads, file contents -- is deliberately not reached.
        result = record.get("toolUseResult")
        if isinstance(result, str) and HOOK_ERROR_MARKER in result:
            match = GUARD_REFUSAL.search(result)
            if match:
                self.guard_tools[match.group(1)] += 1
                self.guards_fired[match.group(2)] += 1
            else:
                self.unnamed_hook_errors += 1

        if kind == "system":
            errors = record.get("hookErrors")
            if isinstance(errors, list) and errors:
                self.hook_error_records += 1
            if record.get("preventedContinuation"):
                self.prevented_continuations += 1

        if kind == "permission-mode":
            mode = record.get("permissionMode")
            if isinstance(mode, str) and (not self.modes or self.modes[-1] != mode):
                self.modes.append(mode)

        if kind == "user" and record.get("promptSource") == "typed":
            self.user_turns += 1

        if kind == "system" and record.get("subtype") == "compact_boundary":
            self.compactions += 1

        if kind == "cost-state":
            # Later cost-state records supersede earlier ones; they are cumulative.
            for attr, key in (("cost_usd", "totalCostUSD"),
                              ("lines_added", "totalLinesAdded"),
                              ("lines_removed", "totalLinesRemoved"),
                              ("duration_ms", "totalDuration")):
                value = record.get(key)
                if isinstance(value, (int, float)):
                    setattr(self, attr, value)
            usage = record.get("modelUsage")
            if isinstance(usage, dict):
                for model in usage:
                    self.models[model] += 1

        message = record.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        self.observe_tool_use(block)

    # -- query -----------------------------------------------------------------

    @property
    def mcp_servers(self):
        return sorted(self.mcp)

    def touched_tool(self, needle):
        needle = needle.lower()
        return any(needle in name.lower() for name in self.tools)

    def touched_mcp(self, needle):
        needle = needle.lower()
        return any(needle in server.lower() for server in self.mcp)

    def touched_guard(self, needle):
        needle = needle.lower()
        return any(needle in guard.lower() for guard in self.guards_fired)


def read_session(path):
    report = SessionReport(path)
    try:
        handle = path.open(errors="replace")
    except OSError as exc:
        print(f"  ! could not read {path}: {exc}", file=sys.stderr)
        return report
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            report.total_lines += 1
            try:
                record = json.loads(line)
            except (ValueError, TypeError):
                report.malformed_lines += 1
                continue
            if isinstance(record, dict):
                report.ingest(record)
    return report


def discover(project=None):
    if not PROJECTS_ROOT.is_dir():
        return []
    if project:
        roots = [PROJECTS_ROOT / project]
    else:
        roots = [p for p in PROJECTS_ROOT.iterdir() if p.is_dir()]
    found = []
    for root in roots:
        if root.is_dir():
            found.extend(sorted(root.glob("*.jsonl")))
    return found


def fmt_duration(ms):
    """Format `totalDuration`, which is WALL-CLOCK SPAN, not time worked.

    A session left open overnight reports 24h+. Real sessions in this corpus report
    spans over 120 hours. Never read this as effort or as billable time; it is only
    useful for spotting a session that stayed open far longer than you thought.
    """
    if not isinstance(ms, (int, float)) or ms <= 0:
        return "—"
    minutes, seconds = divmod(int(ms // 1000), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"


def fmt_day(stamp):
    return stamp.strftime("%Y-%m-%d %H:%M") if stamp else "unknown"


def emit(report, out, summary_only=False, top=12):
    header = f"{fmt_day(report.first_ts)}  {report.session_id[:8]}  {report.project}"
    bits = [f"{sum(report.tools.values())} calls"]
    if report.cost_usd is not None:
        bits.append(f"${report.cost_usd:.2f}")
    if report.duration_ms:
        bits.append(fmt_duration(report.duration_ms) + " open")
    if report.files_written:
        bits.append(f"{len(report.files_written)} files written")
    if report.denials:
        bits.append(f"{sum(report.denials.values())} denied")
    if report.guards_fired:
        bits.append(f"{sum(report.guards_fired.values())} guard refusals")
    if report.compactions:
        bits.append(f"{report.compactions}x compacted")
    print(f"{header}  |  {' · '.join(bits)}", file=out)

    if summary_only:
        return

    def line(label, value):
        print(f"      {label:<22} {value}", file=out)

    if report.modes:
        line("permission mode", " → ".join(report.modes))
    if report.branches:
        line("git branch", ", ".join(sorted(report.branches)[:4]))
    if report.cwds:
        line("cwd", ", ".join(sorted(report.cwds)[:3]))
    if report.models:
        line("model", ", ".join(sorted(report.models)))
    if report.user_turns:
        line("typed turns", report.user_turns)
    if report.lines_added is not None or report.lines_removed is not None:
        line("lines", f"+{report.lines_added or 0} / -{report.lines_removed or 0}")

    if report.tools:
        top_tools = ", ".join(f"{n}×{c}" for n, c in report.tools.most_common(top))
        line("tools", top_tools)
    if report.binaries:
        top_bins = ", ".join(f"{n}×{c}" for n, c in report.binaries.most_common(top))
        line("bash binaries", top_bins)
    if report.mcp:
        for server in report.mcp_servers:
            tools = report.mcp[server]
            detail = ", ".join(f"{n}×{c}" for n, c in tools.most_common(6))
            line(f"mcp {server}", detail)
    if report.skills:
        line("skills", ", ".join(f"{n}×{c}" for n, c in report.skills.most_common(top)))
    if report.denials:
        line("DENIED", ", ".join(f"{n}×{c}" for n, c in report.denials.most_common()))
    if report.guards_fired:
        line("GUARDS FIRED",
             ", ".join(f"{n}×{c}" for n, c in report.guards_fired.most_common()))
        line("  on tool", ", ".join(f"{n}×{c}" for n, c in report.guard_tools.most_common()))
    if report.unnamed_hook_errors:
        line("hook errors, unnamed",
             f"{report.unnamed_hook_errors} (a hook refused but named no refuse-*.py — "
             f"check whether a guard was renamed)")
    if report.hook_error_records:
        line("HOOK ERRORS",
             f"{report.hook_error_records} system record(s) with a non-empty hookErrors "
             f"— a hook FAILED; registration fails open, so treat as a disarmed guard")
    if report.prevented_continuations:
        line("prevented continuation", report.prevented_continuations)
    if report.sidechain_records:
        line("sidechain records", f"{report.sidechain_records} (subagent work; counts are a lower bound)")
    if report.malformed_lines:
        line("malformed lines", f"{report.malformed_lines} of {report.total_lines}")

    if report.files_written:
        print("      files written:", file=out)
        for path, count in report.files_written.most_common(top):
            suffix = f"  ({count}×)" if count > 1 else ""
            print(f"        {path}{suffix}", file=out)
        extra = len(report.files_written) - top
        if extra > 0:
            print(f"        … and {extra} more", file=out)
    print(file=out)


CAVEAT_BLOCK = """
────────────────────────────────────────────────────────────────────────────
WHAT THIS REPORT CANNOT SHOW  (printed every run, on purpose)

  * A GUARD THAT BLOCKED IS SHOWN. A GUARD THAT ALLOWED IS NOT. Refusals are named
    above, per guard. But a guard that ran and permitted the call leaves no record, so
    "no guard refusals" cannot tell you whether nothing was refused or nothing was
    attempted. A quiet report is NOT evidence the guards were never needed.
  * A CRASHED GUARD IS PROVEN INVISIBLE. Measured 2026-10-02 with a two-arm scratch
    config: a hook that EXITS 2 is recorded and named; a hook that CRASHES writes
    NOTHING AT ALL -- no denial, no hookErrors, no trace -- and the command runs. A
    disarmed guard is byte-for-byte indistinguishable here from no guard configured.
    `hookErrors` is read and reported anyway, against the day that changes.
    **Only `verify-hooks.py` can detect a disarmed guard, and it has to be RUN.**
  * A ZERO DENIAL COUNT IS AMBIGUOUS. It says nothing about your permission deny
    rules, which have never appeared in a transcript denial record. Zero is not a pass.
  * COUNTS ARE NOT A TREND. The retained corpus turns over while you work; two reads
    minutes apart have disagreed. Do not compare a figure to one quoted last week.
  * CALLS, NOT EFFECTS. A recorded Write does not prove the bytes are on disk now.
  * SUBAGENT WORK IS UNDER-COUNTED wherever Agent or Workflow appears.

THIS OUTPUT IS LOCAL-ONLY. It names file paths, and a path can disclose what it points
at. Never paste it anywhere outward-facing.
────────────────────────────────────────────────────────────────────────────
"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Report what Claude Code sessions actually did.",
        epilog="A clean report is not a pass. See the caveat block it prints.",
    )
    parser.add_argument("--days", type=int, default=None,
                        help="only sessions whose last activity is within N days "
                             "(may filter nothing -- see hazard 4 in the docstring)")
    parser.add_argument("--session", default=None, help="session id or prefix")
    parser.add_argument("--project", default=None, help="project directory name")
    parser.add_argument("--tool", default=None, help="only sessions that used this tool")
    parser.add_argument("--mcp", default=None, help="only sessions that touched this MCP server")
    parser.add_argument("--guard", default=None,
                        help="only sessions where a guard REFUSED a call, matched on the "
                             "guard filename (e.g. egress, staging). Finding none does "
                             "not mean none was needed -- see hazard 1")
    parser.add_argument("--summary", action="store_true", help="one line per session")
    parser.add_argument("--top", type=int, default=12, help="entries per list (default 12)")
    parser.add_argument("--out", default=None, help="write to a file instead of stdout")
    args = parser.parse_args(argv)

    paths = discover(args.project)
    if args.session:
        paths = [p for p in paths if p.stem.startswith(args.session)]

    if not paths:
        print("No transcripts matched. This means the FILTER found nothing, not that "
              "nothing happened.", file=sys.stderr)
        return 0

    reports = [read_session(p) for p in paths]

    cutoff = None
    if args.days is not None:
        newest = max((r.last_ts for r in reports if r.last_ts), default=None)
        if newest is not None:
            cutoff = newest - dt.timedelta(days=args.days)
            reports = [r for r in reports if r.last_ts and r.last_ts >= cutoff]

    if args.tool:
        reports = [r for r in reports if r.touched_tool(args.tool)]
    if args.mcp:
        reports = [r for r in reports if r.touched_mcp(args.mcp)]
    if args.guard:
        reports = [r for r in reports if r.touched_guard(args.guard)]

    reports.sort(key=lambda r: r.first_ts or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                 reverse=True)

    out = open(args.out, "w") if args.out else sys.stdout
    try:
        stamps = [r.first_ts for r in reports if r.first_ts]
        print(f"SESSION REPORT — {len(reports)} session(s) of {len(paths)} scanned", file=out)
        if stamps:
            print(f"oldest seen: {fmt_day(min(stamps))}   newest seen: {fmt_day(max(stamps))}",
                  file=out)
            if args.days is not None:
                span = (max(stamps) - min(stamps)).days
                print(f"--days {args.days} requested; actual span of retained data is "
                      f"{span} day(s) — the window bit only if {span} < {args.days} is false.",
                      file=out)
        print(file=out)

        for report in reports:
            emit(report, out, summary_only=args.summary, top=args.top)

        totals = collections.Counter()
        mcp_totals = collections.Counter()
        denial_totals = collections.Counter()
        guard_totals = collections.Counter()
        hook_failures = 0
        written = set()
        cost = 0.0
        for report in reports:
            totals.update(report.tools)
            for server, tools in report.mcp.items():
                mcp_totals[server] += sum(tools.values())
            denial_totals.update(report.denials)
            guard_totals.update(report.guards_fired)
            hook_failures += report.hook_error_records
            written.update(report.files_written)
            cost += report.cost_usd or 0.0

        print("ACROSS ALL MATCHED SESSIONS", file=out)
        print(f"  tool calls        {sum(totals.values())}", file=out)
        print(f"  distinct files written  {len(written)}", file=out)
        print(f"  cost (recorded)   ${cost:.2f}", file=out)
        if mcp_totals:
            print("  mcp servers       "
                  + ", ".join(f"{s}×{c}" for s, c in mcp_totals.most_common()), file=out)
        print("  denials recorded  "
              + (", ".join(f"{k}×{v}" for k, v in denial_totals.most_common())
                 if denial_totals else "0  ← ambiguous, see caveats"), file=out)
        print("  guards fired      "
              + (", ".join(f"{k}×{v}" for k, v in guard_totals.most_common())
                 if guard_totals
                 else "0  ← means nothing was refused OR nothing was tried"), file=out)
        print(f"  hook failures     {hook_failures}"
              + ("" if hook_failures else "  ← never yet observed; not proof of none"),
              file=out)
        print(CAVEAT_BLOCK, file=out)
    finally:
        if args.out:
            out.close()
            print(f"Wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

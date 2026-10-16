#!/usr/bin/env python3
"""Tests for session-report.py.

THE LOAD-BEARING TEST IS `test_sentinel_never_escapes`. Everything else here checks
that the report is useful; that one checks that the report is not itself the leak.
A monitoring tool that prints everything it can see will print the thing an assertion
deliberately withheld -- the `--showlocals` hazard, applied to an audit script.

Run:  python3 -m pytest test_session_report.py -q
      python3 test_session_report.py          # no pytest needed
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
# The script under test lives in tools/, not beside this file. Resolved explicitly
# because getting this wrong does not fail a test -- it fails the IMPORT, and a suite
# that cannot load reports nothing rather than reporting a failure.
SCRIPT = HERE.parent / "tools" / "session-report.py"

_spec = importlib.util.spec_from_file_location("session_report", SCRIPT)
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)

# A string that must never appear in output. Stands in for any unpublished content
# that passes through a tool call -- a document body, a record, a customer detail.
SENTINEL = "ZZQQ_UNPUBLISHED_CONTENT_ZZQQ"


def build_transcript(path):
    """A transcript that puts SENTINEL everywhere content really travels."""
    records = [
        {"type": "permission-mode", "permissionMode": "default", "sessionId": "s1"},
        # 1. A tool RESULT -- stored as type "user". The primary hazard.
        {"type": "user", "timestamp": "2026-09-28T10:00:00Z",
         "toolUseResult": {"stdout": SENTINEL},
         "message": {"role": "user", "content": [
             {"type": "tool_result", "content": SENTINEL}]}},
        # 2. A typed prompt.
        {"type": "user", "promptSource": "typed", "timestamp": "2026-09-28T10:01:00Z",
         "message": {"role": "user", "content": f"please review {SENTINEL}"}},
        # 3. A Write whose CONTENT is unpublished but whose path is benign.
        {"type": "assistant", "timestamp": "2026-09-28T10:02:00Z", "gitBranch": "main",
         "cwd": "/Users/dev/projects/example-mcp", "version": "2.1.0",
         "message": {"role": "assistant", "content": [
             {"type": "thinking", "thinking": SENTINEL},
             {"type": "text", "text": SENTINEL},
             {"type": "tool_use", "name": "Write", "input": {
                 "file_path": "/tmp/findings.md", "content": SENTINEL}}]}},
        # 4. A Bash command carrying content in a grep pattern.
        {"type": "assistant", "timestamp": "2026-09-28T10:03:00Z",
         "message": {"role": "assistant", "content": [
             {"type": "tool_use", "name": "Bash", "input": {
                 "command": f"grep -r '{SENTINEL}' /data && echo done"}}]}},
        # 4b. A Bash command with the content LAST and no '/' after it. MEASURED
        # 2026-10-16: without this record `test_sentinel_never_escapes` passed under a
        # mutant that returned the whole command, because the other Bash fixture happens
        # to carry `/data` after the sentinel and `os.path.basename` discarded it. The
        # test was resting on the fixture's shape rather than on the containment.
        {"type": "assistant", "timestamp": "2026-09-28T10:03:30Z",
         "message": {"role": "assistant", "content": [
             {"type": "tool_use", "name": "Bash", "input": {
                 "command": f"echo {SENTINEL}"}}]}},
        # 5. An MCP call on a content-handling server, args carrying content.
        {"type": "assistant", "timestamp": "2026-09-28T10:04:00Z",
         "attributionMcpServer": "ledger", "attributionMcpTool": "fetch_entry",
         "message": {"role": "assistant", "content": [
             {"type": "tool_use", "name": "mcp__ledger__fetch_entry",
              "input": {"query": SENTINEL, "tags": [SENTINEL]}}]}},
        # 6. A skill attribution and a denial.
        {"type": "assistant", "timestamp": "2026-09-28T10:05:00Z",
         "attributionSkill": "coding-standards", "toolDenialKind": "user-rejected",
         "message": {"role": "assistant", "content": [
             {"type": "tool_use", "name": "Read",
              "input": {"file_path": "/Users/dev/data/confidential-records.json"}}]}},
        # 6b. A GUARD REFUSAL, as the transcript really records one -- and with SENTINEL
        # planted in the refusal body, because a guard's message is composed text and a
        # future edit to one could put real content there. The guard name must be
        # reported; everything around it must not.
        {"type": "user", "timestamp": "2026-09-28T10:05:30Z",
         "toolDenialKind": "permission-rule",
         "toolUseResult": (
             "Error: PreToolUse:Bash hook error: [/usr/bin/python3 "
             "/Users/dev/.claude/hooks/refuse-dangerous-staging.py]: REFUSED by "
             f"~/.claude/hooks/refuse-dangerous-staging.py\n\n{SENTINEL}\n"),
         "message": {"role": "user", "content": [
             {"type": "tool_result", "content": SENTINEL}]}},
        # 6c. A hook error naming no guard -- must be counted, never dropped.
        {"type": "user", "timestamp": "2026-09-28T10:05:45Z",
         "toolUseResult": f"Error: PreToolUse:Write hook error: something {SENTINEL}"},
        # 6d. A system record carrying a FAILED hook. This is the fails-open channel.
        {"type": "system", "timestamp": "2026-09-28T10:05:50Z",
         "hookCount": 1, "hookErrors": [{"command": "callback"}],
         "preventedContinuation": True},
        {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-09-28T10:06:00Z"},
        {"type": "assistant", "isSidechain": True, "timestamp": "2026-09-28T10:07:00Z",
         "message": {"role": "assistant", "content": [
             {"type": "tool_use", "name": "Agent", "input": {"prompt": SENTINEL}}]}},
        {"type": "cost-state", "totalCostUSD": 1.25, "totalLinesAdded": 40,
         "totalLinesRemoved": 3, "totalDuration": 425000,
         "modelUsage": {"us.anthropic.claude-opus-5": {"inputTokens": 5}}},
    ]
    with path.open("w") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")
        fh.write("this line is not json\n")
        fh.write("\n")


def render(path, **kwargs):
    report = sr.read_session(path)
    buf = io.StringIO()
    sr.emit(report, buf, **kwargs)
    return report, buf.getvalue()


def test_sentinel_never_escapes():
    """No content field reaches the output. The whole point of the script."""
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "abcd1234.jsonl"
        build_transcript(path)
        report, text = render(path)
        assert SENTINEL not in text, "content leaked into the report"
        # And not via the summary form either.
        _, summary = render(path, summary_only=True)
        assert SENTINEL not in summary
        # Nor into any collected structure, so a future --json cannot leak it.
        blob = json.dumps({
            "tools": report.tools, "binaries": report.binaries,
            "files_written": report.files_written, "files_read": report.files_read,
            "mcp": {k: dict(v) for k, v in report.mcp.items()},
            "skills": report.skills, "denials": report.denials,
            "modes": report.modes, "cwds": sorted(report.cwds),
            "guards_fired": report.guards_fired, "guard_tools": report.guard_tools,
        })
        assert SENTINEL not in blob, "content leaked into a collected field"


def test_guard_refusal_is_named_without_leaking_its_body():
    """The load-bearing test for the one tool-result read this file permits.

    A guard's refusal is composed text. A guard that builds its reason from field
    names alone is safe to read today, but nothing stops a future edit putting real
    content in a message -- so the guard NAME must come through and the body must not,
    even when the body contains content.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "abcd1234.jsonl"
        build_transcript(path)
        report, text = render(path)
        assert report.guards_fired["refuse-dangerous-staging.py"] == 1
        assert report.guard_tools["Bash"] == 1
        assert "refuse-dangerous-staging.py" in text
        assert "GUARDS FIRED" in text
        assert SENTINEL not in text, "a guard's refusal body leaked"


def test_a_dict_tool_result_is_never_read():
    """A dict result is Bash stdout, an MCP payload, a file read. Must not be reached."""
    report = sr.SessionReport(pathlib.Path("x.jsonl"))
    report.ingest({"type": "user",
                   "toolUseResult": {"stdout": f"hook error: {SENTINEL}"}})
    assert not report.guards_fired
    assert report.unnamed_hook_errors == 0, "a dict result was parsed"


def test_unnamed_hook_error_is_counted_not_dropped():
    """A guard renamed out from under the regex must not vanish silently."""
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "abcd1234.jsonl"
        build_transcript(path)
        report, text = render(path)
        assert report.unnamed_hook_errors == 1
        assert "unnamed" in text


def test_failed_hook_is_surfaced_as_a_disarmed_guard():
    """Registration fails open, so a hook ERROR must read as a disarmed control."""
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "abcd1234.jsonl"
        build_transcript(path)
        report, text = render(path)
        assert report.hook_error_records == 1
        assert report.prevented_continuations == 1
        assert "HOOK ERRORS" in text
        assert "disarmed" in text


def test_zero_guards_fired_is_labelled_ambiguous():
    """`0 guards fired` must never read as `the guards were not needed`."""
    src = SCRIPT.read_text()
    assert "nothing was refused OR nothing was tried" in src
    assert "A GUARD THAT ALLOWED IS NOT" in src


def test_bash_keeps_only_the_binary():
    assert sr.first_token(f"grep -r '{SENTINEL}' /banks && echo done") == "grep"
    assert sr.first_token("/usr/bin/python3 script.py") == "python3"
    assert sr.first_token("FOO=bar python3 x.py") == "python3"
    assert sr.first_token("   ") is None
    assert sr.first_token(None) is None


def test_reports_the_facts_it_should():
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "abcd1234.jsonl"
        build_transcript(path)
        report, text = render(path)
        assert report.tools["Write"] == 1
        assert report.tools["Bash"] == 2
        assert report.binaries["grep"] == 1
        assert report.binaries["echo"] == 1
        assert "/tmp/findings.md" in report.files_written
        assert "/Users/dev/data/confidential-records.json" in report.files_read
        assert report.mcp["ledger"]["fetch_entry"] == 1
        assert report.skills["coding-standards"] == 1
        assert report.denials["user-rejected"] == 1
        assert report.compactions == 1
        assert report.sidechain_records == 1
        assert report.user_turns == 1
        assert report.cost_usd == 1.25
        assert report.modes == ["default"]
        assert "ledger" in text
        assert "fetch_entry" in text


def test_write_is_written_read_is_read():
    """A Read must not be reported as a write. An audit that conflates them is useless."""
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "abcd1234.jsonl"
        build_transcript(path)
        report, _ = render(path)
        assert "/Users/dev/data/confidential-records.json" not in report.files_written
        assert "/tmp/findings.md" not in report.files_read


def test_malformed_lines_counted_not_fatal():
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "abcd1234.jsonl"
        build_transcript(path)
        report, _ = render(path)
        assert report.malformed_lines == 1
        assert report.total_lines > 1


def test_caveats_are_unconditional():
    """The caveat block must not be suppressible -- a clean report must carry its limits."""
    # Corrected 2026-10-02: the block used to claim hooks were invisible entirely. It
    # must now carry BOTH halves -- what a refusal proves, and what it does not.
    assert "A GUARD THAT BLOCKED IS SHOWN" in sr.CAVEAT_BLOCK
    assert "A GUARD THAT ALLOWED IS NOT" in sr.CAVEAT_BLOCK
    assert "A CRASHED GUARD IS PROVEN INVISIBLE" in sr.CAVEAT_BLOCK
    # The measured conclusion must survive edits: nothing passive can catch a disarmed
    # guard, so the block has to name the tool that can.
    assert "verify-hooks.py" in sr.CAVEAT_BLOCK
    assert "HOOKS ARE INVISIBLE" not in sr.CAVEAT_BLOCK, "the falsified claim is back"
    assert "ZERO DENIAL COUNT IS AMBIGUOUS" in sr.CAVEAT_BLOCK
    assert "LOCAL-ONLY" in sr.CAVEAT_BLOCK
    src = SCRIPT.read_text()
    # Exactly one print of the block, and no flag that skips it.
    assert src.count("CAVEAT_BLOCK") == 2  # definition + the single print
    assert "--no-caveats" not in src


def test_empty_result_does_not_claim_cleanliness():
    """`No transcripts matched` must say the filter found nothing, not that nothing ran."""
    src = SCRIPT.read_text()
    assert "not that" in src and "nothing happened" in src


def test_zero_denials_labelled_ambiguous():
    src = SCRIPT.read_text()
    assert "ambiguous, see caveats" in src


def test_no_network_and_no_memory_writes():
    """Containment by inspection: this script must not reach the network or memory."""
    src = SCRIPT.read_text()
    for banned in ("requests", "urllib", "socket", "httpx", "subprocess", "os.system"):
        assert banned not in src, f"{banned} must not appear"
    # It must never write into the memory directory.
    assert "memory" not in src, "it must never touch the memory directory"
    assert '"projects"' in src, "it does need to READ the transcript root"
    # It may only open a transcript to read, and one file the user named with --out.
    assert src.count("open(") <= 3


def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"pass {test.__name__}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())

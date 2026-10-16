# Privacy

**This plugin collects nothing, sends nothing, and reads no credentials.** That is a
claim you can check rather than take on trust, and this page says how.

## What it contains

- **Eleven skills** — Markdown files. Claude reads them. They execute nothing.
- **One `PreToolUse` hook**, `hooks/refuse-dangerous-staging.py`. It receives the
  pending Bash command as JSON on standard input, decides whether that command is a
  blanket `git` stage, and exits 0 to allow or 2 to refuse. It writes its reason to
  standard error. It opens no files, reads no environment variables, and sends nothing
  anywhere.
- **Two tools you run yourself**, never automatically: `tools/verify-hooks.py` reads your
  settings files and installed plugins to report which hooks could actually run, and
  `tools/session-report.py` reads Claude Code's own transcript files to report what a
  finished session did and cost. Both print to your terminal.
- **Templates** — files you copy by hand into your own repositories.

## No network access

No file in this plugin opens a socket, and none can. The check is one line:

```
grep -rnE '^\s*(import|from)\s+(requests|urllib|socket|http|httpx|ftplib|smtplib)|subprocess|os\.system|os\.popen|curl|wget' .
```

It matches exactly three things, none of them an import: the test in
`tests/test_session_report.py` that asserts those names are absent, one sentence of prose
in `skills/coding-standards/SKILL.md`, and the line above in this file. No shipped file
imports any of them. There is no telemetry, no analytics, no update check, and no remote
configuration.

## No credentials

Nothing here reads a token, an API key, or a cloud credential. The shipped
`settings.json` template deliberately sets no `env` block, so installing this plugin does
not change how Claude Code authenticates.

## What leaves your machine: nothing

`session-report.py` and `verify-hooks.py` both print **local file paths**, and a path can
disclose what it points at. Their output is therefore for you to read, not to share — both
say so in their own documentation. Neither transmits anything; the caution is about what
*you* might paste somewhere afterwards.

## Reporting a problem

Open an issue: https://github.com/julie-elkins/fail-closed/issues

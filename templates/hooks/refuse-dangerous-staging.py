#!/usr/bin/env /usr/bin/python3
"""Refuse the one mistake a repository cannot take back.

TEMPLATE. The blanket-staging refusal below is universal and works as shipped. The
REPO_HAZARDS section is a stub you fill in per repository -- see "Adding a hazard".

WHY A HOOK RATHER THAN A HABIT. "Stage by path, never `git add -A`" is a rule in
several CLAUDE.md files, and the discipline has generally held. But a habit that has
held is not a control, and the failure a habit misses looks like this: in one repo a
file named `demo.salt.moved-aside` did not match `.gitignore`'s `*.salt`, so a run
killed inside a rename window would have left an un-ignored secret beside its own
store, ready for the next careless stage. That was caught by running
`git check-ignore -v`, not by reasoning about the pattern. This file is the same move
one layer out: a check that runs, rather than a rule that is remembered.

WHY NOT A GIT HOOK. On a managed machine `core.hooksPath` is often already pointed at
a corporate hooks directory, so a repo-local `.git/hooks/pre-commit` never runs -- and
overriding `core.hooksPath` to fix that disables whatever was relying on it, which is a
worse trade than the problem. A Claude Code `PreToolUse` hook sits in a different place
entirely and does not compete for that setting.

THE TWO HALVES ANSWER DIFFERENT QUESTIONS AND SO THEY MATCH DIFFERENTLY. This is the
one design point in the file worth reading before changing anything.

"Is this command a blanket stage?" is a question about STRUCTURE: it depends on which
token is the command word, which is a subcommand, and which are pathspecs. A regex
over the whole string cannot answer it, and MEASURED 2026-09-22 this file's previous
version got eight real blanket stages wrong in the admitting direction -- `git add ./`,
`git add -- .`, `git add :/`, `git add '*'`, `git stage -A`, `git stage .`, `git add -u`
and `git add --update` all exited 0. Not eight oversights; one design mismatch, eight
symptoms. So the blanket half TOKENISES (`_segments` and below) and a `git` token
counts only when it is the command word of a shell segment.

"Does this command name hazardous material anywhere?" is a question about MENTION, and
a regex over the whole string is the right tool for it. So REPO_HAZARDS still matches
that way, and OVER-REFUSAL THERE IS THE SAFE DIRECTION AND IS NOT AN APOLOGY: a
command that merely mentions a hazardous path in a comment or a `--help` argument is
refused too. The cost of a false refusal is one sentence and a rephrased command; the
cost of a false admit can be unrecoverable. Each refusal names its rule and the
cheaper thing to do instead, so a false positive is self-diagnosing rather than
mysterious.

Do not "simplify" by making one half match like the other. Tokenising the hazard half
would admit a secret path inside a quoted string; regexing the blanket half puts the
eight admits back.

WHAT THIS HOOK CANNOT DO, stated so it is not over-read. It sees the command an agent
is about to run in this repository through the Bash tool. It does NOT see your own
terminal, does not see the Write or Edit tools, and cannot stop `git add -f` against a
path it does not recognise. It does not read HEREDOC BODIES, so `bash <<'EOF'` with
`git add -A` inside the body is not inspected by the blanket half -- that is the price
of not refusing the commit message that documents this rule, and `_segments` makes the
trade deliberately. It narrows the surface; it does not close it. Keep `.gitignore`
underneath it.

COMMIT IT AS `.claude/settings.json`, NOT `settings.local.json`. A control that exists
only on the author's laptop mitigates the bus factor for exactly one person, which is
the problem this kit exists to fix.

VERIFY IT IN THE SHAPE A CALLER ACTUALLY WRITES, WHICH MEANS MULTI-LINE. A sibling
hook built on the same tokeniser was bypassable by any multi-line script for twelve
days, and it survived because every probe written to check it was a single line. The
`\\n`-in-punctuation handling in `_segments` is what closes that, and a one-line probe
cannot tell you whether it is still there.

Contract: reads the PreToolUse JSON on stdin, exits 0 to allow and 2 to refuse with
the reason on stderr. Any unexpected input shape exits 0 -- a guard that crashes must
not become a guard that blocks every command.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

# --------------------------------------------------------------------------------
# 1. BLANKET STAGING -- universal, no configuration needed.
#
# Refused not because these are wrong in general but because knowing what is in the
# tree is the premise of every containment argument, and a blanket stage is the one
# operation that adds a file nobody named. `git commit -a` is included deliberately:
# it stages every tracked modification, so it bypasses staging-by-path without ever
# calling `git add`.
#
# Four things the tokeniser buys that a regex over the string did not:
#
#   - `git stage` is a real alias for `git add` (`git-stage(1)`), and it appears in
#     no pattern anyone writes by hand.
#   - `git -C <path> add -A` and `cd sub && git add -A` both escape a pattern
#     anchored on `git add`, and a `permissions.deny` entry anchored at the start of
#     the command string does not see them either.
#   - `git add -- .` puts a blanket pathspec behind the end-of-options marker, where
#     it stops looking like a flag.
#   - NAMED PATHS ARE THE POINT, so `git add .gitignore` MUST SURVIVE. That is why
#     the pathspec test is exact-match on a token and never a prefix: the obvious
#     `git add .*` deny rule also refuses `git add .gitignore` and
#     `git add .python-version`, which inverts the rule it was meant to enforce.
# --------------------------------------------------------------------------------

# Segment separators, as TOKENS rather than as a regex over the raw string. Splitting
# the string on `|` cuts through a quoted grep pattern, so
# `grep -ril 'git add -A|git add --all' .` would yield a fragment whose command word
# is `git` and whose argument is `-A'` -- the guard refusing the audit that looks for
# it. A guard that fires on the work of auditing the guard gets switched off.
#
# A NEWLINE IS A SEPARATOR AND SHLEX WILL NOT HAND YOU ONE. With
# `whitespace_split = True`, shlex treats `\n` as ordinary whitespace and never emits
# it as a token, so `echo probing\ngit add -A` lexes to a SINGLE segment whose command
# word is `echo`. The fix moves `\n` out of the lexer's whitespace and into its
# punctuation. Doing that INSIDE the lexer rather than by pre-splitting the string is
# what keeps the audit allowed: a newline inside a quoted string stays inside its
# token, so `git commit -m "...git add -A..."` remains one argument.
PUNCTUATION = "();<>|&\n"
SEPARATORS = frozenset({";", "&&", "||", "|", "&", "&&&", "(", ")", "\n"})

# Runs of separators arrive glued into one token -- a blank line lexes as "\n\n\n"
# -- so membership in SEPARATORS is not enough on its own.
SEPARATOR_CHARS = ";&|()\n"

# A heredoc BODY is data, not commands. See the docstring of `_segments`.
HEREDOC_OPS = frozenset({"<<", "<<-"})

# LAST RESORT BEFORE THE CRUDE FALLBACK. An unbalanced quote anywhere breaks the lex
# of the WHOLE string -- including one inside a heredoc BODY, whose contents this
# tokeniser treats as data anyway. And in English prose an apostrophe IS an
# unbalanced quote: MEASURED 2026-09-22, a commit message written as a `<<'MSG'`
# heredoc, documenting this very rule, containing both "the lexer's punctuation" and
# `cd sub && git add -A`, was REFUSED -- the odd apostrophe count sent it to the crude
# fallback, and the crude fallback splits on the `&&` inside the prose. That is the
# exact failure the heredoc skip exists to prevent, arriving by the one path the skip
# cannot reach, because the skip runs on TOKENS and lexing comes first. So cut the
# bodies out of the raw string and lex what is left. This LOSES NO COVERAGE: a
# heredoc body was never inspected.
HEREDOC_BODY = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1\n.*?\n\2(?=\s|$)", re.DOTALL)

# Fallback only, for a command string `shlex` cannot lex at all (an unbalanced quote).
# Over-refusal is acceptable on input that is not valid shell,
# BUT `shlex` RAISING IS NOT THE SAME THING AS INVALID SHELL -- see HEREDOC_BODY
# above, and reach this fallback only after that retry.
CRUDE_SPLIT = re.compile(r"(?:\|\||&&|[;|&\n()])")

# Leading tokens that precede a real command word without being one. `do` and `then`
# matter more than they look: `for d in */; do git add -A; done` splits on `;` into a
# segment whose first token is `do`, and skipping it is the difference between
# covering a loop body and not.
PREFIXES = frozenset(
    {"do", "then", "else", "elif", "{", "(", "!", "time", "sudo", "env", "nohup",
     "command", "exec", "builtin", "eval"}
)

# Global git options that take a separate value, so the value is not a subcommand.
GIT_OPTS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree",
                                 "--namespace", "--exec-path", "--super-prefix"})

# Pathspecs meaning "everything", matched EXACTLY against a token, and the exactness
# is the named-paths point above: a prefix test here refuses `git add .gitignore`.
#
# `-A` and `--all` are in this set as well as in the flag branch below, and MEASURED by
# mutation 2026-09-22 they are load-bearing for exactly one shape -- `git add -- -A`,
# where the end-of-options marker makes `-A` a FILENAME. It is refused, which is
# over-refusal on a file genuinely called `-A`; stage that one as `./-A`.
#
# `-u` and `--update` were in this set for one draft and were DEAD. They are consumed
# by the flag branch and never reach the pathspec list, so the only shape they changed
# was `git add -- -u`, which is a file named `-u` -- a NAMED PATH, which this guard
# exists to permit. Their removal is what makes the `--` handling in `_add_is_blanket`
# testable at all. `git add -u` and `git add --update` are still refused, by
# `saw_update`. Kept byte-identical to the house-wide guard's set on purpose.
BLANKET_PATHSPECS = frozenset({".", "./", ":/", ":/*", "*", "-A", "--all"})

ADD_ALIASES = frozenset({"add", "stage"})

# --------------------------------------------------------------------------------
# 2. REPO HAZARDS -- fill this in, or delete it.
#
# Each entry is (compiled pattern, rule sentence, remedy paragraph). The remedy is
# the part that earns the hook: name the CHEAPER thing to do, not the rule that was
# broken. An agent that reads "refused: bad path" retries; one that reads "the real
# export stays at $ENV_VAR, the committable fixture is the synthetic one" does the
# right thing on the next call.
#
# These match over the WHOLE command string, deliberately -- see the docstring. A
# mention is the hazard here, so a quoted or commented mention is refused too.
#
# Patterns worth considering, from repos that needed them:
#   - Credential and secret material, even when `.gitignore` already covers it.
#     Keep it REDUNDANT BY DESIGN: the recorded near-miss was a filename that fell
#     outside the ignore pattern while being secret material in every other sense,
#     and a second check keyed on the same INTENT catches the case where the first
#     one's pattern is the thing that is wrong.
#   - Confidential source documents -- exam exports, customer data, real directory
#     records -- matched by extension and by a distinctive name fragment.
#   - Anything reached through an env var precisely so that no committed file
#     contains its path.
#
# Precision matters more than breadth here. A guard that fires on routine work gets
# switched off, and a switched-off control is worth less than a narrow one. Prefer
# two specific markers over one broad one that also matches `grep FOO docs/`.
# --------------------------------------------------------------------------------
REPO_HAZARDS: list[tuple[re.Pattern, str, str]] = [
    # (
    #     re.compile(r"\.mhtml\b|Item[ _]Bank[ _]Field[ _]History", re.IGNORECASE),
    #     "the command names a confidential export",
    #     "That file holds live content and stays outside the repository, reached\n"
    #     "through $YOUR_ENV_VAR. The committable fixture is the SYNTHETIC one,\n"
    #     "built by tests/fixtures/build_synthetic_*.py.",
    # ),
]

# Paths that look hazardous but are the deliberate committed exception -- typically a
# synthetic fixture asserted byte-equal to a committed generator's output.
#
# Checked PER MATCH rather than per command, and that is the whole point: an
# `if EXCEPTION in command` allow-check admits a command naming the exception AND a
# real hazard beside it, which is a false admit in the one direction this file exists
# to prevent.
ALLOWED_EXCEPTIONS: list[str] = [
    # "tests/fixtures/synthetic_export.mhtml",
]


def _lex(command: str) -> list[str]:
    """Tokenise, with newline kept as a separator. Raises on an unbalanced quote."""
    lex = shlex.shlex(command, posix=True, punctuation_chars=PUNCTUATION)
    lex.whitespace = lex.whitespace.replace("\n", "")
    lex.whitespace_split = True
    return list(lex)


def _segments(command: str) -> list[list[str]]:
    """Split into shell segments of tokens, quoting respected.

    An unbalanced quote makes `shlex` raise, and giving up there would mean a
    command that fails to parse is a command that is allowed. The fallback is
    cruder, splits inside quotes, and still sees `-A`.

    HEREDOC BODIES ARE DROPPED, and that is the audit rule rather than laziness.
    `git commit -F - <<'MSG'` followed by a message that quotes `git add -A` is how
    this guard gets DOCUMENTED, and a guard that refuses the commit explaining it is
    a guard that gets deleted. So the tokens between a heredoc delimiter and its
    terminator are data and are not inspected. The cost is named in WHAT THIS HOOK
    CANNOT DO: a heredoc body piped into a shell is not read as commands.
    """
    try:
        tokens = _lex(command)
    except ValueError:
        try:
            tokens = _lex(HEREDOC_BODY.sub(" ", command))
        except ValueError:
            return [
                frag.split() for frag in CRUDE_SPLIT.split(command) if frag.strip()
            ]

    segments: list[list[str]] = []
    current: list[str] = []
    awaiting_delimiter = False
    terminator: str | None = None
    for tok in tokens:
        if terminator is not None:
            if tok == terminator:
                terminator = None
            continue
        if awaiting_delimiter:
            # `<<-EOF` keeps the dash on the delimiter token; bash strips it.
            terminator = tok.lstrip("-")
            awaiting_delimiter = False
            continue
        if tok in HEREDOC_OPS:
            awaiting_delimiter = True
            continue
        if tok in SEPARATORS or (tok and all(c in SEPARATOR_CHARS for c in tok)):
            if current:
                segments.append(current)
            current = []
            continue
        current.append(tok)
    if current:
        segments.append(current)
    return segments


def _command_word_index(tokens: list[str]) -> int | None:
    """Index of the segment's command word, skipping prefixes and VAR=val."""
    for i, tok in enumerate(tokens):
        if tok in PREFIXES:
            continue
        if "=" in tok and not tok.startswith("-") and tok.split("=", 1)[0].isidentifier():
            continue
        return i
    return None


def _git_subcommand(tokens: list[str], start: int) -> tuple[str | None, list[str]]:
    """Return (subcommand, its arguments) for a `git` segment.

    Walks past global options so `git -C ~/projects/foo add -A` is seen as an `add`.
    A global option that takes a value consumes the value, otherwise the value would
    be mistaken for the subcommand.
    """
    i = start + 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in GIT_OPTS_WITH_VALUE:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        return tok, tokens[i + 1 :]

    return None, []


def _short_flag_letters(tok: str) -> str:
    """Letters of a clustered short option, e.g. `-am` -> `am`. `--all` -> ``."""
    if tok.startswith("--") or not tok.startswith("-") or tok == "-":
        return ""
    return tok[1:]


def _add_is_blanket(args: list[str]) -> str | None:
    """Reason this `git add` stages everything, or None if it names paths.

    `--` ends option parsing, so tokens after it are pathspecs even when they start
    with a dash. Tracked separately because `git add -- .` is a blanket stage wearing
    a path-shaped disguise.

    `-u` / `--update` stage TRACKED modifications only, so neither can add a file
    nobody named -- the specific failure this rule exists to prevent. They are
    refused anyway, because they bypass staging-by-path, which is how a modification
    to a file you did not mean to touch this commit rides along. IF ANY REFUSAL HERE
    PROVES ANNOYING ENOUGH TO SWITCH OFF, THIS IS THE ONE TO DROP; drop it
    deliberately rather than by loosening the tokenising above.
    """
    saw_all = False
    saw_update = False
    pathspecs: list[str] = []
    end_of_options = False

    for tok in args:
        if tok == "--" and not end_of_options:
            end_of_options = True
            continue
        if not end_of_options and tok.startswith("-") and tok != "-":
            if tok in ("--all", "--no-ignore-removal"):
                saw_all = True
            elif tok == "--update":
                saw_update = True
            elif not tok.startswith("--"):
                letters = _short_flag_letters(tok)
                if "A" in letters:
                    saw_all = True
                if "u" in letters:
                    saw_update = True
            continue
        pathspecs.append(tok)

    named = [p for p in pathspecs if p not in BLANKET_PATHSPECS]

    if saw_all:
        return "`-A` / `--all` stages every change in the whole work tree"
    for p in pathspecs:
        if p in BLANKET_PATHSPECS:
            return f"the pathspec `{p}` stages everything beneath it"
    if saw_update and not named:
        return "`-u` with no pathspec stages every tracked modification"
    return None


def _commit_is_blanket(args: list[str]) -> str | None:
    """Reason this `git commit` stages on its own behalf, or None.

    `git commit --amend` and `git commit --author=...` are long options containing
    the letter `a` and must survive, which is why the short-flag test is on clustered
    letters rather than on a substring.
    """
    for tok in args:
        if tok == "--":
            break
        if tok == "--all":
            return "`git commit --all` stages every tracked modification"
        if tok.startswith("--"):
            continue
        if tok.startswith("-") and "a" in _short_flag_letters(tok):
            return (
                f"`{tok}` stages every tracked modification without ever "
                "calling `git add`"
            )
    return None


def _blanket_reason(command: str) -> str | None:
    """Reason any segment of this command is a blanket stage, or None."""
    for tokens in _segments(command):
        idx = _command_word_index(tokens)
        if idx is None or tokens[idx] != "git":
            continue
        sub, args = _git_subcommand(tokens, idx)
        if sub in ADD_ALIASES:
            reason = _add_is_blanket(args)
            if reason:
                return reason
        elif sub == "commit":
            reason = _commit_is_blanket(args)
            if reason:
                return reason
    return None


def _is_allowed_exception(command: str, match: "re.Match[str]") -> bool:
    for exception in ALLOWED_EXCEPTIONS:
        start = max(0, match.end() - len(exception))
        if exception in command[start : match.end()]:
            return True
    return False


def refuse(rule: str, remedy: str) -> None:
    sys.stderr.write(
        # Derived, not hardcoded: this file is installed in three places -- a plugin
        # directory, ~/.claude/hooks/, and a repo's .claude/hooks/ -- and a refusal that
        # names the wrong one sends you looking for a guard that is not there.
        f"REFUSED by {__file__} -- {rule}\n\n{remedy}\n"
    )
    sys.exit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        command = payload["tool_input"]["command"]
    except Exception:
        # A guard that cannot read its input must not block every command.
        sys.exit(0)

    if not isinstance(command, str):
        sys.exit(0)

    reason = _blanket_reason(command)
    if reason:
        refuse(
            "blanket staging is refused in this repository",
            f"{reason}.\n\n"
            "Stage by path instead: `git add <path> <path>`. Knowing what is in\n"
            "the tree is the premise of every containment argument here, and a\n"
            "blanket stage is the one operation that adds a file nobody named.\n"
            "Staging a dotfile BY NAME is fine and always was -- `git add\n"
            ".gitignore` is a named path, `git add .` is not.",
        )

    for pattern, rule, remedy in REPO_HAZARDS:
        if any(
            not _is_allowed_exception(command, m) for m in pattern.finditer(command)
        ):
            refuse(rule, remedy)

    sys.exit(0)


if __name__ == "__main__":
    main()

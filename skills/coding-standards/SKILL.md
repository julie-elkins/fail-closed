---
name: coding-standards
description: >-
  Python coding conventions for agent tooling — dependency pinning, test layout and
  markers, docstring and comment style, provenance labelling, refusal shapes, logging, and
  the deliberate absence of linters and coverage floors. Apply by default when writing or
  reviewing Python in any of these repos, and read it BEFORE setting up a new one: several
  points are about what NOT to add, and a `pyproject.toml` is cheaper to get right than to
  walk back. It governs how the code is written; `mcp-server-standard` governs what an MCP
  tool surface must expose, and `orchestration-standard` governs the layer that calls it.
  It does NOT cover domain rules — those belong in the repo's own CLAUDE.md.
---

# Coding standards

These are the conventions actually in force across eight repositories of agent tooling, written
down because until now they existed only as a pattern you could infer by reading someone
else's tree. Nothing here is aspirational: every rule is one the repos already follow, and
the few that read as omissions are **decisions**, marked as such.

The organising idea is the same one behind the MCP standard: **an unmarked, unmeasured or
absent thing must not be readable as a verified one.** Most of what follows is that
principle applied to source code rather than to a tool payload.

## Dependencies and tooling

**Commit the lockfile.** `uv.lock`, in every repo, always. It is the only artefact that
makes a build reproducible, and it is the thing a colleague needs most on a fresh clone.

**Floors are free; caps must be EARNED.** `mcp>=2.0` costs nothing. `mcp>=2.0,<3.0` is a
claim that you know something breaks at 3.0 — so the comment beside it names what.

```toml
# botocore is a boto3 transitive dep but is ALSO imported directly (SigV4 signing in
# telemetry_runtime/exporters.py), so it is pinned explicitly. Must satisfy boto3's
# >=1.43.21,<1.44.0 constraint; keep in lockstep with requirements-server.txt.
"botocore==1.43.21",
```

That comment is the standard, not the pin. A version number with no reasoning beside it is
a number the next person will bump on vibes.

**Declare what you import, even if it arrives transitively.** A direct `from pydantic
import Field` that rides in via someone else's dependency graph is a production import
depending on a third party's packaging decision. Conversely, **do not pin what you do not
use**: two packages once sat in a dependency list described as transitive deps of a
library that declares neither, and removing them dropped them from the lockfile entirely
with the suite still green. Verify with `uv tree --invert --package <name>` before adding
or removing, and record that you did.

**No linter, no formatter, no type checker, no CI — and this is a decision.** The
strongest version of the argument is a measurement: one repo declared and configured
black, isort, flake8 and mypy, and nothing ever invoked them — no Makefile target, no
buildspec, no hook, no test. `black --check` reported 162 of 192 files would be
reformatted, confirming they had never run. Config describing a standard the tree has
never met **is worse than no config at all, because it implies a convention that is not in
force.** So: add none of them unless you add something that runs them in the same change.

**Put pytest config in exactly ONE file.** `setup.cfg` or `pytest.ini`, whichever the repo
already uses. Never both, and never alongside a `[tool.pytest.ini_options]` block in
`pyproject.toml` — pytest silently ignores the `pyproject.toml` copy when either of the
others exists, so an edit there does nothing and looks like it worked.

**No `--cov-fail-under`, anywhere.** A coverage floor buys tests that execute lines, which
is not the property wanted. Kill mutants instead — see "Mutation testing" below. Coverage
is still worth *measuring*; it is not worth *gating*.

**Register only the markers you actually apply.** A marker registered against zero tests
turns `pytest -m thatmarker` into: collect the whole suite, deselect all of it, exit 5
(`NO_TESTS_COLLECTED`). That reads as a broken build while testing nothing. If selection
is by directory, say so in the config and delete the unused markers.

**Set a test timeout from a measurement.** A cap chosen as "about 4× the full mocked
suite's wall time" fails a hung test loudly with a stack dump and never trips on a healthy
one; a round number chosen by feel does one of those two things by accident. Use
`timeout_method = thread` so it works without a child process and can dump the stuck
test's stack, and override per-test where a subprocess legitimately needs longer.

## Comments and docstrings

**A module docstring states the module's numbered design rules**, not a summary of its
functions. The reader can see the functions.

**Argue every non-obvious decision in place, and name what the wrong choice would have
cost.** This is the highest-value sentence pattern in these repos and the most common
thing lost to a well-meant tidy-up:

```python
# NOTE: `src` is a generic top-level name and could collide with another distribution
# that also installs a `src` package. The alternative is renaming every `src.`-prefixed
# import repo-wide; that is a much larger change, so the explicit declaration is
# preferred until/unless a collision appears.
```

**Use ALL-CAPS for the load-bearing clause**, sparingly. It marks the sentence a reader
must not skim. Lowercasing it in a style pass is a real loss.

**Label every constant's provenance.** One of four labels, and the fourth is honest:

| Label | Means |
|---|---|
| `OBSERVED` / `MEASURED <date>` | You ran something. Give the date and the sample. |
| `FIELD CONVENTION` | A citable external standard. Cite it. |
| `MODELLING ASSUMPTION` | You chose it. Say what it would take to be wrong. |
| `NOT ESTABLISHED` | Nobody knows. Use this rather than guessing. |

An unlabelled magic number is a defect. And **a threshold measured in one regime is not a
constant** — if you expect the value to depend on scale, measure at both ends of the range
and make it a parameter, because tuning it once in the middle produces a defensible figure
and the wrong model of why.

**Record what you tried and abandoned**, with the measured reason. A docstring is a lab
notebook: the assumption, the alternative, and the number that killed it. This is what
stops the next person re-running your dead end.

**British spelling in prose and comments.** Identifiers stay as they are.

## Shapes

**Refusal is a structured result, not an exception.** Return an object carrying `error`,
`message` and `guidance`, where `guidance` names the cheapest correction rather than
restating the rule. A caller — especially an agent — will format whatever it is handed, so
a refusal that raises is a refusal the caller reports as a failure of the whole task.

**Frozen dataclasses for records.** Mutability in a value object is a bug waiting for a
second reader.

**Modern type hints** — `list[str]`, `X | None`, no `typing.List`. Requires-python is
already ≥3.13 in these repos, so there is nothing to be compatible with.

**Logging to stderr via stdlib `logging`, with `propagate = False` on the package
logger.** Never `print`. On an MCP stdio transport this is load-bearing rather than
stylistic — see `mcp-server-standard` point 9 for exactly which writes corrupt a handshake
and which survive.

**~88 columns.** Not enforced by anything; just don't fight it.

## Tests

**Layout.** `test_*.py`, `Test*` classes, `test_*` functions. Shared fixtures in
`conftest.py`, static fixtures under `tests/fixtures/`. Selection by directory
(`tests/unit`, `tests/regression`) rather than by marker, unless the marker is genuinely
applied.

**Synthetic fixtures only.** A known-good record, a multi-level tree, an error case, and
one large enough to be slow. Tests never touch a live system.

**Invariant tests get their own file, and their subject is a property spanning modules** —
not a function's return value. Two shapes worth copying:

- **Security / absence invariants.** "No caller-supplied string can change the URL shape."
  "This package has no write surface." "A documentation citation resolves to a symbol that
  exists."
- **Upstream contract tests.** Pin the *names*, *values* and *shapes* you import from a
  sibling repo. When their threshold moves, you want a failing test, not a wrong answer.

**If a test file's subject is an ABSENCE, mutate it INVERTED.** A file asserting "this
package does not do X" passes trivially while X is absent and goes on passing after X
arrives. Only a mutant that *adds* the forbidden privilege distinguishes those two states.

**No stubs or no-op tests to make a suite green.** A skipped test is worse than a missing
one, because it reports as coverage. Characterization tests must drive the real code path
under a mocked boundary and assert real output.

## Mutation testing, and the three ways a run lies

Run it on new tests before calling them done. Then distrust the output in three specific
ways, each of which has cost real time:

1. **Bust `__pycache__` between mutants, twice.** CPython invalidates bytecode on
   (mtime-in-seconds, size), so a same-size mutant applied within one second of the last
   run loads the *previous* bytecode and reports as a survivor.
2. **Grep the output for the mutation actually landing.** `SURVIVED` is two claims — that
   the test missed it, and that the edit landed. The second is cheaper to check. An anchor
   written against prose, or with the wrong indentation, matches nothing and reports as a
   gap. Print `NOT APPLIED` when the anchor is missing, and grep for `SKIPPED`.
3. **`KILLED` is also a claim that the edit was the one you meant.** Check *which* test
   failed. An inserted line rather than a moved one gets killed by the wrong assertion and
   hides a real survivor.

**Mutate prose too.** Asserting that a document "mentions X" passes on a document that
mentions X and then tells the reader to do the opposite. Pin the imperative, not the topic.

**When a constant becomes a parameter, mutate "use the default where the argument was
passed" at every call site** — and expect the negative-direction tests to miss it.
Hardcoding one side of a two-sided comparison leaves the sides at different widths, so the
result is empty by construction and every "X is not flagged at the wider setting"
assertion passes for the wrong reason. **A comparison of nothing reports exactly like a
comparison that found nothing.** Pin the positive direction alongside it: something that
SHOULD still be caught at the new setting.

## Sweeps

**Scan for structure; never work from a hand-built word list.** A list misses whole
families and every capitalised form. This applies to dialect and terminology passes,
deprecation sweeps, and renames alike.

**Triage every hit into one of three categories before changing it:**

1. **Prose** — fair game.
2. **Identifier** — a function, class, file, test or skill name. Never touch from a prose
   sweep; it breaks imports, and in at least one repo it breaks a test that resolves
   documentation citations against real symbols.
3. **Wire value or quoted output** — a JSON key, an enum member, a log line, a schema
   `description` a test pins, a pasted tool reply. Never touch. A README example in these
   repos is a real recorded run; editing it toward what reads better makes the README lie.

When a hit is ambiguous, leave it and say so. A false negative costs a clunky sentence; a
false positive costs a broken build or a misstated measurement.

## Git

**Stage by path. Never `git add -A`.** The rule exists because a credential file, a real
directory record or a scratch artefact reaching a commit is unrecoverable once pushed.
`templates/hooks/staging-guard.sh` in this kit is the enforcing hook; install it, and read
its stated limits rather than trusting it completely.

**Commit messages are a published surface, separate from file contents.** A message can
name something the tree carefully does not. Grep the log, not just the working tree, before
making a repo readable by a wider audience — and remember that fixing one means a
force-push.

## How to apply

Treat this as the default for new code in these repos. When reviewing, report per area:
followed, breached, or not checkable from here — and **do not report an absent signal as a
satisfied one.** A repo with no linter config is following this standard; a repo with a
linter config nobody runs is breaching it. Those look identical to a checklist and opposite
to a reader.

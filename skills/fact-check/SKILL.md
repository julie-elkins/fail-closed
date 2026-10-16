---
name: fact-check
description: >-
  Verify the checkable claims in a draft against the systems that actually hold the answer —
  internal tickets, code, wikis, package and pipeline state, org data, AWS docs — before it
  goes to a reviewer, a CR, a meeting or an external reader. Use on design docs, CR
  descriptions, meeting docs, threat models, criterion write-ups, résumé and application
  material, and any prose quoting a figure, a date, a schema name, a ticket state or a
  person's role. It returns a per-claim verdict of VERIFIED, CONTRADICTED or NOT CHECKABLE
  FROM HERE and never collapses the third into the first. It is read-only: it posts,
  comments and edits nothing.
---

# Fact check

Most wrong claims in an internal draft are not wrong about the world — they are wrong about
**internal state that has moved since the sentence was written.** A generic web fact-checker
cannot see any of it. This skill checks the things that actually rot.

## The three verdicts, and the one that matters

- **VERIFIED** — you checked it against the authoritative source and quote what you saw.
- **CONTRADICTED** — the source says something else. Quote both.
- **NOT CHECKABLE FROM HERE** — no access, no tool, the source is a person, or the claim is
  a judgement rather than a fact.

**Never report NOT CHECKABLE as VERIFIED.** This is the whole discipline. A draft going to a
security reviewer with four verified claims and two honestly-marked unverifiable ones is in
good shape; the same draft claiming six verified is worse than one that checked nothing,
because it spends the reviewer's trust. This is the same failure `mcp-server-standard` exists
to prevent — an unchecked result reported as a complete one — committed one level up.

## What rots, in order of how often

**1. Ticket and approval state.** The most common defect. An approval *comment* is not a
provisioned grant; a ticket marked approved may still be unactioned. Check the ticket, and
report the state and its date rather than the outcome someone expected.
→ your ticket system's read and search tools

**2. Figures in prose.** Test counts, coverage percentages, node counts, package counts,
dependency-closure sizes, line counts. These are written once and drift silently. **Re-run
the measurement** where you can, rather than trusting the sentence — and if the figure is
load-bearing for a reviewer, say in the draft that it wants a test rather than a sentence.

**3. Names of things.** Schema names, table names, version sets, pipeline names, package
names, registry ids, environment variables, file paths, symbol names. A pipeline looked up
under the wrong name reports NOT FOUND rather than "misspelled", which reads like absence.
→ your code search, your build/pipeline status tool, local `grep`

**4. Whether a cited file or symbol exists.** In repos that pin documentation citations with
a test, this is automated — run the suite. Everywhere else it is not, and a citation written
from memory a day earlier is a common and embarrassing failure.

**5. Dates and relative time.** "Last month", "recently", "as of the current version".
Convert to absolute dates and check them. Today's date is authoritative; a draft's
"currently" may be six weeks stale.

**6. People, roles and reporting lines.** Never assert someone's team, manager or role from
memory, and never infer it from a name. → `find_person` then `lookup_person`; `whoami` for
questions about the user's own org. Read `provenance.age` — replies can be served from a
15-minute cache, and reporting an incomplete org tree's count as a headcount is the main way
to be wrong there.

**7. External technical claims.** Service behaviour, limits, regional availability, API
shapes, model names and pricing. → `aws___search_documentation`,
`aws___read_documentation`, `get_regional_availability`. For anything about Claude models or
the Anthropic API, use the dedicated guide rather than answering from memory.

## Claims to flag rather than check

Some sentences are not facts and should be marked, not verified:

- **Novelty and precedence claims** — "the first X", "no existing tool does Y". These are
  almost never checkable and almost always false in the strong form. Flag every one.
- **Superlatives and completeness claims** — "all", "every", "none", "fully". Ask what would
  have to be true, and whether it was checked or assumed.
- **Attributed positions** — "the team agreed", "legal has cleared". Name who said it and
  when, or mark it unverified. **A channel reply is not a decision.**
- **Causal claims about someone else's system.** You can verify what a service *returned*,
  not why.

## Method

1. **Extract the claims first**, as a numbered list, before checking any of them. A draft
   read and checked in one pass gets its confident sentences checked and its quiet ones
   skipped.
2. **Check the cheap, high-rot ones first** — dates, names, ticket state. They fail most
   often.
3. **Quote the source**, not your conclusion from it. `NOT_CONFIGURED` read off a console is
   a different fact from "logging is off".
4. **Report per claim**, with the verdict, the source, and for CONTRADICTED both versions.
5. **Do not edit the draft** unless asked. Return the findings; the rewrite is a separate
   decision, and some contradicted claims are ones the author will want to argue with a
   reviewer rather than remove.

## Boundaries

**Read-only, always.** No ticket comments, no review-tool comments, no wiki edits, no chat
posts — even when the write tool is available and working. The tool succeeding is not
authorization. Findings go to the user.

**Embargoed content stays in-process.** Where the project handles unpublished material —
an unpublished records file being the standard case — check a claim *about* it without quoting
the content itself into the findings.

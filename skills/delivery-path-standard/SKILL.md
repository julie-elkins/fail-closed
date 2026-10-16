---
name: delivery-path-standard
description: >-
  The 10-point house standard for a build's DELIVERY PATH — whether a change can reach
  production without being checked, and whether a second person could ship or unship it.
  Apply it by default at intake for any new build, and first when reviewing an existing
  one. Do not offer it as an option. Unlike the other two standards it needs NO code
  reading: every point is a yes/no answerable from the package page, the repo root and
  the deploy docs, which is what makes it the cheap first pass and the right thing to
  take to a review board. A "no" here costs one configuration change before the build
  exists and a migration after it ships.
---

# Delivery-path house standard

The other two standards govern what the code does. **This one governs whether anyone
would find out that it stopped doing it.** The failure it targets:

> A production service with good tests, good alarms and a careful owner, where the tests
> were red for twelve days across a deploy, and the recorded remedy was a note reminding
> a human to run them.

That is not a discipline failure. It is the predictable output of a build with **no gate
between a commit and production** — and the whole standard is ten yes/no questions that
find that condition before it ships.

**Every measurement below was taken on a real internal build, and every identifier has
been removed on purpose.** This file circulates; a standard whose examples name a
colleague's package is a code review with a distribution list. The failure shapes
transfer, the names are not what makes them useful.

## Why this one runs first

The fifteen- and twelve-point standards require reading code, and they find defects that
cost a migration to fix. This one requires reading a package page, and it finds
conditions that cost one configuration change to fix — **provided the build does not
exist yet.** After it ships, "add a pipeline" competes with feature work forever.

So the order is: **delivery path at intake, the other two at design.** Not the reverse,
and not this one last as a release checklist, which is the point at which every answer
has already been decided by omission.

## The ten points

1. **It builds in CI, and the build is the gate.** A package with no build has no gate:
   what is deployed is whatever the last person ran from their machine, and the branch is
   a record of intent rather than of what is running.
   MEASURED: a live daily production pipeline whose package page read *"There are no major
   versions for this package. Presumably it has never been built,"* with no version set
   consuming it and a documented deploy of `cdk deploy --require-approval never` from a
   laptop. ❌ **Absence of a red build is not a green one.**

2. **The head branch is protected.** Check it explicitly rather than assuming, because the
   default is off *and looks deliberate* — the package-creation CLI's "unable to push"
   fatal drops branch protection on the way past, so a repo created that way reads
   "No protected branches exist" with nobody having chosen that.
   MEASURED: zero protected branches, and repository-level head protection off, across three
   packages in one team — including one already carrying a security engagement.

3. **Tests run in the gate, not in a runbook.** A suite a human must remember to run is
   documentation. The distinction is not pedantic: it decides whether "the tests pass" is
   a fact about production or a fact about someone's afternoon.
   MEASURED: three unit tests red for **twelve days** spanning a production deploy; found
   by hand at the next sit-down; remedy recorded in the handoff doc as *"Run the command
   above before any pipeline deploy."* Also **grep the run for `SKIPPED`** — a suite that
   reports 23 passed and silently skips the one check you cared about is the same failure
   one level in.

4. **A drift check must BLOCK, not warn.** A warning reports to whoever ran it, and on a
   manual deploy path that is nobody. Deciding this is the whole point: a check written to
   warn was written by someone who had not yet decided it mattered.
   MEASURED: a shared library pinned at one version in a consumer while the library and a
   sibling consumer moved two minor versions ahead. A purpose-built drift check existed,
   correctly reported `BEHIND`, and was documented as *"warns … still non-blocking."* The
   drift was caught by a person, twelve days later, during unrelated work.

5. **No source of truth in a home directory.** Not a config file, not a service list, not
   a bank list, not a checkout path. The test is not "is it committed" but **"does this
   resolve on anyone else's machine."**
   MEASURED: a user-level JSON file in one builder's home directory held the canonical
   list of which record sets get scanned at all. **Three separate packages referenced it**
   — two in comments, one reading it at run time with `expanduser`, so that script cannot
   execute anywhere else. The single-sourcing instinct was right; the location made the
   most consequential input in the system unversioned, unreviewable and single-copy.

6. **A second person can deploy from a fresh checkout using only committed docs.** Deploy
   instructions citing `/local/home/<alias>/workspaces/...` or `~/Documents/...` are a
   runbook for one machine. The check is a thought experiment with a name on it: *could
   the backup owner ship a one-line fix today, without asking?* If the answer needs a
   conversation, the bus factor is 1 whatever the ownership record says.
   Corollary: a handoff doc written for the author's own next session is **good practice
   and not this point** — it proves continuity for one person, which is the thing in
   question.

7. **An alarm goes to a distribution list, not a person.** An alarm addressed to one
   mailbox is off during annual leave, and nothing reports that it is off.
   MEASURED: four genuinely well-designed alarms — including a correct
   *did-the-schedule-stop* detector, which most builds lack entirely — all delivering to a
   single individual's email, with the owner's own documentation noting *"change it to a
   team list if this should reach more than the owner."* It had not been changed. **Good
   alarm design and a bus-factor-1 destination are independent, and the second silently
   voids the first.**

8. **Rollback is named, and has been executed once.** Name the mechanism per artifact, and
   **name what has none** — that list is the real output of this point. Git reverts a
   package. Nothing reverts a Slack message, a wiki edit, a ticket comment, an email, or a
   mass delete of the datastore a human reads as a worklist. An untested rollback is a
   plan; a rehearsed one is a control.

9. **A spike gets deprecated the day it stops being the plan.** An orphan that still
   resolves is indistinguishable from a component, and the next reader — or the next
   agent — will treat it as one.
   MEASURED: a predecessor package with three days of commits, dead three months, still
   reading the home-directory config from point 5 and still naming a bucket in a live
   account. Nothing was wrong with it. It simply could not be told apart from something
   load-bearing without asking its author.

10. **A manual publish step has a named owner and a written procedure.** If a shared
    library is published by hand, record who may publish, what bumps the version, and what
    each consumer must do afterwards. Otherwise consumers drift (point 4), and the
    re-converge is owned by whoever notices.
    MEASURED: a correctly pinned, correctly versioned shared engine — the dependency
    hygiene was **right** — published to an artifact repository by `python -m build` +
    `twine upload` from a workstation, with the consumer-side bump documented and the
    publish-side authority not. Two consumers diverged onto different model versions in
    different regions, and the fix was a retrospective consolidation plan written after
    both had shipped.

## The two-minute version

Points 1, 2, 5, 7 and 9 are answerable **from the package page and the repo root**, with
no code read and no credentials. That is the pass to run at intake, and the reason this
standard belongs in front of a review board rather than at the end of a build:

| Look at | Answers |
|---|---|
| `/packages/<pkg>/releases` | 1 — "never been built" appears in plain English |
| the repository's settings page | 2 — protected branches, head protection |
| repo root + deploy docs | 5, 6 — grep the docs for `~/` and `/local/home/` |
| the alarm/notification config | 7 — is the destination a person |
| package list for the team | 9 — creation and last-commit dates, side by side |

## Anti-patterns, and why each fails

| Anti-pattern | Why it fails |
|---|---|
| Manual deploy from a workstation | no gate, and no record of what is running |
| Non-blocking drift or freshness check | reports to whoever ran it, i.e. nobody |
| Test suite invoked from a runbook | "tests pass" becomes a claim about a person |
| Config or list in a home directory | the most consequential input is single-copy |
| Alarm to an individual | correct detection, zero delivery, on leave |
| Spike left undeprecated | an orphan that resolves reads as a dependency |
| Hand-published shared library | consumers drift; the re-converge has no owner |

## How to apply

At **intake**, ask the ten as written and record the answers; a "no" at this stage is a
line of configuration. At **review**, report per point: **satisfied, breached, or not
checkable from here** — an absent signal is not a satisfied point, and "the owner is
careful" is not an answer to any of them.

Say the cost in the reviewed build's own terms, not in this file's. Every measurement above
came from a build whose author had written the tests, found the breakage, fixed it and
documented the lesson. **None of these ten are caught by a security review**, which checks
controls rather than the path a change travels; and none are caught by the other two house
standards, which read the code and assume something decided whether it shipped.

## What this standard does not reach

It stops at whether a change can reach production unchecked. It says nothing about whether
the change is **correct**, and nothing about the two failure shapes that sit next to it.

A record that vanishes, where its absence reads as success — a row missing because its
assessment failed, a worklist that got shorter because the upstream read was thin, a
confidence score published but gating nothing. Those are data-and-state-model defects; the
fifteen-point standard reaches the *reporting* of them (#6 refusal is a result, #10
diagnostics travel with results) and stops at the boundary of the datastore.
`state-and-deletion-standard` starts there.

And material that leaves the process when it should not have — a report that quotes what it
found, a verbose log holding the payload, an unattended run with no ceiling.
`content-egress-standard` covers that, and it applies even to builds with no delivery path
at all.

**A clean pass here is not a clean build.** It means a change cannot arrive unnoticed, which
is a precondition for the other four standards mattering rather than a substitute for them.

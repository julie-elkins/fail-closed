---
name: security-triage
description: >-
  Decide, before a build is committed to, whether it needs an application security review, what
  data class it handles, and what the review will actually cost in calendar time. Use at intake
  on any proposed build, and on any tool already in use that has never been triaged. It
  produces a data class, a review verdict, a named cost, and the short list of controls that are
  worth having in place before a reviewer asks. It also covers the failure mode that makes
  security work look finished when it is not: a control that never fires reads exactly like a
  healthy system. It is advisory and read-only — it decides nothing on a reviewer's behalf,
  opens no engagement and posts nothing.
---

# Security triage

The question is not "is this secure." It is **"does this build carry a security review, and does
its estimate say so."** A review discovered at launch and a review planned at intake are the same
work on very different clocks, and only one of them leaves room to answer a reviewer properly.

This skill is written from one engagement on a tool handling an organisation's most restricted
class of unpublished material, reviewed after it was already in production. Treat the numbers as
one observation, not a policy. **Your organisation's data-classification scheme is its own**;
what transfers is the shape of the question, not any particular label.

## Step 1: data class, in one line

Three values. Answer factually, before considering consequences.

- **Unpublished content whose disclosure is itself the incident.** Two worked cases, because a
  standard carrying one domain's vocabulary stops being portable. In assessment: question text,
  answer options, rationales, item banks, form assembly reports, cut scores, and anything
  *derived* from these that would let a reader reconstruct them. In a commercial setting: an
  unreleased price list, an unannounced acquisition model, pre-publication financials. The test
  is the same — would a reader who saw the output be able to reconstruct the thing?
- **Personal data** — names, aliases, email addresses, individual performance, attendance.
- **Neither.** This is the common answer and it should be recorded, not assumed.

Two traps. **A tool that reads restricted content to produce a summary still handles restricted
content** — the classification follows the input, not the output. And **a tool that stores ids
rather than text is materially better but not reclassified**: ids that resolve against a store
the reader can also reach are the content with an extra step.

## Step 2: does it need a review

Ask in this order and stop at the first yes.

1. **Does it deploy anything into a cloud account?** A hosted web app, an API, a serverless
   function, a database, a bucket. Yes means a review, and *which* account it lands in is part
   of the question.
2. **Does it handle unpublished content or personal data at rest** — written to disk, a table,
   a bucket, or a log? Yes means a review.
3. **Does it hold credentials for anything, or act with permissions a person did not grant per
   call?** Yes means a review.
4. **Does it run only on one person's machine, read local files, hold nothing, and deploy
   nothing?** Then it is a script, and the honest answer is no review — record that verdict with
   the reason so it can be revisited when the script grows a server.

Whether a *particular* internal engagement type applies, and to which team, is not packaged here
and should not be guessed. The triage verdict above is what intake needs; the engagement mechanics
are a question for the security team named on the closest prior review.

## Step 3: name the cost, in calendar time

This is the field that changes decisions, and the one always left out. From the one engagement
measured:

- **A kickoff call, then a fixed review window.** Two weeks was the stated period. Assume the
  window is shorter than the remediation it will generate.
- **A reviewer with their own queue.** The engagement can be closed by someone else's cleanup
  and need recreating, and nobody is notified when that happens. **Check the engagement is open
  before assuming it is progressing** — six weeks were lost to exactly this.
- **Remediation work that is real engineering**, not configuration. Authorization rules, an
  audit trail, alarms, dependency upgrades.
- **A launch date that has to survive all of the above.** If the review window closes on the
  launch date, the schedule will decide the architecture. Say so at intake, when it is still
  free to move.

Write the cost as a range with the gate named: *"two weeks review window, remediation unknown
until findings land, gated on the reviewer's kickoff date."* A single number here is a guess.

## Step 4: controls worth having before anyone asks

Not a compliance list. These are the ones that came back as findings, and each is cheap
beforehand and expensive under a deadline.

- **Authorization on every model, not most of them.** See the ratchet test below.
- **An append-only audit trail** — who did what to which record. Grant no `update` and no
  `delete` to anyone, including administrators, so the trail cannot be edited by the people it
  is about. Store **ids, never content**, and never a second copy of a judgment that already
  lives in its own table.
- **A retention rule that is actually enforced**, not just a field named `expiresAt`.
- **Alarms that have been observed firing.** An alarm nobody has seen fire is a hypothesis.
- **One named account per environment, verified from configuration** rather than from the
  environment's name. Two accounts both calling an environment `dev` is normal and is how a
  deploy reaches the wrong one.

## The failure mode that outranks all of the above

**A control that never fires is indistinguishable from a quiet, healthy system.** Every one of
these was found in a single engagement, and each looked correct from the outside:

- A retention field written on every row, with retention **never enabled on the table**. The rows
  had an expiry. Nothing ever expired.
- The same field populated in **milliseconds where the mechanism requires seconds**. A valid
  number, a year-55000 expiry, a no-op that logs nothing.
- A subscription left **pending confirmation**. Alerts had a destination and no recipient, and
  the pending state is deleted after three days without a log line.
- An alarm whose missing-data policy meant **absent data counted as healthy**, so the alarm was
  green precisely when the pipeline was dead.
- A notification address that was **not a mailbox** but a resolver group's sink, silently
  dropping automated mail.
- A schedule expression that **restarts its interval every time it is re-applied**, so an
  idempotent redeploy meant it never reached the end of its period.
- A status of `ENABLING` read as `ENABLED`.

The common shape: **the artifact exists, the wiring does not, and absence produces the same
output as success.** So for every control, ask the question that distinguishes them — *what would
I see if this had never once worked?* If the answer is "exactly what I see now," it is not
verified. Make it fire on purpose and watch it.

## The ratchet test, and why a passing suite proves less than it looks

A guard test that accepts the weaker-but-still-acceptable option **cannot detect an incomplete
migration.** Observed: a test asserted every model required authentication, and accepted
authenticated-user-only as satisfying that. One model had been left on authenticated-user-only
while the rest moved to group-based rules. The test passed. It was written to pass, because
failing a hardened model would have been worse.

Both tests are needed and they are different tests:

- **A floor** — nothing is public. Accepts anything authenticated. Never fails on hardening.
- **A ratchet** — nothing is left on the weaker option, with an explicit allow-list of exceptions
  each carrying a written reason. An exception becomes a line in a diff instead of an omission.

Verify the ratchet by mutation: revert one item and confirm the test fails **and names it.** A
test that fails without saying which item is a test you will not trust at 6pm. And assert the
anchor exists before trusting a mutation run — a mutation that silently did not apply reads as a
passing test.

## What this skill does not do

- **It does not decide a reviewer's finding**, argue a severity, or judge whether a deferral is
  acceptable. Those are the reviewer's and the accountable manager's calls.
- **It does not open, comment on or close an engagement.** Outward-facing text is drafted for a
  person to send.
- **It does not classify content it is shown.** If restricted content is needed to answer a question,
  the answer is that it should not have been pasted in. Work from paths, ids and schemas.
- **It names no specific internal review process, form or team**, because those move and a stale
  name reads as authoritative. Find the closest prior review and follow what it actually did.

## Recording the outcome

Four fields, wherever the build register lives:

1. **Data class** — unpublished content, personal data, or neither.
2. **Review verdict** — not required, or required, with the reason in one sentence.
3. **Cost** — window, plus what the remediation estimate is gated on.
4. **Status** — not started, in review, or signed off with a date.

A build in use reading *restricted content / required / not started* is not an accusation. It is a
sequencing fact, and it is the one that decides whether a launch date is real.

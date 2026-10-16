---
name: state-and-deletion-standard
description: >-
  The 10-point house standard for STATE AND DELETION — how a record is allowed to
  disappear, and what its absence is permitted to mean. Apply it by default when designing
  or reviewing anything that writes, counts, prunes, caps or expires records, and
  especially when a human reads the surviving list as a worklist. Do not offer it as an
  option. Use it BEFORE the schema is settled: points 1, 2 and 6 decide what every row and
  every payload has to carry, and cannot be retrofitted without a migration. The failure it
  targets is silent and always flattering — a shorter list read as progress, a capped
  result read as a complete one, a failed unit of work indistinguishable from one that was
  never in scope.
---

# State-and-deletion house standard

The MCP standard governs how a result is **reported**. The orchestration standard governs
how a result **travels between steps**. The delivery-path standard governs whether a change
could reach production **unchecked**. All three stop at the edge of the datastore.

This one starts there, and it asks one question in ten forms:

> **How is a record allowed to disappear, and what is its absence allowed to mean?**

**Every failure in this family is silent, and every one of them errs in the flattering
direction.** That is not a coincidence — it is structural. A row that is missing looks
exactly like a row that was checked and found clean, and there is no mechanism by which the
system could notice the difference, because the evidence that would distinguish them is the
thing that is absent. So nobody is ever alerted; somebody eventually *notices*.

**Measurements below are anonymised on purpose**, as in the delivery-path standard: dates
and figures intact, identifiers removed. This file circulates.

## The two-question version

If you check nothing else, check these two:

1. **Take the count in the output and subtract it from the count of things put in. Is the
   difference a number the system publishes?** If not, the system cannot tell you what it
   lost.
2. **What is the smallest number of input records that would cause a mass delete?** If the
   answer is "one" or "zero", the delete is guarded by nothing.

## The ten points

1. **A failed unit of work writes a row, not nothing.** Absence must mean exactly one thing,
   and it cannot, if a failure path is silent.
   MEASURED: a per-record assessment step caught its own exception, incremented a `failed`
   tally in its log line, and **wrote no record**. Downstream, a record that failed to
   assess was byte-for-byte indistinguishable from one that had never been in scope and one
   that had been assessed as clean. The exception handling was correct, the logging was
   correct, and the result was a datastore that could not answer "what did we not manage to
   look at." ❌ **A log line is not a record.** Nobody reads the log; everybody reads the
   table.

2. **Totals carry their denominator, and `failed` and `skipped` are line items.** Every
   count published must be reconcilable against the count of inputs.
   MEASURED: a payload's `totals` block carried the number of records found impacted and the
   number found not-impacted, and **had no `failed` key at all** — so the one number that
   would have exposed point 1 was never computed. Two plus zero equalled two, and the report
   read as complete. The fix is arithmetic, not judgment: `in + skipped + failed = out`, and
   if it does not balance, the payload says so rather than the reader noticing.

3. **A delete is guarded by a property of the INPUT, never by the shape of the result.**
   This is the load-bearing point and the most expensive one to get wrong.
   MEASURED: a nightly prune deleted every stored record absent from the current run's
   output. Correct behaviour, and the intent was right — stale records must go. But the
   guard was the output itself, so an upstream read returning 6 rows instead of 600 deletes
   594 records, the dashboard goes quiet, and **quiet is what success looks like.** The fix
   is a floor stated in terms of the input: refuse to prune if the run examined fewer than
   *N* records, or if the delta exceeds *X*% of stored rows, and make the refusal a reported
   result rather than a skipped step.

4. **A shorter list is not evidence of progress. Distinguish EMPTIED from NEVER ENTERED.**
   A zero is ambiguous in the flattering direction: a queue nobody could enter reads
   identically to a queue everybody passed. Publish the count of things **examined** beside
   the count of things **found**, always, and let a human see that the first one is zero.

5. **Gate on the input, never on a derived label.** If the check that protects something
   reads a value computed downstream of the thing being protected, the check inherits every
   upstream failure — and it fails *open*, because a missing or defaulted label reads as
   benign. Gate on the raw input, at the boundary, before anything has had a chance to
   summarise it.

6. **A score you publish but do not act on is a decoration. Say which it is, in the
   payload.** MEASURED: a per-record confidence value was computed, stored, and surfaced on
   the dashboard a human worked from — and gated nothing. No threshold consumed it, no
   record was withheld or flagged on it. A low-confidence conclusion and a high-confidence
   one were presented to the reader in the same typeface. Either it gates and the threshold
   has provenance, or the payload states that it is advisory and what it does not cover.

7. **State must be rebuildable from an append-only source.** If the only copy of "what we
   concluded" is the mutable table, a bad run is not recoverable and the delivery-path
   standard's rollback point has nothing to act on — git reverts the code, not the rows.
   Keep the run's raw output as an immutable artifact keyed by run id, so the table is a
   projection rather than the original.

8. **A record a human reads as a worklist carries a deletion audit trail.** Which run
   deleted it, when, and on what basis. Without it, "it was there last week" is
   unanswerable, and the first question after every incident in this family is exactly that.
   A soft delete plus an expiry is usually cheaper than reconstructing the argument later.

9. **A cap or truncation must be visible in the output, as a field.** MEASURED: a scan step
   accepted an optional maximum-candidates argument and broke out of its loop on reaching
   it, returning the truncated list with **nothing in the result saying it had been
   truncated.** A capped run and an exhaustive run returned the same shape. Any limit —
   page size, time budget, token budget, `LIMIT` clause, early `break` — publishes
   `truncated: true` and the limit that bit.

10. **A default substituted for a missing value must be OUT OF RANGE, never plausible.**
    MEASURED: a numeric coercion helper returned `0.5` when a value could not be parsed —
    a perfectly plausible mid-scale confidence, indistinguishable from a real measurement,
    and one that would survive every range check downstream. Prefer a null plus a refusal.
    If a sentinel is unavoidable, pick one no reader could mistake for data, and assert in
    a test that it cannot pass the same validation as a real value.

## Resolving 3 against a legitimate cleanup

Point 3 is not "never delete." Stale records genuinely have to go, and a table that only
grows becomes its own incident. The distinction is **what the delete is conditioned on**:

- **Conditioned on the input** → safe. *"Prune only if this run examined at least 500
  records"*, *"refuse if the delete would exceed 20% of stored rows."*
- **Conditioned on the output** → unsafe, and silently so. *"Delete everything the run
  didn't re-emit"* is correct exactly when the run is correct, which is the thing you
  cannot assume.

A prune that refuses is a good night's work. A prune that cannot refuse has no failure mode
it can report — only one it can cause.

## Anti-patterns, and why each fails

| Anti-pattern | Why it fails |
|---|---|
| Failure logged, not written | absence means three different things at once |
| Totals without a `failed` line | the reconciling number is never computed |
| Prune conditioned on the run's output | a thin upstream read becomes a mass delete |
| A bare zero count | emptied and never-entered are indistinguishable |
| Gate reading a derived label | inherits upstream failure, fails open |
| Ungated confidence score | decoration presented as a safeguard |
| Table as the only copy | no rollback target exists |
| Silent cap or `break` | a partial answer reported as a complete one |
| Plausible fallback value (`0.5`) | a guess that survives every range check |

## How to apply

Do it **at schema design**, before the first write. Points 1, 2 and 6 decide what every row
and every payload carries; adding a `failed` line item to a live table is a migration plus a
backfill plus an argument about what the historical rows should say.

When reviewing, report per point: **satisfied, breached, or not checkable from here** — and
note that in this family "not checkable" is the common answer and must not be rounded to
satisfied. The specific trap: you cannot verify point 3 by looking at the data, because a
correctly-working system and a system that silently deleted 594 rows both look like a table
with the right number of rows in it today. **Read the guard, not the table.**

## What this standard does not reach

It says nothing about whether the conclusion stored in a record is **correct** — a
well-audited, reconcilable, floor-guarded table of wrong answers passes every point here.
And it says nothing about who may **see** the record: whether the material in it may travel
into a report, a ticket, a commit message or an email is a different axis with a different
failure mode, and `content-egress-standard` covers it.

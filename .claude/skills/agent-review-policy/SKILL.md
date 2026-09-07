---
name: agent-review-policy
description: Use when dispatching a review of work in this project, or deciding which model should perform one. Defines which review classes may run on a cheap model, what counts as an escape, the tripwire that revokes cheap reviews, and where escapes are logged.
---

# Agent review policy

Reviews cost real money. Cheap models are worth using where the work is verification
against stated evidence, and not worth using where the work is judgment about what is
*absent*. This policy draws that line and then measures whether the line was drawn
correctly.

## Which reviews may run on a cheap model

| Cheap-eligible | Not cheap-eligible |
|---|---|
| Does the code match the brief? | Is this the right abstraction? |
| Are the docs complete and internally consistent? | Is there a hole in a contract? |
| Do the cited `file:line` references resolve? | Does this design have a footgun? |
| Did the fix land, and land only where intended? | What is missing that nobody asked about? |

The distinction is not difficulty — it is whether the answer is *present in the material*.
Checking a citation resolves is bounded. Noticing that three error paths were never
guarded is not.

### The evidence for this line

Workstream A's one Critical finding was an exit-code hole: three missing guards let a
malformed committed `meta.json` produce exit 1 with `all --json` emitting zero bytes — in a
tool whose central promise is that exit 1 and exit 2 are never conflated. It was found by
an expensive reviewer reasoning about what was *not* in the code. No cheap review was asked
to do that, and this policy does not ask one to.

## Escapes

An **escape** is a defect a review passed over that something later catches:

- the controller's own verification
- a subsequent task's implementer
- a later review, of this task or another
- a gate failure

Every escape is logged in [`docs/agent-review-log.md`](../../../docs/agent-review-log.md)
against the model that missed it.

## The tripwire

**One Critical escape, or two Important escapes, attributed to a cheap review — and that
review class reverts to the expensive model for the remainder of the workstream.**

Not a discussion, not a judgment call at the time. The point of fixing the threshold in
advance is that it cannot be argued away in the moment by whoever is watching the budget.

## Report it honestly

This measures **detected** escapes, which is a lower bound on escapes that exist: an escape
nobody ever catches is never counted. The sample is also small — single-digit reviews per
workstream.

So it is a **tripwire, not a statistic.** When reporting it, say so. Do not present an
escape count as a miss rate, and do not conclude that cheap reviews are safe because the
log is empty — an empty log is equally consistent with nobody having looked.

## Dispatching a review

- Tell the reviewer what has **already been independently verified**, and instruct it not
  to re-measure that. Duplicated verification was the single largest waste in workstream A.
- Give it the diff, not the repository, when the diff is what is under review. A review
  package that accidentally included a committed baseline came to 8.18 MB; the code-only
  diff that replaced it was 259 lines.
- Say plainly which findings are expected to be unverifiable in the current environment,
  and ask for a judgment on the merits rather than a false negative.

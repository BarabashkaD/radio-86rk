# Agent review log

Escapes from agent reviews, one row per escape. Append only.

An **escape** is a defect a review passed over that something later caught — the
controller's own verification, a subsequent task's implementer, a later review, or a gate
failure. The policy that governs this log, including the tripwire that revokes cheap
reviews, is `.claude/skills/agent-review-policy/SKILL.md`.

## Why this file is tracked

The implementation ledgers live under `.superpowers/`, which `.gitignore` excludes as
scratch. A metric that dies with each branch cannot answer the question this log exists to
answer — over time, are cheap reviews good enough? So it lives in `docs/` and survives.

## How to read it

This counts **detected** escapes. An escape nobody ever catches is never recorded here, so
the count is a lower bound and not a miss rate. The sample is small: single-digit reviews
per workstream. Treat the log as a tripwire, not a statistic, and never conclude that cheap
reviews are safe because the log is short — a short log is equally consistent with nobody
having looked.

## Reviews performed

| Date | Workstream | Scope | Model class | Findings raised | Escapes detected |
|---|---|---|---|---|---|
| 2026-09-06 | A · harness | Tasks 1–11, task-by-task | expensive | incl. 1 Critical (exit-code hole), 6 Important | — |
| 2026-09-07 | A · harness | fix wave `2918cdf..e2dcbb6`, 10 items | **cheap** | 0 new; all 10 verdicted addressed | **0 so far** |
| 2026-09-07 | C · agent-flows | `CLAUDE.md`, 5 skills, this log | **cheap** | 1 Minor: an ERC breakdown stated without its measurement marker | **0 so far** |

## Escapes

| Date | Workstream | Task | Reviewer model | Severity | What was missed | Caught by |
|---|---|---|---|---|---|---|
| — | — | — | — | — | *none recorded* | — |

## Notes on open rows

**2026-09-07, A, fix wave.** Zero escapes detected, but nothing has yet been built on top
of that review, so it has not really been tested. Record any escape found later against
this row rather than starting a new one.

One item in that review — `I6`, the flatpak candidate shape — was explicitly
**unverifiable on the review host**: no flatpak Linux environment exists on macOS. The
reviewer judged it on the code's merits, as instructed. It should be retested the first
time the harness runs on Linux, and if it fails there, that is an escape belonging to this
row.

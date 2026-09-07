---
name: workstream-lifecycle
description: Use when starting, executing, or merging a workstream in this project — a self-contained body of work developed on its own branch. Covers the branch-to-merge procedure, the preservation rules that must hold, and how to determine what has already landed.
---

# Workstream lifecycle

A **workstream** here is a self-contained body of work with its own branch, its own
design, and a merge of its own. The KiCad 10 modernization was split into four:
A (`harness`), C (`agent-flows`), B (`kicad10-3d`), D (`freecad-case`).

## Procedure

1. **Branch from master.** One workstream at a time. Never develop on master.
2. **Design first** — a spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`,
   approved before implementation begins.
3. **Decide the execution mode by shape, not by habit.** A plan document plus dispatched
   subagents earns its cost when there are many tasks with real test cycles. For a handful
   of prose files it does not: the plan would have to contain the prose, and an agent would
   then be paid to transcribe it. Choose deliberately and say why.
4. **Execute**, committing in small increments.
5. **Review** before merging. See `agent-review-policy`.
6. **Squash to one commit, then merge.** A workstream lands on master as a single
   commit, so review, revert and `git log` all operate on it as a unit. Squash *before*
   merging and merge *before* pushing: that ordering is what keeps the one-commit rule
   and the no-rewrite rule from colliding.
7. **Run the gates on master afterwards.** Not before, not instead — after.
8. **Do not delete the branch.** After the squash it is the only place the development
   history lives. Push it when anything on master cites its commit SHAs —
   `verify/baseline/meta.json` records the commit its capture came from.

## The preservation rules

These held through the four-way split and still apply:

1. **The archive exists as both a branch and a tag on `origin`** —
   `archive/kicad10-3d-2026-09-06`. Branches move; tags do not.
2. **Master is untouched until a workstream is finished and reviewed.** No partial
   merges, no staging work on master.
3. **Workstream branches are not deleted after merging.** They survive until the
   programme completes.
4. **The no-loss invariant.** After B merges:

   ```
   git diff archive/kicad10-3d-2026-09-06 master -- KiCad/
   ```

   must be **empty**. That is objective proof the board, schematics, footprints and 3D
   models came through the split byte-identical. `tools/` and `docs/` legitimately differ.
5. **The gates run on master after every merge.** Master is never left in a state where
   its output claim is unverified.

## Two guarantees that sound alike and prove different things

Do not substitute one for the other:

```
git diff archive/kicad10-3d-2026-09-06 master -- KiCad/   ->  empty
    file-level identity: "the archived source arrived intact"

python3 tools/kicad-verify.py all                          ->  exit 0
    output-level identity: "the board still manufactures the same"
```

Output identity is the harder claim and the one that matters. B rewrites nearly every file
under `KiCad/` — new format, new footprint references, new model paths — and the output
must come out identical anyway. File identity cannot demonstrate that, because all the
files change.

## Determining what has landed

State is derivable; do not keep a status list in a file, because a status list rots.

```
git branch -a                      # which workstream branches exist
git log --oneline master           # one commit per workstream: this is the list
git tag                            # board revisions and the archive
```

A workstream is done when its branch is merged to master and the gates are green there.

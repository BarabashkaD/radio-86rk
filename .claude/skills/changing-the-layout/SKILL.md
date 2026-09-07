---
name: changing-the-layout
description: Use when modifying Radio-86RK.kicad_pcb — moving traces, pads, vias, footprints or zones, or changing the board outline. Covers the before/after procedure, why zone refills change output on their own, and how to recapture and commit the baseline when the change was intended.
---

# Changing the layout

Target: `KiCad/Radio-86RK.kicad_pcb`. This is the file the published gerbers were made
from, so a change here is a change to a manufactured product.

## Before you start

Answer question 2 from `CLAUDE.md` and **write the answer down**, because it determines
what a passing gate means:

- **Output must not change** — you are refactoring, renaming, or editing metadata. The
  gates must stay green. Exit 1 is a defect in your change.
- **Output should change** — you are moving copper on purpose. Exit 1 is expected, and
  exit **0** is the defect: it means your edit did nothing.

## Procedure

1. **Establish the starting point.**

   ```
   python3 tools/kicad-verify.py all
   ```

   Green here means the board matches the committed baseline before you touch anything.
   If it is *not* green before your change, stop and find out why — otherwise you cannot
   attribute the difference afterwards.

2. **Make the change.**

3. **Re-run the gates.**

   ```
   python3 tools/kicad-verify.py all
   ```

4. **Read the result against what you declared.** Not against a hope that it passes.

5. **Inspect the diff before accepting it.** The gerber gate prints which files differ.
   A change you meant to make to one trace should not be moving five layers.

## Zone refills change output without you moving anything

The board has copper zones. KiCad refills them during DRC and on some save paths, and a
refill can legitimately produce different gerber output than the previous fill — different
thermal spokes, different island pruning — even when no trace moved.

So a gate failure after a layout session is not automatically evidence that *your* edit
moved copper. Check whether the difference is confined to the zone layers before
concluding anything.

This is general KiCad behaviour rather than something measured on this board, and is
flagged as a caution to check, not a fact to quote.

## The DRC figures, and one number that lies

Master reports **22 violations, 0 errors** (measured 2026-09-07): 17 `silk_edge_clearance`
and 5 `starved_thermal`. Seeing them does not mean you broke something. Both sets are
inherited from skiselev's v1.4 — the `v1.4` tag and `upstream/master` are the same commit,
`c5e9cb7`, so anything present there is the original design's, not this fork's.
`docs/drc-exclusions.md` argues each one out.

**"0 errors" is not what it looks like.** Before workstream B the same board read 212
violations with 5 errors. Two different things happened:

| | Before | Now | What changed |
|---|---:|---:|---|
| `lib_footprint_issues` | 190 | 0 | genuinely fixed by vendoring the libraries |
| `silk_edge_clearance` | 17 | 17 | nothing |
| `starved_thermal` | 5 errors | 5 **warnings** | **severity reclassified in the project file — not fixed** |

The five starved thermals are still there. `Radio-86RK.kicad_pro` sets
`"starved_thermal": "warning"`; master previously left it unset, where KiCad's default is
`error`. Fixing them for real would mean moving copper, which is a board change and needs
question 2 answered accordingly.

## Recapturing the baseline

When the output was *meant* to change, the committed baseline is now stale and must move
with the design.

```
python3 tools/kicad-verify.py baseline --force
```

`--force` overwrites the existing baseline of the same mode only — capturing `--geometry`
leaves `strict/` untouched and vice versa.

Then commit `verify/baseline/` **with its justification in the commit message.**

This is not optional politeness. `verify/baseline/meta.json` records `captured`, `commit`,
`kicad_version` and `modes` — so a year from now the metadata will tell you *when* and
*from what* the baseline moved, but nothing anywhere will tell you **why** unless the
commit message says so. State what changed in the design and why the new output is
correct.

## If the schematic changed too

A connectivity change has to reach the board through KiCad's GUI (Tools → Update PCB from
Schematic); `kicad-cli pcb --help` offers `drc`, `export`, `import`, `render`, `upgrade`
and nothing that syncs from a schematic. See `changing-the-schematic`.

## Do not confuse the two gerber sets

`gerber/` holds the **published** fab output — 7 `.gbr` files, `NPTH.drl`, `PTH.drl` and
`gerber.zip`. `verify/baseline/strict/` holds the harness reference — 22 files, Protel
extensions, one merged `.drl`. They are not comparable file-to-file. Regenerating `gerber/`
is a release step, described in `CLAUDE.md` question 3 — not part of ordinary verification.

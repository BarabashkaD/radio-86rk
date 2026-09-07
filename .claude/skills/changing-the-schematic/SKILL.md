---
name: changing-the-schematic
description: Use when modifying any .kicad_sch file in this project — adding or removing components, changing wiring, fixing an ERC finding, or relabelling nets. Covers the before/after procedure, which branch's ERC numbers you are comparing against, and what kicad-cli cannot do for you.
---

# Changing the schematic

The design is one root sheet plus four sub-sheets:

```
KiCad/Radio-86RK.kicad_sch              root
KiCad/Radio-86RK-CRT-Mem.kicad_sch      \
KiCad/Radio-86RK-IO.kicad_sch            |  sub-sheets
KiCad/Radio-86RK-Keyboard.kicad_sch      |
KiCad/Radio-86RK-Power.kicad_sch        /
```

## Before you start

Answer question 2 from `CLAUDE.md` explicitly: **should the manufacturing output change?**

A schematic edit that is meant to be output-neutral (a label, a symbol field, an ERC
suppression) must leave the gates green. A schematic edit that changes connectivity is
*meant* to move the netlist, and possibly the board — so the netlist gate is expected to
fail, and that failure is the evidence your change took effect.

## Procedure

1. **Record the starting point.** Do not skip this; the numbers are the only thing that
   makes the "after" reading meaningful.

   ```
   python3 tools/kicad-verify.py rules
   ```

2. **Make the change.**

3. **Re-run the same command** and compare the ERC counts.

4. **Run the netlist gate** to see which connectivity actually moved:

   ```
   python3 tools/kicad-verify.py netlist
   ```

   Exit 0 means every pin still maps to the same net. Exit 1 prints what differs. Exit 2
   means the gate could not run and is not a statement about the schematic.

5. **If connectivity changed and that was intended**, the board is now out of step with
   the schematic. See `changing-the-layout` for pushing the change through and for
   recapturing the baseline.

## ERC counts differ by branch — check which you are on

This is the trap most likely to waste an hour.

| Where | ERC | Verified |
|---|---|---|
| **master, now** | **32 warnings, 0 errors** — all `same_local_global_label` | measured 2026-09-07 |
| master before workstream B | 413 warnings, 0 errors | measured 2026-09-07 |
| `migrate2kicad10` | 18 warnings, 0 errors | a different, abandoned branch |

**Expect 32.** All of them are bus signals carrying a local and a global label of the same
name; `docs/erc-exclusions.md` argues each one out and shows that clearing them costs 91
label edits for zero errors. If you see 32, you have found nothing.

The 413 reading belongs to the pre-B board, whose 210 `footprint_link_issues`, 142
`lib_symbol_mismatch` and 29 `lib_symbol_issues` were artifacts of unresolved library
links. Vendoring the libraries fixed them for real; only the 32 remain.

The 18 figure is the one most likely to mislead, so it is recorded here rather than left
out: it belongs to `migrate2kicad10`, whose merge-base with this line is `9476ec3` — the
two never met. It is 18 rather than 32 because that branch converted local labels to
global, which is also what **masked the U3/U22 defect** there. Do not treat it as a target.

Reproduce any of this with `python3 tools/kicad-verify.py rules`. Never quote one of these
numbers without naming where it came from.

## What `kicad-cli` will not do for you

Checked against `kicad-cli sch --help`, which offers exactly `erc`, `export`, `upgrade`:

- **No annotation.** If you add symbols, they need annotating, and there is no CLI for it.
- **No update-PCB-from-schematic.** Pushing schematic changes into the board is a GUI
  operation (Tools → Update PCB from Schematic).

So a connectivity change cannot be completed headlessly. Plan for a GUI step, and say so
rather than reporting the work as finished.

## Known pending work

Project notes record a pre-existing **U3/U22 wiring defect, filed as issue #2**. This is
recorded in notes and has not been re-verified — confirm it against the schematic before
acting on it, and treat the note as a lead rather than a specification.

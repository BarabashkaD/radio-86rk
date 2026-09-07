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

| Branch | ERC | Verified |
|---|---|---|
| `master` | **413 warnings, 0 errors** | measured 2026-09-07 |
| the modernization line | 18 warnings, 0 errors after remediation | **project notes only, not re-verified** |

Both figures are correct for their own branch. Master carries 413 because it predates the
remediation. The breakdown, from the same measured run on 2026-09-07: 210
`footprint_link_issues`, 142 `lib_symbol_mismatch`, 32 `same_local_global_label`, 29
`lib_symbol_issues`. Reproduce it any time with `python3 tools/kicad-verify.py rules`.

If you are on master and see 413, you have found nothing — that is the expected reading.

Never quote one of these numbers without naming the branch it came from.

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

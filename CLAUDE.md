# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Radio-86RK: a KiCad 10 remake of a Soviet-era (1986) DIY ham-radio computer (Intel 8080-compatible). This is a hardware project — there is no software build/test/lint cycle for the KiCad files themselves.

- `KiCad/Radio-86RK.kicad_pro` — project file
- `KiCad/Radio-86RK.kicad_sch` — root schematic, with 4 hierarchical sub-sheets: CRT-Mem, IO, Keyboard, Power
- `KiCad/Radio-86RK.kicad_pcb` — PCB layout
- `gerber/` — exported gerbers/drill files for fab
- `Software/` — monitor/font ROM binaries and firmware sources (`Software/src/`), unrelated to the KiCad build
- `Documentation/` — hardware docs

## Working with the schematic and PCB

A `kicad` MCP server (KiCAD-MCP-Server, registered locally, backed by KiCad's bundled Python for `pcbnew` access) is available and should be used as the primary way to inspect or edit the schematic and PCB — prefer its tools over hand-editing the `.kicad_sch`/`.kicad_pcb` S-expression files directly.

After any schematic edit, the PCB does **not** update automatically — it must be re-synced via KiCad's "Update PCB from Schematic" (forward annotation) before running DRC or exporting gerbers, otherwise the board will be checked/exported against stale connectivity.

`kicad-cli` (bundled with the KiCad 10 install, v10.0.4) is available as a headless fallback for ERC/DRC/export if the MCP server isn't available. Locate it rather than assuming a fixed path — it's not always on `PATH`:
- **macOS:** `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
- **Windows:** `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`
- **Linux:** usually on `PATH` already (`which kicad-cli`); otherwise `/usr/bin/kicad-cli`

## Footprint library setup

Footprint libraries are resolved via `KiCad/fp-lib-table` (project-local, takes precedence over the user's global table). **KiCad only reads this file at project-open time** — if you edit it while the project is already open in the UI, close and reopen the project (or restart KiCad) before "Update PCB from Schematic" will find the new/changed entries.

Current nicknames:
- **`Cherry_MX`** → `${KICAD10_3RD_PARTY}/footprints/com_github_perigoso_keyswitch-kicad-library/Switch_Keyboard_Cherry_MX.pretty`. Points at the officially PCM-installed `kiswitch/kiswitch` package (formerly `perigoso/keyswitch-kicad-library` — GitHub auto-redirects the old repo name, so no PCM URL update was needed). Covers 65 of the 67 keyboard switches (all the 1.00u/1.25u/1.50u sizes, footprint `SW_Cherry_MX_PCB_<size>u`).
- **`Cherry_MX_Custom`** → `${KIPRJMOD}/Cherry_MX_Custom.pretty` (project-local, committed to the repo, no external dependency). Holds `CHERRY_PCB_225H` (SW11, Enter) and `CHERRY_PCB_625H` (SW64, Space): both use a hand-built stabilizer made by combining two Cherry Corp leveling-kit parts (Mouser 540-G99-0742 + 540-G99-0226, see README BOM) that has no equivalent in the official library. Geometry was extracted pad-for-pad from the board's embedded footprint copies rather than approximated, then given 3D models (switch body + the official stabilizer model whose hole spacing matches this custom geometry almost exactly) for accurate mechanical reference during case design.
- **`My_Components`** → **not yet resolved.** ~123 components reference this nickname but no entry for it exists in either the project-local or global `fp-lib-table`/`sym-lib-table`; the library's location on disk hasn't been identified. Fixing it is the same class of fix as `Cherry_MX` (add a table entry once the library is found) but is a separate, not-yet-started task.

When a schematic footprint field changes, the PCB does not pick it up until forward-annotated (see above) — and even after that, already-placed instances on the board are frozen copies that won't reflect further edits to the library `.kicad_mod` file itself. If you change a footprint file after syncing, refresh affected instances individually via PCB Editor → right-click → "Update Footprint from Library".

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

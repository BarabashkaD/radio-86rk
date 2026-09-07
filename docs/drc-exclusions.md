# Retained DRC violations

DRC cannot reach zero on this board, and should not. All 22 remaining violations are
properties of skiselev's v1.4 design, preserved deliberately under the project's
board-is-frozen constraint. None is a migration regression: the gerber and drill output is
byte-identical to v1.4, verified by `python3 tools/kicad-verify.py gerber`.

They are warnings, not errors. `unconnected_items` and `schematic_parity` are both zero.

## 17 × `silk_edge_clearance`

Silkscreen graphics that approach or cross the board outline. KiCad 4 did not check this;
KiCad 10 does. **Every one is on an edge-mounted I/O part**, where a silkscreen outline
crossing the board edge is what you would expect — the connector body overhangs the edge by
design.

| Ref | Part | Count |
|---|---|---:|
| J1 | RCA composite video jack | 2 |
| J2 | Barrel power jack | 2 |
| J4 | 8-pin DIN cassette connector | 3 |
| J5 | DE9 serial connector | 5 |
| SW68 | Tactile reset switch | 2 |
| U25 | TO-220 regulator | 3 |

All sit at y ≈ 0.4–25 mm, along the board's rear I/O edge.

Fixing them means moving silkscreen, which changes the fab output for purely cosmetic
benefit and breaks the byte-identical guarantee.

**Reason to record:** `preserved from v1.4 original, not a regression`

## 5 × `starved_thermal`

Thermal reliefs on the `GND` zone with insufficient spoke connection — KiCad reports
"1 spokes connected to isolated island" on layer B.Cu.

| Pad | Position (mm) |
|---|---|
| C29 pad 1 | (43.18, 54.61) |
| R14 pad 2 | (88.90, 29.21) |
| U7 pad 20 | (109.22, 36.83) |
| U16 pad 7 | (254.00, 26.67) |
| U26 pad 7 | (83.82, 10.16) |

Present in the original routing. Fixing them means altering zone or pad geometry.

**Reason to record:** `preserved from v1.4 original, not a regression`

## Marking them as exclusions in KiCad

The list above is the durable record. Marking each violation as an *excluded* item in
KiCad additionally cleans the DRC panel, and is a GUI action:

In **Pcbnew → Inspect → Design Rules Checker**, run DRC, then right-click each violation →
**Exclude with comment**, pasting the reason above. Save the board and the project.

**This cannot reliably be scripted.** Exclusions live in `Radio-86RK.kicad_pro` under
`board.design_settings.drc_exclusions` as `[serialised_marker, comment]` pairs, where the
serialised marker is `type|posX_nm|posY_nm|uuid|uuid`. Generating those externally was tried
and did not take: `kicad-cli pcb drc` re-runs the check from scratch and builds fresh
markers, so a hand-written entry does not match. Let KiCad write them.

## Not in this list

The keyboard adds nothing. Task 7 attached 3D models to the switch footprints without
replacing them, so no switch geometry changed and no new violation appeared.

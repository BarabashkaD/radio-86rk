# Radio-86RK — KiCad 10 Modernization Design

**Date:** 2026-09-04
**Status:** Approved
**Base branch:** `master` (9476ec3)

## Goal

Modernize the Radio-86RK project for full compatibility with current KiCad, reusing
publicly available components wherever it is safe to do so, ending in a complete 3D
render of the board with every component modeled.

Work proceeds in small, independently verifiable increments. Each increment leaves the
project strictly better than before and can be stopped at any point.

## Constraints

1. **Preserve the board exactly.** No copper feature, pad, or drill hole moves. The fab
   output stays equivalent to skiselev's v1.4. The one authorized exception is the
   keyboard slice (see Cherry MX Exception).
2. **Public reuse where it is free of risk.** 3D models and symbols reuse public
   libraries aggressively. Footprint geometry does not.
3. **Every substitution is judged, not assumed.** A difference is a breaking change only
   when it changes behavior or geometry — not merely because two definitions differ.

## Starting State (measured 2026-09-04)

`master` is a clean, fully routed board.

| Metric | Value |
|---|---:|
| ERC violations | 243 (100% warnings, 0 errors) |
| DRC violations | 91 (100% warnings, 0 errors) |
| Unconnected items | 0 |
| Schematic/board parity | 0 |
| Footprints on board | 191 |
| Footprints with a resolving 3D model | **0** |

ERC breaks down as 142 `lib_symbol_mismatch`, 67 `footprint_link_issues`,
32 `same_local_global_label`, 2 `lib_symbol_issues`.

DRC breaks down as 67 `lib_footprint_issues`, 17 `silk_edge_clearance`,
5 `starved_thermal`, 2 `lib_footprint_mismatch`.

All 19 distinct 3D model paths are KiCad 4-era (`dil/`, `discret/`, `pin_array/`) and
resolve to nothing on KiCad 10. 109 footprints carry a broken model reference; 82 carry
none at all.

### Library situation

- `my_components` (symbols) and `My_Components` (footprints) come from
  `github.com/skiselev/my_kicad_library` — 502 symbols, 256 footprints. Recovered and
  cloned as a sibling checkout on 2026-09-04. Registering it took ERC 413 → 243 and
  DRC 212 → 91.
- `Cherry_MX` is **genuinely lost**. The board references `CHERRY_PCB_100H`,
  `CHERRY_PCB_125H`, `CHERRY_PCB_150H`, `CHERRY_PCB_225H`, `CHERRY_PCB_625H`. None
  exist anywhere on disk and none are in `my_kicad_library`.

## Section 1 — The Equivalence Rubric

The question "is this a real breaking change?" resolves differently per layer.

| Layer | Touches copper | Test | Public reuse |
|---|---|---|---|
| 3D model | No — appearance only | Renders at correct size, orientation, Z-height | Aggressive |
| Symbol | No — schematic only | Pin numbers map 1:1 onto existing pad names; netlist unchanged | Where pin-compatible |
| Footprint | **Yes** | Pad-for-pad identity with the board's embedded geometry | Rare |

### Tolerance policy

**Tolerance does not apply at the footprint layer.** Once the board is preserved exactly,
the question is not "is 2.286 mm close enough to 2.5 mm?" but "does the gerber change?"
That is binary and machine-checkable.

**Tolerance does apply at the 3D layer.** A model whose body is a fraction of a millimetre
off, or a generic TO-92 standing in for a Soviet transistor, is correct for this purpose.
This is where public reuse pays, and it carries no fidelity risk.

### Default footprint resolution: vendor from the board

The board is the authoritative geometry source. It embeds all 191 footprints, including
those whose libraries are lost. Footprints are extracted from `Radio-86RK.kicad_pcb` into
a project library, guaranteeing identity by construction. A public footprint is adopted
only when pad-for-pad identical.

### Cherry MX Exception

**Decision:** adopt the public perigoso footprint despite a geometry change, verified
against physical hardware.

Measured comparison, `CHERRY_PCB_100H` vs `SW_Cherry_MX_PCB_1.00u`:

| | Original | perigoso |
|---|---|---|
| pad 1 | (2.54, −5.08) | (−3.81, −2.54) |
| pad 2 | (−3.81, −2.54) | (2.54, −5.08) |
| pad size / drill | 2.286 / 1.4986 | 2.5 / 1.5 |
| center hole | 3.9878 | 4.0 |
| side holes | 1.7018 | 1.75 |

Both pad *positions* are identical; only the names are swapped. The original is
imperial-derived (0.059″, 0.157″, 0.067″); perigoso is the metric-rounded equivalent of
the same physical part. The drill difference is 1.4 µm.

**The pin-name swap is functionally significant even though the switch is not polarized.**
KiCad binds nets to pads by name. On SW54, `master` has pad 1 → `/Keyboard/ROW6` at
(2.54, −5.08) and pad 2 → `/Keyboard/K_PB5` at (−3.81, −2.54). Adopting perigoso moves
both nets to the opposite hole while the copper tracks stay put, producing shorts at
identical coordinates. This is the cause of the 199 `shorting_items` observed on
`migrate2kicad10` — not the pad diameter.

The exception therefore carries three obligations:

1. Adopt `SW_Cherry_MX_PCB_*u` from the perigoso PCM library (brings a 3D model).
2. **Swap the schematic pin assignment** on every affected switch so each net returns to
   its original physical hole. Mandatory — skipping this shorts the keyboard matrix.
   Electrically free, because the switch has no polarity.
3. **Verify on the physical prototype** that the 2.5 mm pads clear adjacent copper.
   Measurement precedes any DRC exclusion, never the reverse.

## Section 2 — Repository & Library Architecture

```
radio-86rk/
├── KiCad/
│   ├── sym-lib-table          ${KIPRJMOD}-relative, committed
│   ├── fp-lib-table           ${KIPRJMOD}-relative, committed
│   ├── Radio86RK.pretty/      vendored: geometry recovered from the board
│   └── Radio86RK.kicad_sym    vendored: symbols with no public equivalent
└── docs/superpowers/specs/
```

**Tier 1 — public, referenced not copied.** KiCad's `.3dshapes`, `Package_DIP`,
`Resistor_THT`, and the perigoso keyswitch library via `${KICAD10_3RD_PARTY}`. Used for
3D models everywhere, symbols where pin-compatible, footprints only for the Cherry MX
exception.

**Tier 2 — vendored from the board.** Footprints whose library is lost or whose geometry
must not move, extracted from the PCB into `Radio86RK.pretty/`.

**Tier 3 — `my_kicad_library` sibling clone: reference only.** Useful for comparison and
symbol metadata recovery, but nothing in the repo may require it. This is what makes a
fresh clone work anywhere. The `${KIPRJMOD}/../../` table entries written on 2026-09-04
are rewritten to point at Tier 2.

All library URIs use `${KIPRJMOD}` or `${KICAD10_*}` variables. No absolute paths.

## Section 3 — Slice Workflow

### Inventory (191 footprints)

| Family | Count | Model state | Notes |
|---|---:|---|---|
| `SW` switches | 68 | 67 none, 1 broken | the exception slice |
| `C` capacitors | 44 | 44 broken | standard THT |
| `U` ICs | 27 | 25 broken, 2 none | DIP in sockets |
| `R` resistors | 15 | 15 broken | standard THT |
| `D` diodes/LEDs | 11 | 11 broken | DO-35, 3 mm LED |
| `J`/`JP` connectors | 9 | 9 broken | RCA, DIN, DE9, IDC |
| `HOLE` | 7 | none | no model needed |
| `RN` arrays | 4 | none | SIP6 / SIP10 |
| `Q`/`Y`/`SP`/`F`/`LOGO` | 6 | 4 broken, 2 none | misc |

3D coverage target is **183**, excluding 7 mounting holes and 1 silkscreen logo.

### Slice order — risk ascending

1. **Foundation** — capture gerber baseline, build the diff harness, rewrite both lib
   tables to Tier 2.
2. **Passives** `R`+`C`+`D`+`Y`+`F` — 72 components (38% of the board). Maps to
   `Resistor_THT.3dshapes`, `Capacitor_THT.3dshapes`, `Diode_THT.3dshapes`,
   `Crystal.3dshapes`.
3. **DIP ICs** `U` — 27, of which 24 are socketed and get two-model composites (below).
4. **Connectors** `J`+`JP` — 9. Hardest sourcing: RCA jack, 8-pin DIN, DC jack,
   friction-lock header, DE9. Models sourced independently from manufacturer or SnapEDA
   exports.
5. **Misc** `RN`+`Q`+`SP`+`HOLE`+`LOGO` — 15.
6. **Keyboard** `SW` — 68, the copper-changing exception, verified against the prototype.

### The loop, per slice

```
inventory → classify (3 layers) → act → verify → commit
```

`act` is at most three moves per component: vendor its footprint geometry from the board,
re-home its symbol if a pin-compatible public one exists, repoint its 3D model at a public
asset.

### Socket composites (slice 3)

ICs are installed in DIP sockets. Each socketed IC carries **two model entries on one
footprint** — socket at board level, chip raised to the socket's seating height:

```
(model ".../Package_DIP.3dshapes/DIP-14_W7.62mm_Socket.step" (offset (xyz 0 0 0)))
(model ".../Package_DIP.3dshapes/DIP-14_W7.62mm.step"        (offset (xyz 0 0 5.48)))
```

### Sockets actually used — Amphenol FCI DILB `-223TLF`

The prototype uses Amphenol FCI DILB series **stamped-and-formed** DIP sockets (not
machined turned-pin). Dimensions from distributor data, 2026-09-04:

| Part | Length | Height | Depth | Row spacing | Board ICs |
|---|---:|---:|---:|---:|---|
| `DILB8P-223TLF` | 10.16 | **5.1** | 10.16 | 7.62 | U21, U23, U24 |
| `DILB14P-223TLF` | 17.78 | **5.48** | 10.16 | 7.62 | U15–U20 |
| `DILB16P-223TLF` | 20.32 | **5.48** | 10.16 | 7.62 | U2, U14, U22 |
| `DILB20P-223TLF` | 25.4 | **5.48** | 10.16 | 7.62 | U12 |
| `DILB24P-223TLF` | 30.48 | **5.48** | 17.78 | 15.24 | U4, U13 |
| `DILB28P-223TLF` | 35.56 | **5.48** | 17.78 | 15.24 | U3, U9, U10, U11 |
| `DILB40P-223TLF` | 50.8 | **5.48** | 17.78 | 15.24 | U1, U5, U6, U7, U8 |

**On the height figures.** Amphenol's own spec sheet publishes Dim A/B/C/D, pitch, row
spacing and tail length but **no overall height** — verified directly against the
`DILB16P-223TLF` datasheet. The height comes from distributor package data, which is
indexed for the 14/16/28/40 parts and for the 0.3″ sibling `DILB24P-224TLF`, all of which
report 5.48 mm across both row spacings and from 14 to 40 positions. Height is a property
of the insulator's extruded cross-section and does not vary with body length, so 5.48 mm
is taken for the 20- and 24-pin as well. The 8-pin at 5.1 mm is the sole outlier.

This is a 3D-appearance parameter, not a geometry one: a 0.38 mm error would be invisible
in the viewer and cannot affect the board. Per §4, be generous here.

**Z-offset rule: 5.1 mm for 8-pin, 5.48 mm for all other sizes.**

**24 of 27 `U` components are socketed.** The exceptions are `U25`/`U27` (3-pin
regulators) and `U26` (7-pin DC-DC converter), which are not DIP parts and take a single
model each.

The prototype is populated with **Western parts only** (Intel `P8255A-5`, NEC `8257C-5`,
TI `SN74198N`, `74LS74`), not the Soviet equivalents named in the dual silkscreen
markings. Symbol and 3D choices follow the Western parts.

All required models are public and verified present:

| Legacy model | Public socket | Public chip |
|---|---|---|
| `dil_8.wrl` | `DIP-8_W7.62mm_Socket.step` | `DIP-8_W7.62mm.step` |
| `dil_16.wrl` | `DIP-16_W7.62mm_Socket.step` | `DIP-16_W7.62mm.step` |
| `dil_20.wrl` | `DIP-20_W7.62mm_Socket.step` | `DIP-20_W7.62mm.step` |
| `dil_24-w600.wrl` | `DIP-24_W15.24mm_Socket.step` | `DIP-24_W15.24mm.step` |
| `dil_28-w600.wrl` | `DIP-28_W15.24mm_Socket.step` | `DIP-28_W15.24mm.step` |
| `dil_40-w600.wrl` | `DIP-40_W15.24mm_Socket.step` | `DIP-40_W15.24mm.step` |

The two-model composite is a technique, not an asset — every socket and chip model is
public, so nothing is carried over from `migrate2kicad10`.

## Section 4 — Failure Paths

**No acceptable public 3D model.** Fall back in order: a visually equivalent public model
of the same package, then a scaled sibling, then leave it blank and record it. A missing
model is cosmetic, never a blocker. `HOLE` and `LOGO` are permanently in this category.

**No pin-compatible public symbol.** Keep the vendored symbol in `Radio86RK.kicad_sym`.
Soviet-designation and Intel MCS-80 parts mostly land here, which is correct.

**Gerber diff non-empty on a slice that should be clean.** Hard stop, revert the slice,
investigate. Non-negotiable — it means something moved that nobody decided to move. The
keyboard slice is the sole pre-authorized exception, and its diff is reviewed feature by
feature rather than accepted wholesale.

Two of these three failures are acceptable outcomes; only the copper failure is fatal.
Be generous and fast at the 3D and symbol layers, paranoid at the footprint layer.

## Section 5 — Verification & Definition of Done

### Three gates per slice

**1. Copper gate — mandatory, binary**

```
kicad-cli pcb export gerbers + export drill → strip header timestamps → diff vs baseline
```

Baseline captured once from `master` before any change. Gerber headers carry generation
timestamps and must be stripped before comparison, or every file reports as changed.

**2. 3D gate — visual, automated**

```
kicad-cli pcb render → PNG per slice
```

Produces a visual progress record and catches models that are wrong in size, orientation,
or Z-height.

**3. Rule gate — trend, not threshold**

ERC and DRC counts recorded per slice. They should fall monotonically. An increase is a
flag even with clean gerbers.

### Definition of done

| Metric | Now | Target |
|---|---:|---:|
| Components rendering in 3D | 0 | **183 / 183** |
| ERC violations | 243 | **0** |
| DRC violations | 91 | **22, documented** |
| Gerber diff vs v1.4 | — | **empty** (keyboard excepted) |
| Fresh clone works standalone | no | **yes** |

ERC reaches zero honestly — all four causes are schematic- and library-level and none
touch copper.

**DRC cannot reach zero, and should not.** The 17 `silk_edge_clearance` and
5 `starved_thermal` violations are properties of the original board, preserved
deliberately. They are recorded as **KiCad DRC exclusions carrying a written reason**
("preserved from v1.4 original, not a regression"), so a future reader sees deliberate
decisions rather than unexplained warnings.

The keyboard slice adds its own delta. Those exclusions are written only after the
prototype ruler check confirms physical clearance.

## Out of Scope

- `migrate2kicad10` entirely. The plan is based on `master` only — no footprints, models,
  libraries or relink decisions are carried over from that branch. It remains readable as
  history and as a source of research notes, but contributes no content.
- The U3/U22 RS-232 wiring defect (GitHub issue #2). Preserve-exactly excludes fixing it.
  Note that ERC on `migrate2kicad10` reports 0 violations, which does **not** establish
  the defect is fixed — converting local labels to global gives those pins a driver and
  silences ERC without moving a wire. Unresolved; out of scope here.
- Adding `my_kicad_library` as a git submodule. Rejected: the vendoring approach removes
  the dependency entirely.
- STEP assembly export and photorealistic renders. The 3D target is correctness in
  KiCad's 3D viewer.

## Open Items

- `sw3-official-reroute-experiment` holds 6 unpushed commits of pad-swap work built on a
  pre-migration base. Its pad-swap logic is now known to be *necessary* under the Cherry
  MX exception. Evaluate whether to salvage it or redo the swap on `master` during
  slice 6.

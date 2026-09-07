# 3D model sources and substitutions

Per the design spec's equivalence rubric, the 3D layer is appearance-only: it touches no
copper, so visually equivalent public models are preferred over exact ones. Every
substitution is recorded here.

Models attach to footprint *definitions*, not to references, which is why 76 components are
covered by 8 assignments. Paths use `${KICAD10_3DMODEL_DIR}`, `${KICAD10_3RD_PARTY}` or
`${KIPRJMOD}` so the project stays portable. KiCad 10 ships `.step` files, not `.wrl`.

Coverage is measured with `the `models` command`, which counts only models whose file
actually resolves — the board began with 109 footprints carrying KiCad-4-era references
(`dil/`, `discret/`, `pin_array/`) that pointed at nothing.

## Passives — 76 components, 8 footprints

| Footprint | Refs | Count | Model | Note |
|---|---|---:|---|---|
| `Res_762` | R1–R15 | 15 | `Resistor_THT/R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal` | exact lead pitch |
| `Cap_Cer_508` | C1–C32, F1 | 39 | `Capacitor_THT/C_Disc_D5.0mm_W2.5mm_P5.00mm` | see F1 note |
| `Cap_Elec_Radial_6.3mm` | C33–C38 | 6 | `Capacitor_THT/CP_Radial_D6.3mm_P2.50mm` | exact |
| `Diode_762` | D1–D9 | 9 | `Diode_THT/D_DO-35_SOD27_P7.62mm_Horizontal` | exact |
| `LED_3mm` | D10, D11 | 2 | `LED_THT/LED_D3.0mm` | exact |
| `Crystal_HC-49U_Vert` | Y1 | 1 | `Crystal/Crystal_HC49-U_Vertical` | exact |
| `Transistor_TO92_EBC_254` | Q1, Q2, U27 | 3 | `Package_TO_SOT_THT/TO-92_Inline` | generic TO-92 for the Soviet KT-series |
| `IC_TO220-3_Vert` | U25 | 1 | `Package_TO_SOT_THT/TO-220-3_Vertical` | exact package |

**F1 renders as a disc capacitor.** F1 is a fuse but is placed on the `Cap_Cer_508`
footprint, and models attach to footprints rather than to references. Splitting the
footprint solely to change F1's appearance would mean a second library part with identical
copper — cost without benefit. Accepted under the tolerance policy.

**U27 is a TO-92 transistor, not a regulator.** The design spec's prose calls U25 and U27
regulators; the board says `Transistor_TO92_EBC_254`. The board is right.

## Socketed DIP ICs — 24 components, 7 footprints

Every DIP on this board sits in a socket, so each DIP footprint carries **two** models: the
socket at board level and the chip raised to the socket's seating height. U25 (TO-220),
U26 (SIP DC-DC) and U27 (TO-92) are not DIP parts and take a single model each.

| Footprint | Refs | Socket (z=0) | Chip (z=offset) | Offset |
|---|---|---|---|---:|
| `IC_DIP8_300` | U21, U23, U24 | `DIP-8_W7.62mm_Socket` | `DIP-8_W7.62mm` | 5.1 |
| `IC_DIP14_300` | U15–U20 | `DIP-14_W7.62mm_Socket` | `DIP-14_W7.62mm` | 5.48 |
| `IC_DIP16_300` | U2, U14, U22 | `DIP-16_W7.62mm_Socket` | `DIP-16_W7.62mm` | 5.48 |
| `IC_DIP20_300` | U12 | `DIP-20_W7.62mm_Socket` | `DIP-20_W7.62mm` | 5.48 |
| `IC_DIP24_600` | U4, U13 | `DIP-24_W15.24mm_Socket` | `DIP-24_W15.24mm` | 5.48 |
| `IC_DIP28_600` | U3, U9, U10, U11 | `DIP-28_W15.24mm_Socket` | `DIP-28_W15.24mm` | 5.48 |
| `IC_DIP40_600` | U1, U5–U8 | `DIP-40_W15.24mm_Socket` | `DIP-40_W15.24mm` | 5.48 |

Row spacing follows the board: `*_300` footprints are 300 mil (7.62 mm), `*_600` are
600 mil (15.24 mm).

**Where the heights come from.** The prototype uses Amphenol FCI DILB `-223TLF`
stamped-and-formed sockets. Amphenol's spec sheet publishes Dim A/B/C/D, pitch, row spacing
and tail length but no overall height. Distributor package data reports 5.48 mm for the 14,
16, 28 and 40 position parts and for the 0.3″ sibling `DILB24P-224TLF`, across both row
spacings and from 14 to 40 positions. Height is a property of the insulator's extruded
cross-section and does not vary with body length, so 5.48 mm is taken for the 20- and
24-pin as well. The 8-pin at 5.1 mm is the only outlier.

This is a 3D-appearance parameter, not a geometry one: a 0.38 mm error would be invisible
in the viewer and cannot reach the board.

**Western parts, not Soviet.** The prototype is populated with Intel `P8255A-5`, NEC
`8257C-5`, TI `SN74198N` and `74LS74` rather than the Soviet equivalents in the dual
silkscreen markings, so package choices follow the Western parts.

## Connectors, arrays and misc — 15 components, 12 footprints

| Footprint | Refs | Model | Fidelity |
|---|---|---|---|
| `Conn_SIL6` | RN2–RN4 | `Resistor_THT/R_Array_SIP6` | exact pin count and pitch |
| `Conn_SIL10` | RN1 | `Resistor_THT/R_Array_SIP10` | exact pin count and pitch |
| `Conn_Pin_Header_4x1_2.54mm` | JP1, JP2 | `PinHeader_1x04_P2.54mm_Vertical` | exact |
| `Conn_Pin_Header_20x1_2.54mm` | J7 | `PinSocket_1x20_P2.54mm_Vertical` | female — see below |
| `Conn_Pin_Header_13x2_2.54mm_Shrouded` | J6 | `IDC-Header_2x13_P2.54mm_Vertical` | exact |
| `Conn_Friction_Lock_8P_2.54mm` | J3 | `Radio86RK.3dshapes/640456-8` | **the real part** — see below |
| `Conn_Power_Jack_Circular_Pads` | J2 | `Radio86RK.3dshapes/KLDX-0202-A` | **the real part** |
| `Conn_Dsub_DE9M` | J5 | `DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm` | housed, with mounting hardware |
| `Speaker_12mm` | SP1 | `Radio86RK.3dshapes/AT-1224-TWT-R` | **the real part** |
| `DC-DC_SIP8` | U26 | `Radio86RK.3dshapes/IZ0512S` | scaled sibling — see below |

`RN1`–`RN4` are SIP resistor networks, so `R_Array_SIP6`/`SIP10` are used rather than pin
headers — same pin count and pitch, correct body.

**J7 is a socket, not a header, despite its footprint name.** The name
`Conn_Pin_Header_20x1_2.54mm` is inherited from the board and cannot change without
changing a `lib_id`, but skiselev's BOM calls for a 3M **929850-01-20-RB** — a female
receptacle strip (Mouser 517-929850-01-20-RB) for the optional extension board. It rendered
as 20 male pins until this was caught in a render. KiCad's `PinSocket_1x20_P2.54mm_Vertical`
has pads identical to the header's, so only the model changed and the transform is
unaffected. J6 and JP1/JP2 were checked against the BOM at the same time and are genuinely
male headers.

### The seven KiCad does not ship

KiCad has no RCA, cinch or phono model, no 8-pin DIN, and nothing for the XP Power IZ
series — searched every installed `.3dshapes` directory including the PCM third-party
libraries. (The one "DIN" hit is `Jack_3.5mm_Ledino_KB3SPRS`, whose *part name* contains
the string.) Four more parts had a stock model that was the right *category* and the wrong
manufacturer.

All seven came from the abandoned `migrate2kicad10` branch, which attacked the same problem
from the opposite end: it replaced each footprint with a manufacturer-sourced one that
carried its own model. Those footprint swaps moved copper and are unusable here — but a
model does not care which footprint introduced it, and the STEP files are the real parts
from skiselev's BOM. They are vendored into `KiCad/Radio86RK.3dshapes/` and referenced via
`${KIPRJMOD}`, so a fresh clone renders them with nothing installed.

| Ref | Part | STEP origin |
|---|---|---|
| J1 | Same Sky / CUI **RCJ-014** RCA phono | SnapEDA (`CUI_DEVICES_RCJ-014.step`) |
| J2 | Kycon **KLDX-0202-A** 2 mm DC jack | SamacSys / Ultra Librarian (`KLDX-0202-A.STEP`) |
| J3 | TE / AMP **640456-8** MTA-100 header | Tyco Electronics (`C-640456-8`, 2013) |
| J4 | Same Sky / CUI **SDF-80J** DIN-8 | manufacturer (`same sky SDF-80J.STEP`) |
| SP1 | PUI **AT-1224-TWT-R** 12 mm transducer | SamacSys, via FreeCAD/OCC |
| SW68 | Omron **B3F-3152** tactile | manufacturer (`B3F_3152.step`) |
| U26 | XP Power **IZ0512S** DC-DC | sibling IA0512S, scaled — below |

**The models are checked against our pads before being reused.** Two libraries drawing the
same part is a premise, not a fact, so `tools/align_models_legacy.py` brute-forces the four
90° rotations, lands our pad 1 on theirs, and reports the worst distance from any of our
pads to the nearest same-named pad of theirs:

| Footprint | fit rotation | worst pad residual |
|---|---:|---:|
| `DC-DC_SIP8` | 0° | 0.0000 mm |
| `Conn_DIN_8pin` | 180° | 0.0000 mm |
| `Conn_Friction_Lock_8P_2.54mm` | 180° | 0.0000 mm |
| `Switch_Tactile_6mm_Right` | 180° | 0.0009 mm |
| `Speaker_12mm` | 90° | 0.0024 mm |
| `Conn_Power_Jack_Circular_Pads` | 0° | 0.1006 mm |
| `Conn_RCA_Right` | 0° | 0.5800 mm |

J1's 0.58 mm is a known error in the *board's* own hand-drawn footprint: measured against
the RCJ-01 datasheet, the manufacturer's signal-to-odd-ground spacing is right and the
board's is 0.58 mm out. It is copper, so it stays as it is; at the 3D layer it is invisible.

#### U26 is the one model that is not the real part

No STEP exists for the IZ0512S anywhere. The old branch substituted the manufacturer's
model for the sibling **IA0512S** — same potted-SIP construction — and scaled it to the IZ's
body. That is a sound approach, and its two ratios were right, but they were applied to the
wrong axes.

The branch's note orders both parts *L × H × W*: IA `19.3 × 10.1 × 6.0`, IZ
`21.85 × 11.10 × 9.20`. The IZ figures are correct — page 1 of
`Documentation/XP Power - DC-DC Converter - IZ Series.pdf` gives 0.86″ (21.85) long,
0.44″ (11.10) high and 0.36″ (9.20) wide on the bottom view. But the STEP itself is authored
Z-up, so *its* axes run L × W × H; measuring the file gives X 19.30, Y 6.09, Z −5.00…10.16.
Stored as `(1.1321, 1.0990, 1.5333)` the height ratio lands on width and the width ratio on
height, rendering U26 about **15.6 mm tall and 6.7 mm thick** instead of 11.10 × 9.20 — a
brick with the right footprint and visibly wrong proportions, filling only part of the v1.4
silkscreen outline.

Corrected to `(1.1321, 1.5107, 1.0925)` in `align_models_legacy.py`'s `SCALE_FIX`, so
re-running the tool reproduces the fix rather than the bug. The body now fills its silk
outline. The board is designed to accept alternatives anyway (README: Traco TMR 3E, Recom
RS3, Cincon EC3SA), so a correctly-proportioned SIP brick of the right family is a fair
representation even though the mould is a sibling's.

#### Licensing

All seven are vendor-published mechanical models, redistributed from the manufacturer or
from SnapEDA / Ultra Librarian exports of manufacturer data. They are geometry for
documentation and rendering, carry no copper, and are not part of the fabrication output —
the gerbers are byte-identical with or without them.

## Keyboard — 68 switches, 6 footprints

| Footprint | Refs | Model(s) | Note |
|---|---|---|---|
| `CHERRY_PCB_100H` | 62 keys | `SW_Cherry_MX_PCB` | perigoso, via PCM |
| `CHERRY_PCB_125H` | SW65, SW66 | `SW_Cherry_MX_PCB` | |
| `CHERRY_PCB_150H` | SW61 | `SW_Cherry_MX_PCB` | |
| `CHERRY_PCB_225H` | SW11 | `SW_Cherry_MX_PCB` + `Stabilizer_Cherry_MX_2.00u` | composite |
| `CHERRY_PCB_625H` | SW64 | `SW_Cherry_MX_PCB` + `Stabilizer_Cherry_MX_6.25u` @ 180° | composite, mirrored |
| `Switch_Tactile_6mm_Right` | SW68 | `Radio86RK.3dshapes/B3F-3152` | reset switch, the real Omron part |

**The footprints are the board's own, not perigoso's.** Only the models come from perigoso.
The design spec proposed adopting perigoso's footprints on the grounds that doing so
"brings a 3D model", but models attach to any footprint by name, and both libraries put the
switch's centre guide boss at (0, 0) — verified — so the model lands correctly on the
original geometry with no offset.

Keeping the board's footprints avoided a 2.286 → 2.5 mm pad growth on 67 switches, the
compensating schematic pin swap, two clearance violations at 0.150 mm needing prototype
measurement, and the loss of SW11/SW64's stabilizer holes. Cost: perigoso's tidier
silkscreen and a real `F.CrtYd` courtyard. Cherry specifies hole sizes (⌀1.5 mm terminals,
⌀4.0 mm boss, ⌀1.7 mm locating pins), not land diameter, so the board's 2.286 mm pads are
as legitimate as perigoso's 2.5 mm.

### Why SW64's stabilizer is rotated 180°

The board mounts the spacebar stabilizer opposite to the 2.25u one, in the footprint's own
frame:

| | ⌀3.9878 (housing) | ⌀3.048 (wire) |
|---|---|---|
| Board SW11 (2.25u) | y = +8.255 | y = −6.985 |
| perigoso `Stabilizer_2.00u` | y = +8.225 | y = −6.985 |
| Board SW64 (6.25u) | y = **−8.255** | y = **+6.985** |
| perigoso `Stabilizer_6.25u` | y = **+8.225** | y = **−6.985** |

A 180° rotation about Z maps (x, y) → (−x, −y). Both patterns are symmetric about x = 0, so
it acts as a pure front-to-back flip and aligns the model with the board's holes. Verified
in a close render of the spacebar row: the housings sit on the board with the wire
spanning between them. At 0° the whole assembly hangs off the board edge, 16.5 mm out.

Per skiselev's README BOM, SW11 and SW64 take Cherry **G99-0742** leveling kits
(Mouser `540-G99-0742`), and SW64 additionally uses the **wire from a G99-0226** (MX 1x8,
`540-G99-0226`) fitted into G99-0742 housings. That hybrid is why SW64's 100.076 mm spacing
matches no stock 6.25u part, and why perigoso's is 38 µm out and mirrored. The stabilizer
models sit 30 µm (SW11) and 38 µm (SW64) from the board's actual hole centres — invisible in
the viewer, and exactly what the 3D tolerance policy exists to permit.

## Coverage

**183 / 183.** The 7 mounting holes and the silkscreen logo are exempt. Nothing is missing:
J4, the last gap, was closed with the manufacturer's own SDF-80J model.

## Validating the render

Automated checks catch missing models; they cannot catch a model that is present but wrong.
Do both.

### Scripted

```bash
python3 tools/kicad-verify.py models                 # counts only resolving models
python3 tools/kicad-verify.py models  # names what has none
```

Coverage counts a footprint as covered only if the model file exists on disk. The board
began with 109 footprints carrying KiCad-4-era references that pointed at nothing, so
"has a model entry" would have scored those as covered.

### Visual, in KiCad

PCB Editor → **View → 3D Viewer** (`Alt+3`). Left-drag rotates, scroll zooms.
**Preferences → Display Options → Raytracing** for a realistic render.
Hiding the board itself makes floating or sunk parts obvious.

### Visual, scripted

Top-down views hide Z errors. A low camera angle is what exposes them:

```bash
# the shot that validates seating heights
kicad-cli pcb render --output check.png --width 1600 --height 700 --quality high \
  --rotate '-72,0,0' --zoom 2.2 --pivot '-2.0,3.0,0' --perspective board.kicad_pcb
```

Reproduce the views this was checked against — renders are build output and are not
committed:
`tools/render.py --view iso-left dip` for socket seating, and `--view back profile` for
switch heights, where the edge-on elevation shows them against each other.

### What to check, and why each could be wrong

| Check | Expected | Failure mode |
|---|---|---|
| DIP seating | chip sitting *in* a socket, socket rails visible beneath | wrong Z offset — 5.1 mm for 8-pin, 5.48 mm otherwise |
| SW64 spacebar | two stabilizer housings straddling the switch, wire between, all **on** the board | wrong rotation — at 0° the assembly hangs 16.5 mm off the edge |
| SW11 (2.25u) | same, no rotation | |
| Edge connectors J2, J5, J6 | bodies pointing **outward** past the board edge | model orientation |
| Y1 crystal | standing upright | vertical vs horizontal model |
| Switch row | uniform height, all flat on the board | |
| J1 | a yellow RCA phono jack, opening past the board edge | wrong rotation would face it inward |
| J4 | a round DIN socket overhanging the edge, body inside its silk outline | composed transform wrong |
| J5 | black housing filling the silk outline, bosses on the two plated mounting holes | wrong housed variant |
| U26 | a squat brick filling its silk outline, not a tall thin one | swapped scale axes |

All of these were checked on the current board and are correct.

## Model alignment — why offsets and rotations are needed

A 3D model is authored in the coordinate frame of the KiCad footprint it ships with. Our
footprints came from a 1986 board through a different library and use different
conventions, so a model dropped in at offset (0,0,0) lands wrong. Three distinct mismatches
were found, all of them by looking at the render:

| Mismatch | Effect | Example |
|---|---|---|
| KiCad puts **pad 1 at the origin**; ours are **centred** | model sits half a pitch off — one lead in a hole, one in mid-air | `Cap_Cer_508` pads at ±2.54; KiCad's at 0 and +5.0 |
| KiCad's DIPs run their long axis along **Y**; ours along **X** | every IC appears rotated 90° | `IC_DIP40_600` is 48.26 × 15.24; KiCad's is 15.24 × 48.26 |
| Some of ours number pads in the **opposite direction** | body reversed — a diode's cathode band at the wrong end | `Diode_762` pad 1 at +3.81; KiCad's at 0 |

None of this touches copper. It is purely how the model is placed for rendering, which is
why both gerber gates passed throughout while the render was visibly wrong.

**KiCad's 3D model offset has Y inverted relative to PCB coordinates** (the 3D view has Y
up, the board has Y down); the Z rotation is not inverted. That was determined empirically
with a calibration board rendering eight candidate conventions
side by side against KiCad's own DIP-40 as a known-good reference, and only one puts the
chip body between its pad rows. It is also why the passives looked right while every IC was
visibly wrong: the passives all have `off_y` = 0, so the inversion changes nothing for them.

`tools/align_models.py` derives the transform from geometry rather than guessing: it takes
the pad-1 → pad-N vector in each footprint, rotates by the angle between them, and
translates so the model's pad 1 lands on ours. The results are written into `models.tsv` as
explicit `off_x`, `off_y`, `off_z`, `rot_z` columns, so the data records what is applied and
the tool records why.

Of 27 footprints with stock KiCad models, **only the switches needed no correction** — and
those were verified separately, since both libraries put the switch's centre boss at (0,0).

### Manufacturer models need two more degrees of freedom

KiCad's own models are all authored Z-up in the footprint frame, so `off_x, off_y, off_z,
rot_z` is enough for them. Vendor models are not: they arrive in whatever frame the vendor's
CAD used — several of these are exported lying on their side and need `rot_x = -90` — and
the U26 substitution needs a scale. `models.tsv` therefore takes five optional trailing
columns, `rot_x rot_y sx sy sz`, defaulting to 0 and 1.

The transforms for those seven are *composed*, not measured: each model already had a
placement inside the old branch's own footprint, and our footprint differs from theirs by a
Z rotation θ and a translation. KiCad renders a model as

```
translate(offset) . Rz(-rot_z) . Ry(-rot_y) . Rx(-rot_x) . scale
```

so pre-multiplying Rz(θ) gives `translate(Rz(θ)·offset + δ) . Rz(-(rot_z + θ)) . Ry . Rx .
scale` — the stored Z rotations simply add, `rot_x`/`rot_y`/`scale` pass through, and the
old offset is rotated by θ before δ is added. `tools/align_models_legacy.py` does this and
prints the rows. J4 is the case that proves the algebra: θ = 180° over a non-zero offset and
an X rotation, and the model lands inside its silkscreen outline to the pixel.

**Automated coverage cannot catch this.** the `models` command proves a model file resolves;
it says nothing about whether the model is placed correctly. Only the render does. See the
validation section above.

### Connector alignment, verified

Checked numerically (does the transform map every pad?) and visually:

| Ref | Footprint | rot | worst pad error | Visual |
|---|---|---:|---:|---|
| J5 | `Conn_Dsub_DE9M` | 180° | 0.107 mm | housing fills the silk outline, shell past the board edge, bosses on the mounting holes |
| J6 | `Conn_Pin_Header_13x2_2.54mm_Shrouded` | 270° | 0.000 mm | shroud opening faces up |
| J7 | `Conn_Pin_Header_20x1_2.54mm` | 270° | 0.000 mm | a socket body with a row of receptacle holes, not pins |
| JP1, JP2 | `Conn_Pin_Header_4x1_2.54mm` | 270° | 0.000 mm | pins on pads, body within the silk outline |
| RN1 | `Conn_SIL10` | 0° | 0.000 mm | |
| RN2–RN4 | `Conn_SIL6` | 0° | 0.000 mm | |
| J3 | `Conn_Friction_Lock_8P_2.54mm` | 180° | 0.000 mm | posts on pads (rotation changed with the 640456-8 model) |

J5's 0.107 mm is KiCad's generic 2.77/2.84 mm DSUB pitch against the board's exact
2.7432/2.8448 (0.108"/0.112"). Neither matters at the 3D layer.

**J5 uses a housed variant, and our footprint does have somewhere to put the hardware.** Its
two 3.05 mm pads named `0` at ±12.494 are the connector's plated mounting holes, sitting on
the centreline between the pin rows — there are no *non-plated* holes, which is a different
thing. Of KiCad's five housed right-angle DE9 models, three put their mounting holes on that
centreline; the `EdgePinOffset4.94mm` and `EdgePinOffset14.56mm_...Offset8.20mm` variants
put them at row-2 height instead, a real mechanical mismatch rather than a naming one. The
three survivors differ only in how far the shell stands off the pins, and the board's near
pin row sits 8.178 mm from the edge, so `EdgePinOffset7.70mm` is the fit and the shell
overhangs by 0.478 mm.

Reference renders: `validate-ic-alignment.png`, `validate-connectors.png`,
`validate-jumpers.png`.

### Polarity, verified against the netlist

Placement being right does not mean *orientation* is right — a diode can sit perfectly on
its pads with the band at the wrong end. Checked through the whole chain rather than by
eye alone.

**Diodes (D1–D9, `Diode_762`).** `Device:D` numbers pin 1 = K (cathode). Our footprint
makes pad 1 the **square** pad at (+3.81, 0) and puts a filled silkscreen band at
x = 0.762…1.27, on the pad-1 side — so the board's own marking agrees that pad 1 is the
cathode. KiCad's `D_DO-35_SOD27_P7.62mm_Horizontal` also puts the cathode at pad 1, and the
transform maps KiCad's pad 1 onto ours, so the model's band lands on the cathode.
Confirmed by rendering the diode rows: square pad and red band on the same end.

**Electrolytics (C33–C38, `Cap_Elec_Radial_6.3mm`).** Symbol `Device:C_Polarized_US`,
pin 1 = +. Our footprint makes pad 1 the square pad and carries a `+` silkscreen at
(−3.175, 2.54), the pad-1 side. Netlist check across all six:

| Cap | pin 1 (+) | pin 2 (−) | |
|---|---|---|---|
| C33, C34 | VCC | GND | ✓ |
| C35 | +12V | GND | ✓ |
| C36 | GND | −12V | ✓ |
| C37 | GND | −5V | ✓ |
| C38 | video in | local net | ✓ coupling cap, not a rail |

C36 and C37 look reversed relative to the others and are **correct**: on a negative rail the
`+` terminal belongs on GND, the more positive node. Every one has pin 1 on the more
positive net.

Rendered top-down, each can shows its pale stripe — the negative
marking — on the side opposite the `+` silkscreen.

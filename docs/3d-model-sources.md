# 3D model sources and substitutions

Per the design spec's equivalence rubric, the 3D layer is appearance-only: it touches no
copper, so visually equivalent public models are preferred over exact ones. Every
substitution is recorded here.

Models attach to footprint *definitions*, not to references, which is why 76 components are
covered by 8 assignments. All paths use `${KICAD10_3DMODEL_DIR}` or `${KICAD10_3RD_PARTY}`
so the project stays portable. KiCad 10 ships `.step` files, not `.wrl`.

Coverage is measured with `tools/model_coverage.py`, which counts only models whose file
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
| `Conn_Pin_Header_20x1_2.54mm` | J7 | `PinHeader_1x20_P2.54mm_Vertical` | exact |
| `Conn_Pin_Header_13x2_2.54mm_Shrouded` | J6 | `IDC-Header_2x13_P2.54mm_Vertical` | exact |
| `Conn_Friction_Lock_8P_2.54mm` | J3 | `Molex_KK-254_AE-6410-08A_1x08_P2.54mm_Vertical` | exact family |
| `Conn_Power_Jack_Circular_Pads` | J2 | `BarrelJack_CUI_PJ-063AH_Horizontal` | equivalent barrel jack |
| `Conn_Dsub_DE9M` | J5 | `DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset9.40mm` | exact |
| `Speaker_12mm` | SP1 | `Buzzer_12x9.5RM7.6` | 12 mm body, correct pitch |
| `DC-DC_SIP8` | U26 | `Converter_DCDC_Bothhand_CFUSxxxx_THT` | generic SIP DC-DC |

`RN1`–`RN4` are SIP resistor networks, so `R_Array_SIP6`/`SIP10` are used rather than pin
headers — same pin count and pitch, correct body.

### The two KiCad does not ship

Searched every installed `.3dshapes` directory including the PCM third-party libraries:
there is no RCA, cinch or phono model, and no 8-pin DIN. (The one "DIN" hit is
`Jack_3.5mm_Ledino_KB3SPRS`, whose *part name* contains the string.)

| Ref | Footprint | Decision |
|---|---|---|
| J1 | `Conn_RCA_Right` | **Fallback:** `Connector_Coaxial/BNC_Amphenol_B6252HB-NPP3G-50_Horizontal` — the nearest public shape, a horizontal panel-mount coaxial jack |
| J4 | `Conn_DIN_8pin` | **Deliberately blank.** No comparable public 8-pin DIN exists, and a visibly wrong connector is worse than an absent one. |

Both are recorded as rows in `tools/models.tsv` so the decision is visible in the data, not
just here — J4's row has `-` as its model path, which the applier treats as "handled, no
model" rather than an oversight.

To improve either, place a sourced `.step` in `KiCad/Radio86RK.3dshapes/` and reference it
via `${KIPRJMOD}` so a fresh clone still renders it. Manufacturer downloads or SnapEDA /
Ultra Librarian / GrabCAD exports are all suitable; note the origin and licence here.

**3D coverage after this task: 114/183.** The remaining 69 are the 68 switches (Task 7)
and J4.

## Keyboard — 68 switches, 6 footprints

| Footprint | Refs | Model(s) | Note |
|---|---|---|---|
| `CHERRY_PCB_100H` | 62 keys | `SW_Cherry_MX_PCB` | perigoso, via PCM |
| `CHERRY_PCB_125H` | SW65, SW66 | `SW_Cherry_MX_PCB` | |
| `CHERRY_PCB_150H` | SW61 | `SW_Cherry_MX_PCB` | |
| `CHERRY_PCB_225H` | SW11 | `SW_Cherry_MX_PCB` + `Stabilizer_Cherry_MX_2.00u` | composite |
| `CHERRY_PCB_625H` | SW64 | `SW_Cherry_MX_PCB` + `Stabilizer_Cherry_MX_6.25u` @ 180° | composite, mirrored |
| `Switch_Tactile_6mm_Right` | SW68 | `SW_Tactile_SPST_Angled_PTS645Vx31-2LFS` | reset switch |

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
in `verify/renders/07-spacebar-closeup.png`: the housings sit on the board with the wire
spanning between them. At 0° the whole assembly hangs off the board edge, 16.5 mm out.

Per skiselev's README BOM, SW11 and SW64 take Cherry **G99-0742** leveling kits
(Mouser `540-G99-0742`), and SW64 additionally uses the **wire from a G99-0226** (MX 1x8,
`540-G99-0226`) fitted into G99-0742 housings. That hybrid is why SW64's 100.076 mm spacing
matches no stock 6.25u part, and why perigoso's is 38 µm out and mirrored. The stabilizer
models sit 30 µm (SW11) and 38 µm (SW64) from the board's actual hole centres — invisible in
the viewer, and exactly what the 3D tolerance policy exists to permit.

## Coverage

**182 / 183.** The 7 mounting holes and the silkscreen logo are exempt. The single gap is
**J4**, the 8-pin DIN, for which no public model exists anywhere — see above.

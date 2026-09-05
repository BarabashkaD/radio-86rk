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

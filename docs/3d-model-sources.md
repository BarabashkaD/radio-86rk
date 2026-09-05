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

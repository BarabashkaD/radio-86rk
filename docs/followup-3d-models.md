# Follow-up: 3D models that still need work

The board is finished and verified — copper identical to v1.4, ERC 32 / DRC 22 both
documented, 3D coverage 182/183. What remains here is **appearance only**. Nothing in this
document touches copper, and every change is gated the same way: `tools/gerber-gate.sh
--strict` must still pass.

Five components render as an approximation or not at all. They are listed worst-first.

---

## 1. U26 — DC-DC converter, completely wrong

| | |
|---|---|
| Footprint | `DC-DC_SIP8` |
| Real part | **XP Power IZ0512S**, ±12 V ±125 mA, 4.5–9 V in — Mouser [209-IZ0512S](https://www.mouser.com/ProductDetail/209-IZ0512S) |
| Currently renders as | `Converter_DCDC_Bothhand_CFUSxxxx_THT` — a different manufacturer and a different body shape |
| Datasheet in repo | `Documentation/XP Power - DC-DC Converter - IZ Series.pdf` |

KiCad ships 52 DC-DC models but none of the XP Power IZ series. The closest in *format*
are `Converter_DCDC_RECOM_R5xxxPA_THT` and `Converter_DCDC_XP_POWER_JTExxxxDxx_THT`, but
neither is the right body.

**Fix:** source a model. XP Power publishes STEP files for the IZ series on the product
page; the datasheet in `Documentation/` has the mechanical drawing if one has to be built.
Save as `KiCad/Radio86RK.3dshapes/XP_Power_IZ0512S.step` and reference it via `${KIPRJMOD}`.

Note the board is designed to accept alternatives (see README line 120 — Traco TMR 3E,
Recom RS3, Cincon EC3SA are listed), so a generic SIP-8 body is a defensible compromise if
sourcing fails.

---

## 2. J4 — cassette connector, renders nothing

| | |
|---|---|
| Footprint | `Conn_DIN_8pin` |
| Real part | **CUI SDF-80J**, DIN 8-position, right angle, PCB mount — Mouser [490-SDF-80J](https://www.mouser.com/ProductDetail/490-SDF-80J) |
| Currently renders as | nothing — deliberate blank |

No 8-pin DIN model exists in any installed library; searched every `.3dshapes` directory
including the PCM third-party ones. The blank is recorded as a `-` row in `models.tsv` so it
reads as a decision, not an oversight.

**Fix:** source from CUI's product page, SnapEDA, or GrabCAD. This is the only component
with **no** representation at all, so fixing it takes coverage to the full 183/183.

---

## 3. J1 — RCA jack, wrong connector type

| | |
|---|---|
| Footprint | `Conn_RCA_Right` |
| Real part | **CUI RCJ-014**, RCA phono, yellow — Mouser [490-RCJ-014](https://www.mouser.com/ProductDetail/490-RCJ-014) |
| Currently renders as | `BNC_Amphenol_B6252HB-NPP3G-50_Horizontal` — a BNC, not an RCA |

KiCad ships no RCA, cinch or phono model at all. The BNC was chosen as the nearest public
shape: a horizontal panel-mount coaxial jack of roughly the right size. It is visibly the
wrong connector.

**Fix:** source from CUI, SnapEDA or GrabCAD. Save as
`KiCad/Radio86RK.3dshapes/RCA_CUI_RCJ-014.step`.

---

## 4. J5 — DE9, missing its housing and mounting hardware

| | |
|---|---|
| Footprint | `Conn_Dsub_DE9M` |
| Real part | **Amphenol L717SDE09P1ACH3R**, DE9 male, right angle, PCB mount — Mouser [523-L717SDE09P1ACH3R](https://www.mouser.com/ProductDetail/523-L717SDE09P1ACH3R) |
| Currently renders as | `DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset9.40mm` — bare pins and shell, no housing or board mounts |

KiCad has five **housed** right-angle DE9 variants that include the mounting hardware:

```
DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset4.94mm_Housed_MountingHolesOffset4.94mm
DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm
DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset9.90mm_Housed_MountingHolesOffset11.32mm
DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset14.56mm_Housed_MountingHolesOffset8.20mm
DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset14.56mm_Housed_MountingHolesOffset15.98mm
```

**Caveat found while checking:** our `Conn_Dsub_DE9M` footprint has **zero NPTH pads** — no
board mounting holes at all. The real connector is retained by its pins and shell alone. A
`Housed_MountingHolesOffset` model will therefore draw mounting brackets over bare board.
That is still closer to the real part than bare pins, but it is a compromise either way.

**Fix:** try the housed variants, choosing by which `EdgePinOffset` best matches our
footprint's pin-1 distance from the board edge, and re-run `tools/align_models.py` — the
transform will change, since these models have a different origin.

---

## 5. J2 — power jack, approximate

| | |
|---|---|
| Footprint | `Conn_Power_Jack_Circular_Pads` |
| Real part | **Kycon KLDX-0202-A**, DC power jack, 2 mm pin — Mouser [806-KLDX-0202-A](https://www.mouser.com/ProductDetail/806-KLDX-0202-A) |
| Currently renders as | `BarrelJack_CUI_PJ-063AH_Horizontal` — right family, wrong part |

Other candidates already installed: `BarrelJack_CUI_PJ-063BH_Horizontal`,
`BarrelJack_CUI_PJ-079BH_Horizontal`, `BarrelJack_GCT_DCJ200-10-A_Horizontal`, and the
generic `BarrelJack_Horizontal`.

**Fix:** compare each against the KLDX-0202-A drawing and pick the closest, or source the
real model. The generic `BarrelJack_Horizontal` may read better than a specifically-wrong
named part.

---

## Optional: keycaps

Currently the switches render as bare Cherry MX bodies — housing and stem, no caps. Adding
caps would make the render look like the finished machine.

**No keycap models are installed anywhere** — not in KiCad's libraries, not in the perigoso
keyswitch library, which ships only switch bodies, stabilizers and plate mounts.

Doing this properly means:

1. **Source or build a keycap model.** XDA or DSA profile, which is what skiselev
   recommends (README: *"XDA or DSA keycaps are recommended, as they have uniform shape
   regardless of the row"*). A uniform profile is a real simplification — one model serves
   every row.
2. **Five sizes are needed**, matching the footprints: 1.00u (62 keys), 1.25u (SW65, SW66),
   1.50u (SW61), 2.25u (SW11), 6.25u (SW64).
3. **Add as a second model per switch footprint**, raised to sit on the stem — the same
   composite technique the DIP sockets and stabilizers already use. The Z offset is the
   switch's mounted height; measure from the Cherry MX drawing in
   `Documentation/MX Series.pdf`.
4. Run `tools/align_models.py` if the source footprint's origin differs, then
   `tools/apply_models.py`, then check the gerber gate still passes and look at the render.

Worth noting this is the one item on this page that would change how the board *reads* at a
glance — 68 keycaps is most of the visible surface.

---

## How to do any of these

```bash
# 1. put the sourced model where a fresh clone will find it
cp downloaded.step KiCad/Radio86RK.3dshapes/<Name>.step

# 2. add or edit its row in tools/models.tsv, referencing it via ${KIPRJMOD}
#    footprint <TAB> model <TAB> off_x <TAB> off_y <TAB> off_z <TAB> rot_z

# 3. if the model comes from a KiCad footprint, let the tool compute the transform
"$KICAD_PY" tools/align_models.py

# 4. apply, then verify
"$KICAD_PY" tools/apply_models.py tools/models.tsv "$PCB" KiCad/Radio86RK.pretty
tools/gerber-gate.sh --strict          # must still PASS
"$KICAD_PY" tools/model_coverage.py "$PCB"
tools/render.sh check                  # and actually look at it
```

Record the model's origin and licence in `docs/3d-model-sources.md`.

**Look at the render.** Every 3D defect found in this project — the 90° IC rotation, the
half-pitch offsets, these five — was invisible to the automated checks and obvious in a
picture. Coverage proves a file resolves; it says nothing about whether the thing looks
right.

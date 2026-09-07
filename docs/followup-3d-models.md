# Follow-up: 3D models

The board is finished and verified — copper identical to v1.4, ERC 32 / DRC 22 both
documented, 3D coverage **183 / 183**. Everything on this page is **appearance only**.
Nothing here touches copper, and every change is gated the same way: `python3 tools/kicad-verify.py gerber
--strict` must still pass.

## Resolved

Five components rendered as an approximation or not at all. All five are now the real part,
recovered from the abandoned `migrate2kicad10` branch — see
[3D model sources](3d-model-sources.md) for the provenance table, the pad-congruence
evidence and the transform algebra.

| Ref | Was | Now |
|---|---|---|
| U26 | `Converter_DCDC_Bothhand_CFUSxxxx_THT` — wrong manufacturer, wrong body | XP Power **IZ0512S**, via the sibling IA0512S rescaled to the datasheet |
| J4 | nothing | Same Sky / CUI **SDF-80J** DIN-8, the manufacturer's own model |
| J1 | `BNC_Amphenol_B6252HB-NPP3G-50_Horizontal` — a BNC | Same Sky / CUI **RCJ-014** RCA phono |
| J5 | `..._EdgePinOffset9.40mm` — bare pins | `..._EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm`, housing and mounting hardware |
| J2 | `BarrelJack_CUI_PJ-063AH_Horizontal` — right family, wrong part | Kycon **KLDX-0202-A** |

Three more improved along the way, because the same branch had their models too: **J3** (TE
640456-8 rather than a Molex KK-254), **SP1** (PUI AT-1224-TWT-R rather than a generic
buzzer) and **SW68** (Omron B3F-3152 rather than a PTS645).

Two things found while doing it are worth keeping:

- **U26's scale was wrong in the source branch.** The sibling-model approach was right and
  both ratios were right, but they were applied to the wrong axes — the STEP is authored
  Z-up (L × W × H) while the branch's note ordered the parts L × H × W. U26 rendered ~15.6 mm
  tall and 6.7 mm thick instead of 11.10 × 9.20. Corrected in `align_models_legacy.py`'s
  `SCALE_FIX`, so re-running reproduces the fix rather than the bug.
- **J5 does have mounting holes.** An earlier note here said the footprint had none. It has
  no *non-plated* holes, but its two 3.05 mm pads named `0` at ±12.494 are exactly the
  connector's plated mounting holes, so a housed model with mounting hardware is correct
  rather than a compromise.

## Optional: keycaps

The switches render as bare Cherry MX bodies — housing and stem, no caps. Caps would make
the render look like the finished machine, and this is the one remaining item that changes
how the board *reads* at a glance: 68 keycaps is most of the visible surface.

**No keycap models are installed anywhere** — not in KiCad's libraries, and not in the
perigoso keyswitch library, which ships only switch bodies, stabilizers and plate mounts. So
this one needs a model sourced or built first.

1. **Source or build a cap.** XDA or DSA profile, which is what skiselev recommends
   (README: *"XDA or DSA keycaps are recommended, as they have uniform shape regardless of
   the row"*). Uniform profile is a real simplification — one model serves every row.
2. **Five sizes**, matching the footprints: 1.00u (62 keys), 1.25u (SW65, SW66), 1.50u
   (SW61), 2.25u (SW11), 6.25u (SW64).
3. **Add as a second model per switch footprint**, raised to sit on the stem — the same
   composite technique the DIP sockets and stabilizers already use. Measure the Z from the
   Cherry MX drawing in `Documentation/MX Series.pdf`.
4. Run `tools/align_models.py` if the source footprint's origin differs, then
   `tools/apply_models.py`, then check the gate and look at the render.

## How to do any of this

```bash
# 1. put the sourced model where a fresh clone will find it
cp downloaded.step KiCad/Radio86RK.3dshapes/<Name>.step

# 2. add or edit its row in tools/models.tsv, referencing it via ${KIPRJMOD}
#    footprint <TAB> model <TAB> off_x <TAB> off_y <TAB> off_z <TAB> rot_z
#                              [<TAB> rot_x <TAB> rot_y <TAB> sx <TAB> sy <TAB> sz]

# 3. let a tool compute the transform rather than guessing it
python3 tools/kicad-verify.py run tools/align_models.py          # models that come from a KiCad footprint
python3 tools/kicad-verify.py run tools/align_models_legacy.py   # models from the migrate2kicad10 branch

# 4. apply, then verify
python3 tools/kicad-verify.py run tools/apply_models.py tools/models.tsv "$PCB" KiCad/Radio86RK.pretty
python3 tools/kicad-verify.py gerber          # must still PASS
python3 tools/kicad-verify.py models
python3 tools/render.py check          # and actually look at it
```

Record the model's origin and licence in `docs/3d-model-sources.md`.

**Look at the render.** Every 3D defect found in this project — the 90° IC rotation, the
half-pitch offsets, the five above, U26's swapped scale axes — was invisible to the
automated checks and obvious in a picture. Coverage proves a file resolves; it says nothing
about whether the thing looks right.

# Radio-86RK KiCad 10 Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Radio-86RK project to full KiCad 10 compatibility and a complete 3D render of every populated component, without moving a single copper feature.

**Architecture:** The board is the authoritative geometry source. All 191 footprint instances are extracted into a project-local library (`Radio86RK.pretty`), guaranteeing pad-for-pad identity by construction; 3D models are then attached to the 35 *unique* footprint definitions rather than to the 191 instances. Every change is gated by a gerber+drill diff against a baseline captured from `master` before any edit, and **no task changes copper** — that gate passes on every one of them.

**Tech Stack:** KiCad 10.0.4; `kicad-cli` for export/DRC/ERC/render; KiCad's bundled Python 3.9 with the `pcbnew` SWIG bindings for scripted board and library edits; plain POSIX shell for the verification harness; git for per-task commits.

## Global Constraints

Every task's requirements implicitly include this section.

- **KiCad version floor:** 10.0.4. All file formats end at board `version 20260206`.
- **Copper is frozen.** No pad, track, via, zone or drill hole may move. The gerber+drill gate is binary and must pass on **every** task, with no exceptions.
- **Schematic-side tasks never write to the board.** Do not run *Update PCB from Schematic* in any task except where this plan explicitly says to. It is the mechanism by which a harmless-looking schematic edit becomes board damage — see Finding 5, where it turned a field refresh into 170 shorts and 2118 unconnected items.
- **Never batch a GUI operation you have not measured.** Every KiCad GUI action in this plan is followed by a verification step comparing against the previous commit. Commit before starting one, so `git checkout -- KiCad/` is always the recovery.
- **From scratch only.** No commit, footprint, symbol, model, library table or configuration is taken from `migrate2kicad10`, `sw3-official-reroute-experiment`, or any other branch. Findings from earlier attempts may inform the work only as facts independently re-verified against `master`.
- **No absolute paths in committed files.** Every library and model URI uses `${KIPRJMOD}`, `${KICAD10_3DMODEL_DIR}` or `${KICAD10_3RD_PARTY}`.
- **Public reuse policy, by layer:** 3D models — aggressive, on every footprint. Symbols — where pin-compatible. Footprints — **none are replaced**; all 35 are vendored from the board. See Finding 1: the spec's Cherry MX exception rested on a false premise and is not taken.
- **Tolerance policy:** does not apply to footprints (the gerber diff is binary); does apply to 3D models (a fraction of a millimetre is invisible and carries no risk).
- **Work branch:** `kicad10-modernization`, based on `master` (`9476ec3`).
- **Every task ends with a commit.** No task leaves the tree dirty.

## Measured Environment (2026-09-04, verified)

| Thing | Value |
|---|---|
| `kicad-cli` | `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` (10.0.4) |
| KiCad Python | `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3` |
| `${KICAD10_3DMODEL_DIR}` | `/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels` |
| `${KICAD10_3RD_PARTY}` | `/Users/dveremeev/Documents/KiCad/10.0/3rdparty` |
| perigoso footprints | `${KICAD10_3RD_PARTY}/footprints/com_github_perigoso_keyswitch-kicad-library/Switch_Keyboard_Cherry_MX.pretty` |
| perigoso 3D | `${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/SW_Cherry_MX_PCB.stp` |
| Board format at start | `20211014` (KiCad 6), **CRLF** line endings |
| Schematic format at start | `20211123` (KiCad 6) |
| Footprint instances | 191 |
| **Unique footprint definitions** | **35** |

KiCad 10 ships `.step` files in `3dmodels`, **not** `.wrl`. Every model path below ends in `.step` (perigoso's is `.stp`).

## Execution Progress (updated 2026-09-05)

Parts of this plan have been executed and committed on `kicad10-modernization`. Numbers
below are **measured**, not predicted.

| Commit | What landed | Verified by |
|---|---|---|
| `2a7788a` | Schematics converted to KiCad 10 format (`20211123` → `20260306`) via the **GUI** | netlist identical (22971 lines); ERC 243 unchanged; DRC 91, unconnected 0, parity 0; gerbers byte-identical to v1.4 |
| `9d8e182` | Symbol definitions refreshed from libraries — **ERC 243 → 101**, all 142 `lib_symbol_mismatch` cleared | footprints 218/218 unchanged; netlist connectivity byte-identical (6790 lines); board untouched |
| `16a7755` | Q1/Q2 re-pointed `Device:Q_NPN_EBC` → `Transistor_BJT:Q_NPN_EBC` | netlist connectivity byte-identical; footprints intact; DRC 91, parity 0 |

**Current state:** board still at format `20211014` and byte-identical to v1.4. ERC 101 =
67 `footprint_link_issues` + 32 `same_local_global_label` + 2 `lib_symbol_mismatch`.
DRC 91, unconnected 0, parity 0.

That maps onto the tasks below as:

- **Task 2** — schematic half done in `2a7788a`. The **board** half is still outstanding.
- **Task 8** — the hard part is done (`9d8e182`, `16a7755`). What remains is the 32 label
  collisions, Q1/Q2's stale cache, and the sym-lib-table.
- **Task 3** — not executed here, but rehearsed end-to-end on a scratch copy: vendoring
  produced exactly DRC 22 (17 `silk_edge_clearance` + 5 `starved_thermal`), unconnected 0,
  parity 0, clearing all 67 `lib_footprint_issues` and both `lib_footprint_mismatch`.

Everything else is unexecuted.

---

## Findings That Amend the Spec

These were measured while writing this plan and change what the spec assumed. Each is
handled by the task named.

1. **The spec's Cherry MX exception rests on a false premise, and is not taken.**
   The spec adopts perigoso's `SW_Cherry_MX_PCB_*u` footprints on the stated grounds that
   doing so *"brings a 3D model"*. It does not need to. `models.tsv` attaches a model to any
   footprint **by name** — that is how the other 27 footprints in Tasks 4–6 get theirs — and
   the origins already coincide: both libraries put the switch's centre guide boss at (0, 0),
   so `SW_Cherry_MX_PCB.stp` lands correctly on the board's own geometry with no offset.

   Verified consequences of adopting perigoso anyway, none of which buy anything:

   - **Pads grow 2.286 → 2.5 mm** on all 67 Cherry switches. Cherry specifies *hole* sizes
     (⌀1.5 mm terminals, ⌀4.0 mm boss, ⌀1.7 mm locating pins), **not** land diameter, so
     neither figure is "the manufacturer's value" and the board's own is as correct as
     perigoso's. skiselev's numbers are Cherry's metric drawing on an imperial grid —
     1.4986 mm = 0.059″, 1.7018 mm = 0.067″, 3.9878 mm = 0.157″ — so the drill deltas are
     unit-conversion artefacts of ~0.1%, noise at fab tolerance.
   - **A schematic pin swap becomes mandatory** on all 67, because perigoso exchanges the two
     pad names against identical positions. This is the single riskiest operation in the
     plan: applied to the wrong subset it shorts the keyboard matrix.
   - **Two clearance violations appear.** Measured across all 134 switch pads, the +0.107 mm
     of radius drops SW4 pad 2 and SW61 pad 2 to 0.150 mm against the project's 0.2 mm rule,
     requiring a prototype measurement gate to dispose of.
   - **SW11 and SW64 lose their stabilizer holes.** The board's `CHERRY_PCB_225H` carries 4
     extra NPTH (±11.938, +8.255 @ ⌀3.9878; ±11.938, −6.985 @ ⌀3.048) and `_625H` carries 4
     (±50.038, −8.255 @ ⌀3.9878; ±50.038, +6.985 @ ⌀3.048). perigoso's wide-key footprints
     are byte-identical to its 1.00u apart from the keycap outline, because it keeps
     stabilizers as *separate* footprints. Its separate parts do not recover them either:
     `Stabilizer_Cherry_MX_2.00u` is 30 µm out and `_6.25u` is 38 µm out **and mirrored**.
     That is not a rounding error — per skiselev's README BOM, SW64's stabilizer is a hybrid
     of a **G99-0226** (MX 1x8) wire in **G99-0742** housings, so its 100.076 mm spacing
     matches no stock part.

   → **Task 7 keeps every switch footprint and attaches the models to it.** Copper, drill and
   silkscreen are untouched, there is no pin swap, no clearance question and no prototype
   gate, and the stabilizer holes are never at risk. What is forfeited is cosmetic:
   perigoso's tidier silkscreen and a real `F.CrtYd` courtyard where skiselev draws the
   outline on `Eco2.User`, which KiCad 10 ignores for `courtyard_overlap`. Adding courtyards
   to the vendored footprints remains available later as a non-copper change.
2. **A byte diff of gerbers does not work — the gate must canonicalise.** Verified by
   running `kicad-cli pcb upgrade` on this board: it re-emits identical geometry in a
   different order and renumbers aperture D-codes. 12 of 22 files change byte-wise, yet the
   drill file is byte-identical, the aperture sets match, and every copper file holds the
   same multiset of drawing commands. `F_Silkscreen` additionally drops 7 redundant
   aperture-select no-ops and swaps which diameters D12 and D13 name. A naive line *sort* is
   not safe either, because `F_Cu`, `B_Cu` and `F_Silkscreen` use G36/G37 region fills whose
   vertex order defines the polygon. → Task 1 Step 3 adds `tools/gerber_canon.py`, validated
   both ways: it passes the format upgrade and catches a 1 µm pad shift in 5 files.

3. **Use the GUI for the format conversion, not `kicad-cli sch upgrade` — they are not
   equivalent.** The CLI leaves the embedded `lib_symbols` cache stale. Measured pin
   definitions per sheet:

   | Sheet | original | GUI save | `kicad-cli sch upgrade` |
   |---|---:|---:|---:|
   | Radio-86RK | 450 | 560 | 560 |
   | CRT-Mem | 462 | **527** | 462 |
   | IO | 409 | **442** | 409 |
   | Keyboard | 360 | **372** | 360 |
   | Power | 306 | **366** | 306 |
   | **total** | 1987 | **2267** | 2097 |

   The GUI rebuilds the cache from the current libraries, adding 280 pin definitions; the
   CLI leaves four of five sheets untouched. Those stale definitions then manufacture **21
   spurious `different_unit_net` ERC violations** on the multi-unit 74xx logic (U16–U20).
   The GUI path produces none — ERC stayed at exactly 243 through conversion.

   *An earlier revision of this plan recorded those 21 violations as a real finding to be
   handled in Task 8. They were an artefact of the wrong tool.* → Task 2 uses the GUI.

4. **`Update Symbols from Library` is destructive by default, and its damage reaches the
   board.** Run with the *Update/reset Fields* options enabled and followed by *Update PCB
   from Schematic*, it reset 8 components to their symbols' default footprints and pushed
   that onto the board:

   | Ref | Board's footprint | Overwritten with |
   |---|---|---|
   | RN1 | `My_Components:Conn_SIL10` | `Resistor_THT:R_Array_SIP10` |
   | RN2–RN4 | `My_Components:Conn_SIL6` | `Resistor_THT:R_Array_SIP6` |
   | U23, U24 | `My_Components:IC_DIP8_300` | `Package_DIP:DIP-8_W7.62mm` |
   | U22 | `My_Components:IC_DIP16_300` | `Package_DIP:DIP-16_W7.62mm` |
   | U25 | `My_Components:IC_TO220-3_Vert` | `Package_TO_SOT_THT:TO-220-3_Vertical` |

   Result: DRC 91 → **669**, including **170 `shorting_items`**, 201 `solder_mask_bridge`
   and **2118 unconnected items**. The replacements have the same pin *pitch* but a
   different **origin**: RN2's pads shifted 6.35 mm, U25's a full 2.54 mm pitch, so nets
   bound to physically different holes while the tracks stayed put. Rolled back with
   `git checkout -- KiCad/`.

   KiCad warns about this itself — *"Warning: fields "Value" and "Footprints" will be
   therefore replaced."* → Task 8 unchecks every field option and never touches the board.
   This is the third instance of one pattern, after the Cherry MX pad-name swap and the
   missing stabilizer holes: a public footprint that is "the same part" and still moves
   nets relative to copper.

5. **`Device:Q_NPN_EBC` moved to `Transistor_BJT`.** Verified on 10.0.4: 0 hits in
   `Device.kicad_sym`, 1 in `Transistor_BJT.kicad_sym`. This is the whole of the 2
   `lib_symbol_issues`, on Q1 and Q2, and the only errors the symbol refresh reported. Pin
   numbering is unchanged (E=1, B=2, C=3), which is what `Transistor_TO92_EBC_254` depends
   on. → Fixed in `16a7755`.

6. **Shell portability: this environment is `zsh`, which does not word-split unquoted
   variables.** `cmd $NAMES` passes one argument, not many — silently, and the failure looks
   like the tool not finding anything. Every step that passes a generated list to a script
   must pipe through `xargs` rather than expand a bare variable.

7. **Gerbers embed net names.** `%TO.N,<netname>*%` appears 1155 times in `F_Cu` alone, so a
   net rename changes gerber bytes without moving copper. → Task 1 builds two gate modes.
8. **The project is in KiCad 6 format with CRLF endings.** The first save rewrites all
   173,936 lines. → Task 2 does that once, in isolation, gated.
9. **3D models attach to 35 footprint definitions, not 191 instances.** → Tasks 4–6 are 35
   assignments, not 191.
10. **U27 is `Transistor_TO92_EBC_254`, not a 3-pin regulator.** The spec's §3 text is wrong;
   its socket table (which excludes U25/U26/U27) is right. → Task 4 gives it a TO-92 model.
11. **F1 (a fuse) uses `Cap_Cer_508`.** Because models attach to footprints, F1 necessarily
   inherits the disc-capacitor model. Accepted per the 3D tolerance policy; recorded in
   `docs/3d-model-sources.md`.
12. **KiCad ships no RCA and no 8-pin DIN model.** → Task 6 sources or records fallbacks.

## File Structure

| Path | Responsibility |
|---|---|
| `tools/kicad-env.sh` | Single source of truth for tool paths. Sourced by every other script. |
| `tools/gerber_canon.py` | Canonicalise a gerber so reordering and D-code renumbering compare equal. |
| `tools/gerber-gate.sh` | Export gerbers+drill, canonicalise, diff vs baseline. Two modes. |
| `tools/netlist-gate.sh` | Export the netlist, diff vs baseline. Proves no pin was renumbered. |
| `tools/rules-report.sh` | Run ERC + DRC, print violation counts by type. |
| `tools/render.sh` | Render the board to PNG for the visual record. |
| `tools/vendor_footprints.py` | Extract the 35 unique footprints from the board into `Radio86RK.pretty`. |
| `tools/apply_models.py` | Apply `models.tsv` to both the library and the board instances. |
| `tools/models.tsv` | Data: footprint → 3D model → Z offset → Z rotation. Grows across Tasks 4–7. |
| `verify/baseline/` | Frozen normalized gerbers+drill from `master`. Committed. |
| `verify/renders/` | Per-task PNG renders. Committed. |
| `KiCad/Radio86RK.pretty/` | Tier 2: the 35 vendored footprints. |
| `KiCad/Radio86RK.kicad_sym` | Tier 2: the `my_components` symbols, vendored so a fresh clone works. |
| `KiCad/Radio86RK.3dshapes/` | Externally sourced models (RCA, DIN-8, DC-DC) if obtained. |
| `KiCad/fp-lib-table`, `KiCad/sym-lib-table` | Project-local library registration. |
| `docs/3d-model-sources.md` | Why each model was chosen; every substitution and fallback. |
| `docs/drc-exclusions.md` | Written reason for each retained DRC violation. |
| `docs/erc-exclusions.md` | Written reason for each retained ERC violation (the RS-232 defect). |
| `docs/modernization-summary.md` | Before/after outcome table and how to re-verify it. |

---

### Task 1: Verification harness and frozen baseline

Nothing may be edited until the gate that protects the board exists and is proven to work
on an unchanged board. This task creates it and captures the reference.

**Files:**
- Create: `tools/kicad-env.sh`, `tools/gerber-gate.sh`, `tools/rules-report.sh`, `tools/render.sh`
- Create: `verify/baseline/` (generated content, committed)
- Create: `.gitignore` entries for scratch output

**Interfaces:**
- Produces: `tools/gerber-gate.sh [--strict|--geometry]` — exit 0 on match, 1 on difference,
  prints a unified diff of the offending files. `tools/rules-report.sh` — prints
  `ERC <n>` / `DRC <n>` plus a per-type breakdown. Both are consumed by every later task.

- [ ] **Step 1: Create the branch**

```bash
cd /Users/dveremeev/projects/radio-86rk
git checkout -b kicad10-modernization master
```

- [ ] **Step 2: Write `tools/kicad-env.sh`**

```bash
#!/usr/bin/env bash
# Single source of truth for KiCad tool locations. Source, don't execute.
KICAD_APP="/Applications/KiCad/KiCad.app/Contents"
export KICAD_CLI="$KICAD_APP/MacOS/kicad-cli"
export KICAD_PY="$KICAD_APP/Frameworks/Python.framework/Versions/3.9/bin/python3"
export KICAD_3DMODEL_DIR="$KICAD_APP/SharedSupport/3dmodels"
export KICAD_3RD_PARTY="$HOME/Documents/KiCad/10.0/3rdparty"
export REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PCB="$REPO_ROOT/KiCad/Radio-86RK.kicad_pcb"
export SCH="$REPO_ROOT/KiCad/Radio-86RK.kicad_sch"
export BUILD="$REPO_ROOT/.build"

for v in KICAD_CLI KICAD_PY KICAD_3DMODEL_DIR KICAD_3RD_PARTY PCB SCH; do
  [ -e "${!v}" ] || { echo "kicad-env: missing $v = ${!v}" >&2; return 1 2>/dev/null || exit 1; }
done
```

- [ ] **Step 3: Write `tools/gerber_canon.py`**

**A byte diff of gerbers does not work, and this was verified the hard way.** Running
`kicad-cli pcb upgrade` on this board re-emits identical geometry in a *different order*,
and renumbers aperture D-codes: after the format upgrade, 12 of 22 files differ byte-wise
while the drill file is byte-identical, apertures are the same set, and every copper file
holds the same multiset of drawing commands. A naive byte gate would fail Task 2 and every
task after it.

A naive line *sort* is not safe either: `F_Cu`, `B_Cu` and `F_Silkscreen` all use G36/G37
region fills, whose vertex order determines the polygon.

So the gate canonicalises first — resolving each D-code to the aperture *shape* it names,
grouping commands into atomic drawing units, and sorting the units:

```python
"""Canonicalise a gerber file so reordering and aperture renumbering compare equal,
while any change to real geometry compares different.

Canonical form: the file is split into atomic drawing units --
  * a G36...G37 region block, kept verbatim and in order
  * a D02 move plus the D01/D03 operations that follow it
  * a bare D03 flash
each prefixed by the resolved aperture definition (not its D-code) and the current
interpolation mode. Units are then sorted, so order between units is irrelevant while
order within a unit is preserved.
"""
import re, sys

APERTURE_DEF = re.compile(r"^%ADD(\d+)([^*]*)\*%")
APERTURE_SEL = re.compile(r"^D(\d+)\*$")
GMODE        = re.compile(r"^(G0[123])\*?$")
OPLINE       = re.compile(r"D0([123])\*$")

def canon(path):
    apertures, units = {}, []
    cur_ap, cur_g, unit = "none", "G01", None
    in_region, region = False, []

    for raw in open(path, errors="replace"):
        line = raw.rstrip("\n").rstrip("\r")
        if not line:
            continue

        m = APERTURE_DEF.match(line)
        if m:                                   # remember the shape, discard the D-code
            apertures[m.group(1)] = m.group(2)
            continue

        if line.startswith("G36"):
            if unit:
                units.append(unit); unit = None
            in_region, region = True, []
            continue
        if line.startswith("G37"):
            units.append("REGION|%s|%s" % (cur_ap, "|".join(region)))
            in_region = False
            continue
        if in_region:
            region.append(line)
            continue

        m = APERTURE_SEL.match(line)
        if m:                                   # aperture select: resolve to its shape
            if unit:
                units.append(unit); unit = None
            cur_ap = apertures.get(m.group(1), "D" + m.group(1))
            continue

        m = GMODE.match(line)
        if m:
            cur_g = m.group(1)
            continue

        m = OPLINE.search(line)
        if m:
            op = m.group(1)
            if op == "2":                       # move: starts a new unit
                if unit:
                    units.append(unit)
                unit = "DRAW|%s|%s|%s" % (cur_ap, cur_g, line)
            elif op == "1":                     # draw: extends the current unit
                if unit is None:
                    unit = "DRAW|%s|%s|" % (cur_ap, cur_g)
                unit += "||" + line
            else:                               # flash: atomic
                if unit:
                    units.append(unit); unit = None
                units.append("FLASH|%s|%s" % (cur_ap, line))
            continue
        # everything else (format specs, attributes, M02) is metadata, not geometry

    if unit:
        units.append(unit)
    return sorted(units)

if __name__ == "__main__":
    for u in canon(sys.argv[1]):
        print(u)
```

This exact script was validated both ways on this board: it reports the format upgrade as
unchanged, and it detects a 1 µm pad displacement in 5 files. Step 8 re-runs both checks.

- [ ] **Step 4: Write `tools/gerber-gate.sh`**

Drill and job files are compared directly (the drill file is byte-stable). Gerbers go
through the canonicaliser. `--strict` additionally keeps the X2 net/component attributes so
a net rename is visible; `--geometry` drops them, for tasks that legitimately rename nets.

```bash
#!/usr/bin/env bash
# Export gerbers+drill and diff against verify/baseline.
#   --strict    (default) byte-identical after timestamp stripping
#   --geometry  also strip X2 net/component attributes (%TO.*, %TA.*, G04 #@!)
#   --capture   write the baseline instead of comparing
set -euo pipefail
source "$(dirname "$0")/kicad-env.sh"

MODE="strict"; CAPTURE=0
for a in "$@"; do
  case "$a" in
    --strict)   MODE="strict" ;;
    --geometry) MODE="geometry" ;;
    --capture)  CAPTURE=1 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

RAW="$BUILD/gerber-raw"; NORM="$BUILD/gerber-$MODE"
BASE="$REPO_ROOT/verify/baseline/$MODE"
rm -rf "$RAW" "$NORM"; mkdir -p "$RAW" "$NORM"

"$KICAD_CLI" pcb export gerbers --output "$RAW" "$PCB" >/dev/null
"$KICAD_CLI" pcb export drill   --output "$RAW" "$PCB" >/dev/null

# Timestamp-bearing lines, all four forms observed in KiCad 10.0.4 output.
STAMP='CreationDate|Created by KiCad|DRILL file KiCad'
for f in "$RAW"/*; do
  out="$NORM/$(basename "$f")"
  case "$(basename "$f")" in
    *.drl|*.gbrjob)
      # Drill and job files are already stable and order-independent.
      grep -vE "$STAMP" "$f" > "$out" ;;
    *)
      # Gerbers go through the canonicaliser: KiCad re-emits the same geometry in a
      # different order and with D-codes renumbered, so a byte diff is meaningless.
      "$KICAD_PY" "$(dirname "$0")/gerber_canon.py" "$f" > "$out"
      if [ "$MODE" = "strict" ]; then
        # In strict mode also keep the X2 net/component attributes, so a net rename
        # is visible. --geometry drops them.
        grep -E '^%T[OA]\.' "$f" | sort >> "$out"
      fi ;;
  esac
done

if [ "$CAPTURE" = 1 ]; then
  rm -rf "$BASE"; mkdir -p "$(dirname "$BASE")"; cp -R "$NORM" "$BASE"
  echo "gerber-gate: captured $MODE baseline ($(ls "$BASE" | wc -l | tr -d ' ') files)"
  exit 0
fi

[ -d "$BASE" ] || { echo "gerber-gate: no $MODE baseline; run --capture" >&2; exit 2; }
if diff -r -q "$BASE" "$NORM" >/dev/null; then
  echo "gerber-gate($MODE): PASS - board geometry unchanged"
else
  echo "gerber-gate($MODE): FAIL"; diff -r -u "$BASE" "$NORM" | head -80; exit 1
fi
```

- [ ] **Step 5: Write `tools/rules-report.sh`**

```bash
#!/usr/bin/env bash
# Print ERC and DRC violation counts, total and by type.
set -euo pipefail
source "$(dirname "$0")/kicad-env.sh"
mkdir -p "$BUILD"

"$KICAD_CLI" sch erc --format json --output "$BUILD/erc.json" \
    --severity-all --exit-code-violations "$SCH" >/dev/null 2>&1 || true
"$KICAD_CLI" pcb drc --format json --output "$BUILD/drc.json" \
    --severity-all --exit-code-violations "$PCB" >/dev/null 2>&1 || true

"$KICAD_PY" - "$BUILD/erc.json" "$BUILD/drc.json" <<'PY'
import json, sys, collections
for label, path in (("ERC", sys.argv[1]), ("DRC", sys.argv[2])):
    d = json.load(open(path))
    items = [v for s in d.get("sheets", d.get("violations") and [d] or [])
             for v in s.get("violations", [])] if "sheets" in d else d.get("violations", [])
    by = collections.Counter(v["type"] for v in items)
    sev = collections.Counter(v.get("severity", "?") for v in items)
    print(f"{label} {len(items)}  errors={sev.get('error',0)} warnings={sev.get('warning',0)}")
    for t, n in by.most_common():
        print(f"     {n:4d}  {t}")
    if label == "DRC":
        print(f"     unconnected={len(d.get('unconnected_items', []))}"
              f"  parity={len(d.get('schematic_parity', []))}")
PY
```

- [ ] **Step 6: Write `tools/render.sh`**

```bash
#!/usr/bin/env bash
# Render the board to PNG. Usage: tools/render.sh <tag>
set -euo pipefail
source "$(dirname "$0")/kicad-env.sh"
TAG="${1:?usage: render.sh <tag>}"
OUT="$REPO_ROOT/verify/renders"; mkdir -p "$OUT"
"$KICAD_CLI" pcb render --output "$OUT/$TAG-top.png" \
    --width 2400 --height 1600 --quality high \
    --rotate '-30,0,25' --perspective --floor "$PCB"
echo "rendered $OUT/$TAG-top.png"
```

- [ ] **Step 7: Make the scripts executable and ignore build output**

```bash
cd /Users/dveremeev/projects/radio-86rk
chmod +x tools/*.sh
printf '.build/\n.DS_Store\nKiCad/.history/\nKiCad/*.kicad_prl\nKiCad/*.lck\n' >> .gitignore
```

- [ ] **Step 8: Prove the gate works — capture the baseline, then run it unchanged**

This is the failing-test-first moment: a gate that cannot pass on an untouched board is
worthless, and a gate that cannot fail is equally worthless.

```bash
tools/gerber-gate.sh --strict   --capture
tools/gerber-gate.sh --geometry --capture
tools/gerber-gate.sh --strict
tools/gerber-gate.sh --geometry
```

Expected: two `captured` lines, then two `PASS` lines.

- [ ] **Step 9: Prove the gate can fail**

```bash
# Perturb one pad by 1 micron in a scratch copy, confirm the gate catches it.
cp KiCad/Radio-86RK.kicad_pcb /tmp/pcb-backup.kicad_pcb
perl -0pi -e 's/\(at 247\.65 8\.89\)/(at 247.651 8.89)/' KiCad/Radio-86RK.kicad_pcb
tools/gerber-gate.sh --strict || echo "GATE CORRECTLY DETECTED THE CHANGE"
cp /tmp/pcb-backup.kicad_pcb KiCad/Radio-86RK.kicad_pcb
tools/gerber-gate.sh --strict
```

Expected: `FAIL` + a diff + the confirmation line, then `PASS` after restore.

- [ ] **Step 10: Record the starting rule counts**

```bash
tools/rules-report.sh | tee verify/rules-00-baseline.txt
```

Expected, per the spec's measured starting state: `ERC 243  errors=0`,
`DRC 91  errors=0`, `unconnected=0  parity=0`.
If the numbers differ, stop and reconcile before continuing — the whole plan is calibrated
against them.

These numbers depend on `KiCad/sym-lib-table` and `KiCad/fp-lib-table`, which exist in the
working tree as untracked files written on 2026-09-04. Step 10 commits them as-is so the
baseline is reproducible from git; Tasks 3 and 7 then rewrite both to point at vendored
libraries.

- [ ] **Step 11: Commit**

```bash
git add tools .gitignore verify KiCad/sym-lib-table KiCad/fp-lib-table
git commit -m "Add gerber/DRC verification harness and freeze the v1.4 baseline

The gerber gate is proven both ways: it passes on the untouched board and
fails on a 1um pad displacement. Two modes, because KiCad's X2 gerbers embed
net names (1155 %TO.N records in F_Cu alone) - --strict for tasks that must
change nothing, --geometry for tasks that legitimately rename nets.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 2: Upgrade the project files to KiCad 10 format

> **STATUS: schematic half complete** — done in the GUI and committed as `2a7788a`
> (`20211123` → `20260306`). The **board** half is outstanding; it is still at
> `20211014`. Steps 1–7 are marked done and record what was measured. Resume at Step 8.

The board is KiCad 6 format with CRLF endings, and the schematics were. Any later edit
would be against a legacy format that KiCad rewrites wholesale on first save, burying real
changes in a reformat. Do the reformat once, alone, and prove it moved nothing.

**Use the GUI, not `kicad-cli`.** Per Finding 3 these are not equivalent: `kicad-cli sch
upgrade` leaves the embedded `lib_symbols` cache stale on four of five sheets, which then
manufactures 21 spurious `different_unit_net` ERC violations. The GUI rebuilds the cache
(1987 → 2267 pin definitions) and produces none.

**Files:**
- Modify: all five `KiCad/*.kicad_sch` *(done, `2a7788a`)*, `KiCad/Radio-86RK.kicad_pro` *(done)*
- Modify: `KiCad/Radio-86RK.kicad_pcb` *(outstanding)*

**Interfaces:**
- Consumes: `tools/gerber-gate.sh`, `tools/rules-report.sh`, `tools/netlist-gate.sh` from Task 1.

- [x] **Step 1: Record the pre-upgrade format versions**

Measured: board `(kicad_pcb (version 20211014) (generator pcbnew)`, schematics
`(kicad_sch (version 20211123) (generator eeschema)`, and 173,936 CRLF lines in the board.

- [x] **Step 2: Confirm the gate passes before touching anything**

- [x] **Step 3: Convert the schematics in the GUI**

Open the project, open **Schematic Editor**, then **File → Save** (KiCad prompts to
convert). Do **not** use `kicad-cli sch upgrade`.

- [x] **Step 4: Verify the conversion is faithful, not just successful**

Measured on `2a7788a` — this is the step that distinguishes the GUI from the CLI:

```bash
for f in Radio-86RK Radio-86RK-CRT-Mem Radio-86RK-IO Radio-86RK-Keyboard Radio-86RK-Power; do
  printf "%-24s orig %4d  now %4d\n" "$f" \
    "$(git show HEAD~1:KiCad/$f.kicad_sch | grep -c '(pin ')" \
    "$(grep -c '(pin ' KiCad/$f.kicad_sch)"
done
```

Expected: every sheet's pin count **rises or stays equal**, totalling 1987 → 2267. A sheet
whose count is unchanged means the cache was not rebuilt — you used the CLI.

- [x] **Step 5: Netlist gate**

Measured: 22971 lines, identical apart from the source path and one pair of UUIDs swapping
order within a single net's `tstamps`. No connectivity changed.

- [x] **Step 6: Rule counts**

Measured: **ERC 243, unchanged**, same breakdown (142 `lib_symbol_mismatch`,
67 `footprint_link_issues`, 32 `same_local_global_label`, 2 `lib_symbol_issues`).
DRC 91, unconnected 0, parity 0. No `different_unit_net` — see Finding 3.

- [x] **Step 7: Commit the schematic conversion** — `2a7788a`.

---

**Resume here.** Everything below is outstanding.

- [ ] **Step 8: Confirm the board is still pristine before converting it**

```bash
tools/gerber-gate.sh --strict
head -1 KiCad/Radio-86RK.kicad_pcb | cut -c1-45
git status --short KiCad/Radio-86RK.kicad_pcb || echo "board unmodified"
```

Expected: `PASS`, `(kicad_pcb (version 20211014)`, and no modification. If the board is
already dirty, stop and find out why before converting.

- [ ] **Step 9: Convert the board in the GUI**

Open the **PCB Editor** and **File → Save**. Close KiCad afterwards — later steps read the
files and must not race a live session.

```bash
ls KiCad/*.lck 2>/dev/null && echo "GUI STILL OPEN" || echo "closed"
head -2 KiCad/Radio-86RK.kicad_pcb | tr -d '\n\t' | cut -c1-45
grep -c $'\r' KiCad/Radio-86RK.kicad_pcb || echo "CRLF gone"
```

Expected: `closed`, `version 20260206` (or later), zero CRLF lines.

- [ ] **Step 10: Run the gate — the whole point of the task**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`. **This is where `gerber_canon.py` earns its place.** `kicad-cli pcb
upgrade` was measured to rewrite the gerbers substantially — 12 of 22 files change
byte-wise, `F_Silkscreen` drops 7 redundant aperture-select no-ops and swaps which
diameters D12 and D13 name — while moving no geometry. Whether the GUI save reorders the
same way is **not yet measured**; the canonical gate is correct either way.

If it fails, `git checkout -- KiCad/Radio-86RK.kicad_pcb` and stop. A reformat that moves a
coordinate is a KiCad bug or a wrong command.

- [ ] **Step 11: Rule counts and netlist**

```bash
tools/netlist-gate.sh
tools/rules-report.sh | tee verify/rules-02-board-format.txt
```

Expected: netlist `PASS`; DRC unchanged from the run before the save (91 at time of
writing, or 22 if Task 3 has already run); unconnected 0; parity 0.

- [ ] **Step 12: Commit the board conversion**

```bash
git add KiCad/Radio-86RK.kicad_pcb verify
git commit -m "Convert the board to KiCad 10 format via the GUI

A pure reformat: every line of the board file changes and the canonical
gerber gate passes, so no copper moved. Isolated in its own commit so later
diffs stay readable.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 3: Vendor the 35 footprints and make the project self-contained

> **STATUS: rehearsed end-to-end on a scratch copy, not yet committed.** Every step below
> was executed against a throwaway copy of this board and produced exactly the numbers
> stated — DRC 22, unconnected 0, parity 0, all 67 `lib_footprint_issues` and both
> `lib_footprint_mismatch` cleared. The predictions here are measurements.

`Cherry_MX` is lost and `My_Components` currently resolves only through a sibling clone,
so a fresh clone of this repo cannot open the board. Extract all 35 unique footprints from
the board itself — identity is guaranteed by construction — and register them project-locally.

**The board and schematics are not edited in this task.** The vendored library is registered
under the *existing* nicknames `My_Components` and `Cherry_MX`, so all 191 `lib_id`s and
every schematic `Footprint` field keep resolving unchanged. This is the lowest-risk way to
reach a standalone project: no relink, no parity risk, and the gerber gate cannot even be
threatened. Task 9 relinks the switches, and only the switches.

`Symbol:KiCad-Logo2_6mm_SilkScreen` (LOGO1) stays pointed at KiCad's stock `Symbol` library
— that is legitimate public reuse of a library guaranteed to ship with KiCad, not an
external dependency. A vendored copy is written anyway as a belt-and-braces fallback.

**Files:**
- Create: `tools/vendor_footprints.py`
- Create: `KiCad/Radio86RK.pretty/` (35 `.kicad_mod` files)
- Modify: `KiCad/fp-lib-table`

**Interfaces:**
- Consumes: `tools/kicad-env.sh`, `tools/gerber-gate.sh`, `tools/rules-report.sh`.
- Produces: `KiCad/Radio86RK.pretty/<name>.kicad_mod` for all 35 names; consumed by
  `tools/apply_models.py` in Tasks 4–6 and by Task 9.

- [ ] **Step 1: Write `tools/vendor_footprints.py`**

The `Duplicate()` return needs a cast, so mutate the loaded board in memory instead — it is
a throwaway copy and is never saved.

```python
"""Extract every unique footprint from the board into a project-local .pretty library.

Geometry identity is guaranteed by construction: these ARE the board's footprints, with
only instance data (placement, rotation, reference, net assignments) neutralised.
"""
import os, sys, pcbnew

BOARD = sys.argv[1]
LIB   = sys.argv[2]

os.makedirs(LIB, exist_ok=True)
board = pcbnew.LoadBoard(BOARD)
io    = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

seen = set()
for fp in board.GetFootprints():
    name = str(fp.GetFPID().GetLibItemName())
    if name in seen:
        continue
    seen.add(name)
    # Neutralise instance data so this is a library part, not a placement.
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    fp.SetOrientationDegrees(0)
    fp.SetReference("REF**")
    fp.SetValue(name)
    for pad in fp.Pads():
        pad.SetNetCode(0)
    io.FootprintSave(LIB, fp)

print("vendored %d unique footprints -> %s" % (len(seen), LIB))
```

- [ ] **Step 2: Verify the expectation before running — 35 unique, 191 instances**

```bash
grep -c '^	(footprint "' KiCad/Radio-86RK.kicad_pcb
grep -o '^	(footprint "[^"]*"' KiCad/Radio-86RK.kicad_pcb | sort -u | wc -l
```

Expected: `191` then `35`. (The leading tab is the KiCad 10 indent produced by Task 2.)

- [ ] **Step 3: Extract**

```bash
source tools/kicad-env.sh
"$KICAD_PY" tools/vendor_footprints.py "$PCB" "$REPO_ROOT/KiCad/Radio86RK.pretty"
ls KiCad/Radio86RK.pretty | wc -l
```

Expected: `vendored 35 unique footprints` and `35`.
A harmless `create wxApp before calling this` assert on stderr is normal for headless `pcbnew`.

- [ ] **Step 4: Verify the stabilizer holes survived — the highest-value single check**

If the 2.25u and 6.25u stabilizer holes were lost here, Task 9 would silently ship a board
with 8 missing drills.

```bash
grep -c '(pad ' KiCad/Radio86RK.pretty/CHERRY_PCB_225H.kicad_mod
grep -c '(pad ' KiCad/Radio86RK.pretty/CHERRY_PCB_625H.kicad_mod
grep -c '(pad ' KiCad/Radio86RK.pretty/CHERRY_PCB_100H.kicad_mod
grep -E '11\.938|50\.038' KiCad/Radio86RK.pretty/CHERRY_PCB_225H.kicad_mod KiCad/Radio86RK.pretty/CHERRY_PCB_625H.kicad_mod | wc -l
```

Expected: `9`, `9`, `5`, and `8` (four stabilizer pads in each of the two files).

- [ ] **Step 5: Verify no instance data leaked into the library**

```bash
grep -l -E 'Sheetfile|Sheetname|\(path |\(net ' KiCad/Radio86RK.pretty/*.kicad_mod | wc -l
```

Expected: `0`.

- [ ] **Step 6: Write `KiCad/fp-lib-table`**

Two nicknames, one directory. This is what removes the sibling-clone dependency without
touching the board.

```
(fp_lib_table
	(version 7)
	(lib (name "My_Components")(type "KiCad")(uri "${KIPRJMOD}/Radio86RK.pretty")(options "")(descr "Vendored from Radio-86RK.kicad_pcb - geometry identical to v1.4 by construction"))
	(lib (name "Cherry_MX")(type "KiCad")(uri "${KIPRJMOD}/Radio86RK.pretty")(options "")(descr "Vendored from Radio-86RK.kicad_pcb - original Cherry_MX library is lost upstream"))
)
```

Two nicknames, one directory. They keep the board's existing 191 `lib_id`s resolving
untouched, which is what makes this task a pure addition: no `lib_id` is rewritten anywhere
in the plan, so no footprint is ever replaced and the strict gate cannot be threatened.

- [ ] **Step 7: Run the gate — the board was not edited, so this must pass trivially**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`.

- [ ] **Step 8: Confirm the rule counts moved as predicted**

```bash
tools/rules-report.sh | tee verify/rules-03-vendored.txt
```

Expected — **this whole step was executed end-to-end on a scratch copy of this board and
produced exactly these numbers:**

`DRC 22`, being 17 `silk_edge_clearance` + 5 `starved_thermal`. All 67
`lib_footprint_issues` and both `lib_footprint_mismatch` clear, which confirms the
extraction reproduces the board's geometry closely enough for KiCad's own library
comparison. `unconnected_items` and `schematic_parity` are both empty.

**ERC drops by exactly 67** — the `footprint_link_issues` clear, because the schematic's
footprint fields now resolve. From the current state of 101 that gives **ERC 34**
(32 `same_local_global_label` + 2 `lib_symbol_mismatch`); once Task 8's remaining steps
land it gives **0**. Run this task before or after those — it is independent of them.

If `lib_footprint_mismatch` is **non-zero**, the extraction altered something. Diff the
offending library footprint against its board instance before proceeding.

- [ ] **Step 9: Commit**

```bash
git add KiCad/Radio86RK.pretty KiCad/fp-lib-table tools/vendor_footprints.py verify
git commit -m "Vendor all 35 footprints from the board into Radio86RK.pretty

The board is the authoritative geometry source, so extracting from it makes
library-vs-board identity true by construction rather than by inspection.
Registered under the existing My_Components and Cherry_MX nicknames, so no
lib_id or schematic Footprint field changes and the board is untouched.

DRC 91 -> 22 (all 67 lib_footprint_issues and both lib_footprint_mismatch
resolved); ERC 243 -> 176. The project now opens from a fresh clone.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 4: 3D models for passives (76 components, 8 footprints)

All 19 legacy model paths are KiCad 4-era (`dil/`, `discret/`, `pin_array/`) and resolve to
nothing. Because models attach to footprint *definitions*, 76 components are covered by 8
assignments.

**Files:**
- Create: `tools/apply_models.py`, `tools/models.tsv`, `docs/3d-model-sources.md`
- Modify: `KiCad/Radio86RK.pretty/*.kicad_mod` (8 files), `KiCad/Radio-86RK.kicad_pcb`

**Interfaces:**
- Consumes: `KiCad/Radio86RK.pretty/` from Task 3.
- Produces: `tools/apply_models.py <models.tsv> <board> <lib>` — applies every row to both
  the vendored library and the matching board instances, then saves the board.
  Re-runnable and idempotent: it clears a footprint's model list before adding. Tasks 5, 6
  and 9 append rows to the same `models.tsv` and re-run the same script.

- [ ] **Step 1: Write `tools/apply_models.py`**

```python
"""Apply models.tsv to the vendored library AND to the board's footprint instances.

TSV columns: footprint_name <TAB> model_path <TAB> z_offset_mm [<TAB> z_rotation_deg]
The 4th column is optional and defaults to 0; Task 9 needs it because perigoso's 6.25u
stabilizer model is mirrored in Y relative to this board's stabilizer holes.
Multiple rows per footprint are applied in order (used for socket+chip and
switch+stabilizer composites).
A model_path of "-" means "deliberately no model"; the row documents the decision.
"""
import sys, collections, pcbnew

TSV   = sys.argv[1]
BOARD = sys.argv[2]
LIB   = sys.argv[3]

wanted = collections.OrderedDict()
for raw in open(TSV):
    line = raw.split("#", 1)[0].strip()
    if not line:
        continue
    cols = [c.strip() for c in line.split("\t") if c.strip() != ""]
    name, path, z = cols[0], cols[1], cols[2]
    rot = float(cols[3]) if len(cols) > 3 else 0.0
    wanted.setdefault(name, [])
    if path != "-":
        wanted[name].append((path, float(z), rot))

def set_models(fp, entries):
    fp.Models().clear()
    for path, z, rot in entries:
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        m.m_Offset   = pcbnew.VECTOR3D(0, 0, z)
        m.m_Scale    = pcbnew.VECTOR3D(1, 1, 1)
        m.m_Rotation = pcbnew.VECTOR3D(0, 0, rot)
        m.m_Show     = True
        fp.Models().push_back(m)

io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

# 1. the library (footprints living in an external library are board-only)
external = []
for name, entries in wanted.items():
    fp = pcbnew.FootprintLoad(LIB, name)
    if fp is None:
        external.append(name)
        continue
    set_models(fp, entries)
    io.FootprintSave(LIB, fp)
if external:
    print("board-only (not in %s): %s" % (LIB, ", ".join(external)))

# 2. the board instances
board = pcbnew.LoadBoard(BOARD)
touched = collections.Counter()
for fp in board.GetFootprints():
    name = str(fp.GetFPID().GetLibItemName())
    if name in wanted:
        set_models(fp, wanted[name])
        touched[name] += 1
pcbnew.SaveBoard(BOARD, board)

total = sum(touched.values())
for name in wanted:
    print("  %3d x %s  (%d model(s))" % (touched[name], name, len(wanted[name])))
print("applied to %d footprints / %d instances" % (len(wanted), total))

# A name that is neither in the library nor on the board is a typo, not a decision.
ghosts = [n for n in wanted if touched[n] == 0 and n in external]
if ghosts:
    sys.exit("ERROR: named in models.tsv but found nowhere: %s" % ", ".join(ghosts))
```

- [ ] **Step 2: Write `tools/models.tsv` (passives)**

Columns are tab-separated. `${KICAD10_3DMODEL_DIR}` keeps the paths portable.

```
# footprint	model	z_offset_mm	[z_rotation_deg, optional]
Res_762	${KICAD10_3DMODEL_DIR}/Resistor_THT.3dshapes/R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.step	0
Cap_Cer_508	${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/C_Disc_D5.0mm_W2.5mm_P5.00mm.step	0
Cap_Elec_Radial_6.3mm	${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D6.3mm_P2.50mm.step	0
Diode_762	${KICAD10_3DMODEL_DIR}/Diode_THT.3dshapes/D_DO-35_SOD27_P7.62mm_Horizontal.step	0
LED_3mm	${KICAD10_3DMODEL_DIR}/LED_THT.3dshapes/LED_D3.0mm.step	0
Crystal_HC-49U_Vert	${KICAD10_3DMODEL_DIR}/Crystal.3dshapes/Crystal_HC49-U_Vertical.step	0
Transistor_TO92_EBC_254	${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-92_Inline.step	0
IC_TO220-3_Vert	${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-220-3_Vertical.step	0
```

- [ ] **Step 3: Verify every model file exists before applying**

A path typo produces a silently invisible component, so check first.

```bash
source tools/kicad-env.sh
awk -F'\t' '!/^#/ && NF>=2 {print $2}' tools/models.tsv \
  | sed "s|\${KICAD10_3DMODEL_DIR}|$KICAD_3DMODEL_DIR|" \
  | while read -r m; do [ -f "$m" ] || echo "MISSING: $m"; done
echo "check complete"
```

Expected: `check complete` with no `MISSING` lines.

- [ ] **Step 4: Confirm the board currently renders nothing**

```bash
tools/render.sh 03-no-models
```

Expected: a bare green board with pads and silkscreen, zero component bodies.

- [ ] **Step 5: Apply**

```bash
"$KICAD_PY" tools/apply_models.py tools/models.tsv "$PCB" "$REPO_ROOT/KiCad/Radio86RK.pretty"
```

Expected: a per-footprint count table summing to `applied to 8 footprints / 76 instances`.

- [ ] **Step 6: Run the gate — models must not move copper**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`. `apply_models.py` rewrites the whole board file via `SaveBoard`, so this
also confirms the round-trip through `pcbnew` is lossless.

- [ ] **Step 7: Render and eyeball**

```bash
tools/render.sh 04-passives
```

Expected: resistors, disc and electrolytic capacitors, diodes, LEDs, the crystal and the
TO-92/TO-220 packages all visible, seated on the board, none floating or sunk. ICs,
connectors and switches are still bare.

- [ ] **Step 8: Start `docs/3d-model-sources.md`**

```markdown
# 3D model sources and substitutions

Per the design spec's equivalence rubric, the 3D layer is appearance-only: it touches no
copper, so visually equivalent public models are preferred over exact ones. Every
substitution is recorded here.

## Passives

| Footprint | Refs | Model | Note |
|---|---|---|---|
| `Res_762` | R1-R15 | `Resistor_THT/R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal` | exact lead pitch |
| `Cap_Cer_508` | C1-C32, F1 | `Capacitor_THT/C_Disc_D5.0mm_W2.5mm_P5.00mm` | see F1 note |
| `Cap_Elec_Radial_6.3mm` | C33-C38 | `Capacitor_THT/CP_Radial_D6.3mm_P2.50mm` | exact |
| `Diode_762` | D1-D9 | `Diode_THT/D_DO-35_SOD27_P7.62mm_Horizontal` | exact |
| `LED_3mm` | D10, D11 | `LED_THT/LED_D3.0mm` | exact |
| `Crystal_HC-49U_Vert` | Y1 | `Crystal/Crystal_HC49-U_Vertical` | exact |
| `Transistor_TO92_EBC_254` | Q1, Q2, U27 | `Package_TO_SOT_THT/TO-92_Inline` | generic TO-92 for Soviet KT-series |
| `IC_TO220-3_Vert` | U25 | `Package_TO_SOT_THT/TO-220-3_Vertical` | exact package |

**F1 renders as a disc capacitor.** F1 is a fuse but is placed on the `Cap_Cer_508`
footprint, and 3D models attach to footprints rather than to references. Splitting the
footprint solely to change F1's appearance would mean a second library part with identical
copper — cost without benefit. Accepted under the tolerance policy.

**U27 is a TO-92 transistor, not a regulator.** The design spec's prose calls U25/U27
regulators; the board says `Transistor_TO92_EBC_254`. The board is right.
```

- [ ] **Step 9: Commit**

```bash
git add tools/apply_models.py tools/models.tsv docs/3d-model-sources.md \
        KiCad/Radio86RK.pretty KiCad/Radio-86RK.kicad_pcb verify/renders
git commit -m "Add 3D models for 76 passive components

Eight footprint definitions cover 76 instances, since models attach to
footprints rather than references. All models are KiCad stock .step files
referenced through the KICAD10_3DMODEL_DIR variable.

Gerber gate passes, which also proves the pcbnew SaveBoard round-trip is
lossless. 3D coverage 0/183 -> 76/183.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 5: 3D models for socketed DIP ICs (24 ICs, 7 footprints)

Every DIP on this board sits in a socket, so each of the 7 DIP footprints carries **two**
models: the socket at board level and the chip raised to the socket's seating height.

The prototype uses Amphenol FCI DILB `-223TLF` stamped-and-formed sockets. Amphenol
publishes no overall height; distributor package data reports **5.48 mm** consistently for
the 14, 16, 28 and 40 position parts across both row spacings, and height is a property of
the insulator's extruded cross-section rather than of body length — so 5.48 mm is used for
20 and 24 as well. The 8-pin is the sole outlier at **5.1 mm**.

**Files:**
- Modify: `tools/models.tsv`, `docs/3d-model-sources.md`
- Modify: `KiCad/Radio86RK.pretty/IC_DIP*.kicad_mod` (7 files), `KiCad/Radio-86RK.kicad_pcb`

**Interfaces:**
- Consumes: `tools/apply_models.py` from Task 4, unchanged. Multi-model support is already
  in it — this task is the first to use it.

- [ ] **Step 1: Verify the socket/chip model pairs exist**

```bash
source tools/kicad-env.sh
for m in DIP-8_W7.62mm DIP-14_W7.62mm DIP-16_W7.62mm DIP-20_W7.62mm \
         DIP-24_W15.24mm DIP-28_W15.24mm DIP-40_W15.24mm; do
  for v in "" "_Socket"; do
    f="$KICAD_3DMODEL_DIR/Package_DIP.3dshapes/${m}${v}.step"
    [ -f "$f" ] || echo "MISSING: $f"
  done
done
echo "check complete"
```

Expected: `check complete` with no `MISSING` lines — all 14 files.

- [ ] **Step 2: Append the socket composites to `tools/models.tsv`**

Row spacing follows the board: the `*_300` footprints are 300 mil (7.62 mm), the `*_600`
are 600 mil (15.24 mm).

```
# --- Socketed DIP ICs: socket at z=0, chip at seating height ---
IC_DIP8_300	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-8_W7.62mm_Socket.step	0
IC_DIP8_300	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-8_W7.62mm.step	5.1
IC_DIP14_300	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-14_W7.62mm_Socket.step	0
IC_DIP14_300	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-14_W7.62mm.step	5.48
IC_DIP16_300	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-16_W7.62mm_Socket.step	0
IC_DIP16_300	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-16_W7.62mm.step	5.48
IC_DIP20_300	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-20_W7.62mm_Socket.step	0
IC_DIP20_300	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-20_W7.62mm.step	5.48
IC_DIP24_600	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-24_W15.24mm_Socket.step	0
IC_DIP24_600	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-24_W15.24mm.step	5.48
IC_DIP28_600	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-28_W15.24mm_Socket.step	0
IC_DIP28_600	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-28_W15.24mm.step	5.48
IC_DIP40_600	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-40_W15.24mm_Socket.step	0
IC_DIP40_600	${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-40_W15.24mm.step	5.48
```

- [ ] **Step 3: Apply**

```bash
"$KICAD_PY" tools/apply_models.py tools/models.tsv "$PCB" "$REPO_ROOT/KiCad/Radio86RK.pretty"
```

Expected: `applied to 15 footprints / 100 instances` — the 8 passive footprints from
Task 4 (76 instances) plus these 7 (24 instances). The script is idempotent, so
re-applying Task 4's rows is intentional and harmless.

- [ ] **Step 4: Verify the composite landed in the board, not just the library**

```bash
grep -A3 'DIP-40_W15.24mm' KiCad/Radio-86RK.kicad_pcb | grep -E 'model|xyz' | head -8
```

Expected: the socket model with `(xyz 0 0 0)` and the chip model with `(xyz 0 0 5.48)`.

- [ ] **Step 5: Run the gate**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`.

- [ ] **Step 6: Render — this is the step that catches a wrong Z offset**

```bash
tools/render.sh 05-dip-sockets
```

Expected: 24 ICs visibly seated **in** sockets — a distinct socket body under each chip,
chip bodies not intersecting the socket rails and not floating above them. Compare U21
(8-pin, 5.1 mm) against U1 (40-pin, 5.48 mm); both should look seated.

- [ ] **Step 7: Extend `docs/3d-model-sources.md`**

```markdown
## Socketed DIP ICs

24 of the 27 `U` components are DIP parts in sockets. Each carries two models: the socket
at z=0 and the chip at the socket's seating height. U25 (TO-220), U26 (SIP DC-DC) and U27
(TO-92) are not DIP parts and take a single model each.

| Footprint | Refs | Socket (z=0) | Chip (z=offset) | Offset |
|---|---|---|---|---:|
| `IC_DIP8_300` | U21, U23, U24 | `DIP-8_W7.62mm_Socket` | `DIP-8_W7.62mm` | 5.1 |
| `IC_DIP14_300` | U15-U20 | `DIP-14_W7.62mm_Socket` | `DIP-14_W7.62mm` | 5.48 |
| `IC_DIP16_300` | U2, U14, U22 | `DIP-16_W7.62mm_Socket` | `DIP-16_W7.62mm` | 5.48 |
| `IC_DIP20_300` | U12 | `DIP-20_W7.62mm_Socket` | `DIP-20_W7.62mm` | 5.48 |
| `IC_DIP24_600` | U4, U13 | `DIP-24_W15.24mm_Socket` | `DIP-24_W15.24mm` | 5.48 |
| `IC_DIP28_600` | U3, U9, U10, U11 | `DIP-28_W15.24mm_Socket` | `DIP-28_W15.24mm` | 5.48 |
| `IC_DIP40_600` | U1, U5-U8 | `DIP-40_W15.24mm_Socket` | `DIP-40_W15.24mm` | 5.48 |

**Where the heights come from.** The prototype uses Amphenol FCI DILB `-223TLF`
stamped-and-formed sockets. Amphenol's spec sheet publishes Dim A/B/C/D, pitch, row
spacing and tail length but no overall height. Distributor package data reports 5.48 mm for
the 14, 16, 28 and 40 position parts and for the 0.3" sibling `DILB24P-224TLF`, across both
row spacings and from 14 to 40 positions. Height is a property of the insulator's extruded
cross-section and does not vary with body length, so 5.48 mm is taken for 20 and 24 as
well; the 8-pin at 5.1 mm is the only outlier. A 0.38 mm error here is invisible in the
viewer and cannot reach the board.

**Western parts, not Soviet.** The prototype is populated with Intel `P8255A-5`, NEC
`8257C-5`, TI `SN74198N` and `74LS74` rather than the Soviet equivalents in the dual
silkscreen markings, so package choices follow the Western parts.
```

- [ ] **Step 8: Commit**

```bash
git add tools/models.tsv docs/3d-model-sources.md \
        KiCad/Radio86RK.pretty KiCad/Radio-86RK.kicad_pcb verify/renders
git commit -m "Add socket+chip 3D composites for the 24 socketed DIP ICs

Every DIP on this board sits in an Amphenol FCI DILB socket, so each of the
7 DIP footprints carries two models: socket at z=0 and chip raised to the
seating height (5.1mm for 8-pin, 5.48mm for the rest).

3D coverage 76/183 -> 100/183. Gerber gate passes.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 6: 3D models for connectors, arrays and misc (15 components, 12 footprints)

The hardest sourcing task. KiCad ships no RCA jack and no 8-pin DIN model, so those two are
either sourced externally into a project-local library or recorded as documented fallbacks.
Per the spec's failure paths, a missing or approximate model is cosmetic and never blocks.

**Files:**
- Modify: `tools/models.tsv`, `docs/3d-model-sources.md`
- Create (conditionally): `KiCad/Radio86RK.3dshapes/`
- Modify: `KiCad/Radio86RK.pretty/*.kicad_mod` (12 files), `KiCad/Radio-86RK.kicad_pcb`

**Interfaces:**
- Consumes: `tools/apply_models.py` unchanged.
- Produces: nothing new; completes non-switch 3D coverage at 115/183.

- [ ] **Step 1: Append the 10 models KiCad already ships**

```
# --- Connectors, resistor arrays, misc ---
Conn_SIL6	${KICAD10_3DMODEL_DIR}/Resistor_THT.3dshapes/R_Array_SIP6.step	0
Conn_SIL10	${KICAD10_3DMODEL_DIR}/Resistor_THT.3dshapes/R_Array_SIP10.step	0
Conn_Pin_Header_4x1_2.54mm	${KICAD10_3DMODEL_DIR}/Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x04_P2.54mm_Vertical.step	0
Conn_Pin_Header_20x1_2.54mm	${KICAD10_3DMODEL_DIR}/Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x20_P2.54mm_Vertical.step	0
Conn_Pin_Header_13x2_2.54mm_Shrouded	${KICAD10_3DMODEL_DIR}/Connector_IDC.3dshapes/IDC-Header_2x13_P2.54mm_Vertical.step	0
Conn_Friction_Lock_8P_2.54mm	${KICAD10_3DMODEL_DIR}/Connector_Molex.3dshapes/Molex_KK-254_AE-6410-08A_1x08_P2.54mm_Vertical.step	0
Conn_Power_Jack_Circular_Pads	${KICAD10_3DMODEL_DIR}/Connector_BarrelJack.3dshapes/BarrelJack_CUI_PJ-063AH_Horizontal.step	0
Conn_Dsub_DE9M	${KICAD10_3DMODEL_DIR}/Connector_Dsub.3dshapes/DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset9.40mm.step	0
Speaker_12mm	${KICAD10_3DMODEL_DIR}/Buzzer_Beeper.3dshapes/Buzzer_12x9.5RM7.6.step	0
DC-DC_SIP8	${KICAD10_3DMODEL_DIR}/Converter_DCDC.3dshapes/Converter_DCDC_Bothhand_CFUSxxxx_THT.step	0
```

`RN1-RN4` are SIP resistor networks, so `R_Array_SIP6`/`SIP10` are used rather than pin
headers — same pin count and pitch, correct body.

- [ ] **Step 2: Verify those 10 paths resolve**

```bash
source tools/kicad-env.sh
awk -F'\t' '!/^#/ && NF>=2 {print $2}' tools/models.tsv \
  | sed "s|\${KICAD10_3DMODEL_DIR}|$KICAD_3DMODEL_DIR|" \
  | while read -r m; do [ -f "$m" ] || echo "MISSING: $m"; done
echo "check complete"
```

Expected: `check complete`, no `MISSING`.

- [ ] **Step 3: Source models for J1 (RCA) and J4 (8-pin DIN)**

KiCad ships neither. Attempt, in this order, and stop at the first success:

1. The manufacturer's own STEP download for the actual part.
2. A SnapEDA / Ultra Librarian / GrabCAD export of an equivalent part.
3. The recorded fallback below.

If a model is obtained, save it as `KiCad/Radio86RK.3dshapes/<Name>.step` and reference it
through `${KIPRJMOD}`, which keeps the project standalone:

```
Conn_RCA_Right	${KIPRJMOD}/Radio86RK.3dshapes/RCA_Jack_Right_Angle.step	0
Conn_DIN_8pin	${KIPRJMOD}/Radio86RK.3dshapes/DIN_8pin_270deg.step	0
```

If sourcing fails, use the fallback rows instead and say so in the docs:

```
Conn_RCA_Right	${KICAD10_3DMODEL_DIR}/Connector_Coaxial.3dshapes/BNC_Amphenol_B6252HB-NPP3G-50_Horizontal.step	0
Conn_DIN_8pin	-	0
```

`BNC_..._Horizontal` is a horizontal panel-mount coaxial jack — the closest public shape to
a right-angle RCA. There is no comparable stand-in for an 8-pin DIN, so `-` records a
deliberate blank rather than an oversight.

- [ ] **Step 4: Apply**

```bash
"$KICAD_PY" tools/apply_models.py tools/models.tsv "$PCB" "$REPO_ROOT/KiCad/Radio86RK.pretty"
```

Expected: `applied to 27 footprints / 115 instances` (or `/ 114` if J4 is blank).

- [ ] **Step 5: Run the gate**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`.

- [ ] **Step 6: Count 3D coverage explicitly**

```bash
source tools/kicad-env.sh
"$KICAD_PY" - "$PCB" <<'PY'
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
have = [f.GetReference() for f in b.GetFootprints() if len(f.Models()) > 0]
none = sorted(f.GetReference() for f in b.GetFootprints() if len(f.Models()) == 0)
print("with models: %d   without: %d" % (len(have), len(none)))
print("without:", " ".join(none))
PY
```

Expected: `with models: 115  without: 76`. The 76 without are the 68 `SW` (Task 9), the 7
`HOLE` and `LOGO1` — the last 8 are permanently modelless by design.

- [ ] **Step 7: Render**

```bash
tools/render.sh 06-connectors
```

Expected: every connector, resistor array, the speaker and the DC-DC module visible and
correctly oriented. Check J5 (DE9) and J2 (barrel jack) point outward at the board edge
rather than into the board.

- [ ] **Step 8: Extend `docs/3d-model-sources.md`**

```markdown
## Connectors, arrays and misc

| Footprint | Refs | Model | Fidelity |
|---|---|---|---|
| `Conn_SIL6` | RN2-RN4 | `Resistor_THT/R_Array_SIP6` | exact pin count and pitch |
| `Conn_SIL10` | RN1 | `Resistor_THT/R_Array_SIP10` | exact pin count and pitch |
| `Conn_Pin_Header_4x1_2.54mm` | JP1, JP2 | `PinHeader_1x04_P2.54mm_Vertical` | exact |
| `Conn_Pin_Header_20x1_2.54mm` | J7 | `PinHeader_1x20_P2.54mm_Vertical` | exact |
| `Conn_Pin_Header_13x2_2.54mm_Shrouded` | J6 | `IDC-Header_2x13_P2.54mm_Vertical` | exact |
| `Conn_Friction_Lock_8P_2.54mm` | J3 | `Molex_KK-254_AE-6410-08A_1x08_P2.54mm_Vertical` | exact family |
| `Conn_Power_Jack_Circular_Pads` | J2 | `BarrelJack_CUI_PJ-063AH_Horizontal` | equivalent barrel jack |
| `Conn_Dsub_DE9M` | J5 | `DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset9.40mm` | exact |
| `Speaker_12mm` | SP1 | `Buzzer_12x9.5RM7.6` | 12mm body, correct pitch |
| `DC-DC_SIP8` | U26 | `Converter_DCDC_Bothhand_CFUSxxxx_THT` | generic SIP DC-DC |

### The two KiCad does not ship

`Conn_RCA_Right` (J1) and `Conn_DIN_8pin` (J4) have no model anywhere in KiCad 10's
libraries. Record here which branch was taken:

- **Sourced** - file placed in `KiCad/Radio86RK.3dshapes/`, referenced via `${KIPRJMOD}`
  so a fresh clone still renders it. Note the origin and licence.
- **Fallback** - J1 renders as a horizontal BNC jack, the nearest public shape. J4 renders
  as nothing; there is no comparable public 8-pin DIN and a wrong connector is worse than
  an absent one.
```

- [ ] **Step 9: Commit**

```bash
git add tools/models.tsv docs/3d-model-sources.md KiCad verify/renders
git commit -m "Add 3D models for connectors, resistor arrays and misc

Ten of twelve footprints map to KiCad stock models. RCA (J1) and 8-pin DIN
(J4) have no public model; both are recorded in docs/3d-model-sources.md
with whichever branch was taken - sourced into Radio86RK.3dshapes or the
documented fallback.

3D coverage 100/183 -> 115/183; the remaining 68 switches are Task 7.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 7: 3D models for the keyboard (68 switches, 6 footprints)

The last 68 components, completing 3D coverage at 183/183. Like every other 3D task, this
one **does not touch copper** — the switches keep their vendored footprints and simply gain
models.

**Why the switch footprints are not replaced.** An earlier revision of this plan adopted
perigoso's `SW_Cherry_MX_PCB_*u` footprints, on the design spec's stated grounds that doing
so *"brings a 3D model"*. That premise is false. `models.tsv` attaches a model to any
footprint by name — it is how the other 27 footprints in Tasks 4–6 get theirs — so the
perigoso *model* never required the perigoso *footprint*. The origins already coincide:
both put the switch's centre guide boss at (0, 0), so `SW_Cherry_MX_PCB.stp` lands correctly
on the board's own geometry with no offset.

Dropping that substitution removes, at no cost to the result:

| Removed | Why it existed |
|---|---|
| Pad growth 2.286 → 2.5 mm on 67 switches | a side effect of adopting perigoso's pads |
| The schematic pin swap on all 67 switches | to compensate for perigoso's exchanged pad names |
| Two clearance violations (SW4, SW61 at 0.150 mm) | a consequence of the pad growth |
| A prototype measurement gate | to dispose of those violations |
| Derived stabilized footprints for SW11/SW64 | to re-add stabilizer holes perigoso lacks |

The pin swap in particular was the single riskiest operation in this plan — applied to the
wrong subset it shorts the keyboard matrix — and it existed only to undo a change that was
itself unnecessary. **Cherry specifies hole sizes, not land diameter** (⌀1.5 mm terminals,
⌀4.0 mm boss, ⌀1.7 mm locating pins), so neither 2.286 mm nor 2.5 mm is "the manufacturer's
value"; keeping the board's own pads forfeits nothing.

What is given up is cosmetic: perigoso's tidier silkscreen, and a real `F.CrtYd` courtyard
where skiselev draws the outline on `Eco2.User` (which KiCad 10 does not treat as a
courtyard, so `courtyard_overlap` checks stay inert for switches). Adding courtyards to the
vendored footprints later is a non-copper change and remains available.

**The wide keys keep their stabilizer holes** because their footprints are never replaced.
SW11 (2.25u) carries ⌀3.9878 at (±11.938, +8.255) and ⌀3.048 at (±11.938, −6.985); SW64
(6.25u, spacebar) carries ⌀3.9878 at (±50.038, −8.255) and ⌀3.048 at (±50.038, +6.985).
Per skiselev's README BOM these take Cherry **G99-0742** leveling kits, with SW64
additionally using the **wire from a G99-0226** (MX 1x8) in G99-0742 housings — a hybrid
assembly, which is why its 100.076 mm spacing matches no stock 6.25u part.

**Files:**
- Modify: `tools/models.tsv`, `docs/3d-model-sources.md`
- Modify: `KiCad/Radio86RK.pretty/CHERRY_PCB_*.kicad_mod`, `KiCad/Radio-86RK.kicad_pcb`

**Interfaces:**
- Consumes: `tools/apply_models.py` from Task 4, unchanged — including its optional
  4th column, which this task is the first to use.

- [ ] **Step 1: Confirm the model origins coincide**

This is the fact the whole task rests on. If the two footprints did not share an origin, the
model would need an offset.

```bash
source tools/kicad-env.sh
PG="$KICAD_3RD_PARTY/footprints/com_github_perigoso_keyswitch-kicad-library"
echo "board:"; grep -A2 '(pad ""' KiCad/Radio86RK.pretty/CHERRY_PCB_100H.kicad_mod \
  | grep -B1 '3.9878' | grep '(at '
echo "perigoso:"; grep '(at 0 0)' "$PG/Switch_Keyboard_Cherry_MX.pretty/SW_Cherry_MX_PCB_1.00u.kicad_mod" \
  | grep 'size 4 4'
```

Expected: both centre bosses at `(0 0)` — the board's at ⌀3.9878, perigoso's at ⌀4.0. Same
origin, so the model needs no offset.

- [ ] **Step 2: Verify the six model files exist**

```bash
source tools/kicad-env.sh
D="$KICAD_3RD_PARTY/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes"
for m in SW_Cherry_MX_PCB Stabilizer_Cherry_MX_2.00u Stabilizer_Cherry_MX_6.25u; do
  [ -f "$D/$m.stp" ] || echo "MISSING: $D/$m.stp"
done
[ -f "$KICAD_3DMODEL_DIR/Button_Switch_THT.3dshapes/SW_Tactile_SPST_Angled_PTS645Vx31-2LFS.step" ] \
  || echo "MISSING: tactile switch model"
echo "check complete"
```

Expected: `check complete`, no `MISSING` lines.

- [ ] **Step 3: Append the keyboard rows to `tools/models.tsv`**

The fourth column is the Z rotation. perigoso's 6.25u stabilizer model is mirrored in Y
relative to this board's hole pattern — its big holes sit at +8.225 where the board's sit at
−8.255 — so SW64's stabilizer needs 180°. SW11's does not.

```
# --- Keyboard: plain switches ---
CHERRY_PCB_100H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/SW_Cherry_MX_PCB.stp	0	0
CHERRY_PCB_125H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/SW_Cherry_MX_PCB.stp	0	0
CHERRY_PCB_150H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/SW_Cherry_MX_PCB.stp	0	0
# --- Keyboard: stabilized wide keys, switch + stabilizer composite ---
CHERRY_PCB_225H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/SW_Cherry_MX_PCB.stp	0	0
CHERRY_PCB_225H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/Stabilizer_Cherry_MX_2.00u.stp	0	0
CHERRY_PCB_625H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/SW_Cherry_MX_PCB.stp	0	0
CHERRY_PCB_625H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/Stabilizer_Cherry_MX_6.25u.stp	0	180
# --- Keyboard: reset switch ---
Switch_Tactile_6mm_Right	${KICAD10_3DMODEL_DIR}/Button_Switch_THT.3dshapes/SW_Tactile_SPST_Angled_PTS645Vx31-2LFS.step	0	0
```

- [ ] **Step 4: Apply**

```bash
source tools/kicad-env.sh
"$KICAD_PY" tools/apply_models.py tools/models.tsv "$PCB" "$REPO_ROOT/KiCad/Radio86RK.pretty"
```

Expected: `applied to 33 footprints / 183 instances` — the 27 footprints from Tasks 4–6
(115 instances) plus these 6 (68 instances).

- [ ] **Step 5: Run the gate**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`. **This is the step that distinguishes Option C from the abandoned
approach**: the keyboard now passes the same unmodified strict gate as every other task, so
the board carries no authorized copper exception at all.

- [ ] **Step 6: Confirm full 3D coverage**

```bash
source tools/kicad-env.sh
"$KICAD_PY" - "$PCB" <<'PY'
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
none = sorted(f.GetReference() for f in b.GetFootprints() if len(f.Models()) == 0)
print("without models: %d ->" % len(none), " ".join(none))
PY
```

Expected: only the 7 `HOLE` references and `LOGO1` (plus `J4` if its model was not
sourced) — i.e. **183/183** coverage of components that should have one.

- [ ] **Step 7: Render, and check the stabilizers specifically**

```bash
tools/render.sh 07-keyboard-complete
```

Expected: all 68 keys present with keycap-less switch bodies. Check SW11 and SW64
closely: the stabilizer wire and housings must render **alongside** the switch body, and
SW64's must sit on the correct side of the key. **If SW64's stabilizer looks mirrored, the
180° is on the wrong row** — it belongs on the `Stabilizer_Cherry_MX_6.25u` line, not the
`SW_Cherry_MX_PCB` one.

The stabilizer models sit 30 µm (SW11) and 38 µm (SW64) from the board's actual hole
centres, because perigoso models them at ±11.938/±50 where this board uses ±11.938/±50.038.
That is invisible in the viewer and is exactly the kind of difference the 3D tolerance
policy exists to permit.

- [ ] **Step 8: Extend `docs/3d-model-sources.md`**

```markdown
## Keyboard

| Footprint | Refs | Model(s) | Note |
|---|---|---|---|
| `CHERRY_PCB_100H` | 62 keys | `SW_Cherry_MX_PCB` | perigoso, via PCM |
| `CHERRY_PCB_125H` | SW65, SW66 | `SW_Cherry_MX_PCB` | |
| `CHERRY_PCB_150H` | SW61 | `SW_Cherry_MX_PCB` | |
| `CHERRY_PCB_225H` | SW11 | `SW_Cherry_MX_PCB` + `Stabilizer_Cherry_MX_2.00u` | composite |
| `CHERRY_PCB_625H` | SW64 | `SW_Cherry_MX_PCB` + `Stabilizer_Cherry_MX_6.25u` @ 180° | composite, mirrored |
| `Switch_Tactile_6mm_Right` | SW68 | `SW_Tactile_SPST_Angled_PTS645Vx31-2LFS` | reset switch |

**The footprints are the board's own, not perigoso's.** Only the models come from perigoso.
The design spec proposed adopting perigoso's footprints on the grounds that doing so "brings
a 3D model", but models attach to any footprint by name, and both libraries put the switch's
centre boss at (0, 0), so the model lands correctly on the original geometry. Keeping the
board's footprints avoids a 2.286 → 2.5 mm pad growth, the compensating schematic pin swap,
two clearance violations at 0.150 mm, and the loss of SW11/SW64's stabilizer holes — all for
no loss beyond silkscreen cosmetics.

Cherry specifies hole sizes (⌀1.5 mm terminals, ⌀4.0 mm boss, ⌀1.7 mm locating pins), not
land diameter, so the board's 2.286 mm pads are as legitimate as perigoso's 2.5 mm.
skiselev's figures are Cherry's metric drawing on an imperial grid: 1.4986 mm = 0.059″,
1.7018 mm = 0.067″, 3.9878 mm = 0.157″.

### Stabilizers

SW11 and SW64 keep the stabilizer holes baked into their footprints. Per skiselev's README
BOM they take Cherry **G99-0742** leveling kits (Mouser `540-G99-0742`), and SW64
additionally uses the **wire from a G99-0226** (MX 1x8, `540-G99-0226`) fitted into G99-0742
housings — *"use the wire from this part and one of 540-G99-0742 to build a through hole
leveling kit for the spacebar"*. That hybrid is why SW64's 100.076 mm spacing matches no
stock 6.25u stabilizer, and why perigoso's is 38 µm out and mirrored.

| Ref | Size | Stabilizer holes (mm) |
|---|---|---|
| SW11 | 2.25u | ⌀3.9878 at (±11.938, +8.255); ⌀3.048 at (±11.938, −6.985) |
| SW64 | 6.25u | ⌀3.9878 at (±50.038, −8.255); ⌀3.048 at (±50.038, +6.985) |
```

- [ ] **Step 9: Commit**

```bash
git add tools/models.tsv docs/3d-model-sources.md \
        KiCad/Radio86RK.pretty KiCad/Radio-86RK.kicad_pcb verify/renders
git commit -m "Add 3D models for the keyboard; 3D coverage complete at 183/183

The switches keep their own footprints and simply gain models. The design
spec proposed adopting perigoso's footprints because doing so 'brings a 3D
model', but models attach to any footprint by name - as the other 27
footprints in Tasks 4-6 demonstrate - and both libraries put the switch's
centre boss at (0,0), so the model lands correctly on the original geometry.

Not doing the substitution avoids a 2.286 -> 2.5mm pad growth on 67
switches, the compensating schematic pin swap, two clearance violations at
0.150mm needing a prototype measurement, and the loss of SW11/SW64's
stabilizer holes. Cost is cosmetic: perigoso's tidier silkscreen and a real
F.CrtYd courtyard.

SW11 and SW64 get switch+stabilizer composites; SW64's stabilizer is rotated
180 degrees because perigoso models it mirrored relative to this board.

The board now has no authorized copper exception: --strict passes everywhere.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 8: Refresh symbol definitions and drive ERC down

> **STATUS: mostly complete.** The symbol refresh landed in `9d8e182` (ERC **243 → 101**,
> all 142 `lib_symbol_mismatch` cleared) and the Q1/Q2 re-home in `16a7755`. What remains is
> the 32 label collisions, Q1/Q2's stale cache, and `sym-lib-table`. Resume at Step 6.

**This task is schematic-only. It must never run *Update PCB from Schematic*.** That single
rule is the difference between the two runs recorded below: one produced 170 shorts, the
other changed no connectivity at all and cleared 142 warnings.

**Everything here resolves through public reuse — nothing needs vendoring.** The
mismatching symbols were *KiCad's own* stock symbols that drifted between KiCad 4 and
KiCad 10 (power flags, 74xx logic, `Device:D`/`LED`), not the lost `my_components` library.
And `Device:Q_NPN_EBC` was not deleted — it moved to `Transistor_BJT`, same name, same
E-B-C pin numbering.

> **The failure that shaped this task.** The first attempt ran *Update Symbols from Library*
> with the *Update/reset Fields* options enabled, then *Update PCB from Schematic*. KiCad's
> own warning describes what happens — *"Warning: fields "Value" and "Footprints" will be
> therefore replaced."* — and it did: 8 components (RN1–RN4, U22–U25) were reset to their
> symbols' default footprints and that was pushed onto the board. DRC went 91 → **669**,
> with **170 `shorting_items`** and **2118 unconnected items**, because the stock footprints
> anchor their pads at a different origin (RN2 shifted 6.35 mm, U25 a full 2.54 mm pitch).
> Recovered with `git checkout -- KiCad/`. See Finding 4.

**Files:**
- Modify: `KiCad/*.kicad_sch` *(refresh done, `9d8e182`; Q1/Q2 done, `16a7755`)*
- Create: `KiCad/Radio86RK.kicad_sym`, `KiCad/sym-lib-table` *(outstanding)*
- Create: `docs/erc-exclusions.md` *(outstanding)*

**Interfaces:**
- Consumes: `tools/netlist-gate.sh`, `tools/rules-report.sh`, `tools/gerber-gate.sh`.
- Produces: nothing reusable; this task is schematic edits plus one file copy.

- [x] **Step 1: Capture the footprint assignments before touching anything**

The check that catches the destructive failure. Measured baseline: **218** footprint fields.

```bash
grep -h -A1 '"Footprint"' KiCad/*.kicad_sch \
  | grep -oE '"[A-Za-z_][A-Za-z0-9_]*:[^"]*"' | sort | uniq -c | sort -rn \
  > verify/footprint-props-before.txt
```

- [x] **Step 2: Capture the netlist baseline**

```bash
tools/netlist-gate.sh --capture
```

- [x] **Step 3: Refresh the symbol definitions — the safe procedure**

In Eeschema: **Tools → Update Symbols from Library…**

- Scope: **Update all symbols in schematic**
- In **Update/reset Fields**, uncheck **every** option: field text, field visibilities,
  field sizes and styles, field positions, pin name/number visibilities, symbol attributes,
  *Remove fields if not in library symbol*, *Reset fields if empty in library symbol*, and
  *Update keywords and footprint filters*.

With all of those off the action still does its core job — *update symbol shape and pins* —
which is the only part wanted. Save, and **do not run *Update PCB from Schematic***.

Two errors are expected and benign: `Update symbol Q1/Q2 from 'Device:Q_NPN_EBC' … symbol
not found`. That symbol moved libraries; Step 5 fixes it.

- [x] **Step 4: Verify — four checks, all measured on `9d8e182`**

```bash
grep -h -A1 '"Footprint"' KiCad/*.kicad_sch \
  | grep -oE '"[A-Za-z_][A-Za-z0-9_]*:[^"]*"' | sort | uniq -c | sort -rn \
  > verify/footprint-props-after.txt
diff verify/footprint-props-before.txt verify/footprint-props-after.txt \
  && echo "footprints intact"
tools/netlist-gate.sh
tools/rules-report.sh
tools/gerber-gate.sh --strict
```

Measured: footprints **218/218 unchanged**; netlist connectivity **byte-identical**
(6790 lines in the `(nets …)` section); **ERC 243 → 101**; DRC 91, unconnected 0, parity 0;
gerbers byte-identical to v1.4.

The only content changes are metadata refreshes from the current libraries — updated
`ki_keywords` and `ki_fp_filters`, real datasheet URLs replacing KiCad-4-era relative
paths, added ngspice `Sim.*` fields, and `#LOGO` → `#SYM` for the annotation-only logo
symbol.

**If the footprint diff is non-empty, stop and `git checkout -- KiCad/`.** That is the
destructive failure recurring, and it means a field option was left checked.

- [x] **Step 5: Re-home Q1/Q2 to the library that now holds their symbol** — `16a7755`

```bash
sed -i '' 's|Device:Q_NPN_EBC|Transistor_BJT:Q_NPN_EBC|g' \
    KiCad/Radio-86RK-CRT-Mem.kicad_sch KiCad/Radio-86RK-IO.kicad_sch
```

Two occurrences per sheet — the `lib_symbols` cache key and the instance `lib_id` — so one
substitution keeps them consistent. Verified: netlist connectivity byte-identical,
footprints 218/218 intact, board untouched. The two violations change class from
`lib_symbol_issues` (not found) to `lib_symbol_mismatch` (found, cache differs).

---

**Resume here.** ERC currently 101 = 67 `footprint_link_issues` + 32
`same_local_global_label` + 2 `lib_symbol_mismatch`.

- [ ] **Step 6: One more symbol refresh, bundled with Step 7**

Q1/Q2's cache still holds the old `Device` definition under the new key. Re-running Step 3's
procedure now finds `Transistor_BJT:Q_NPN_EBC` and rewrites it, clearing the last 2
`lib_symbol_mismatch`.

Do this in the **same Eeschema session** as Step 7 rather than as its own trip — 2 warnings
do not justify a separate round-trip with an operation that has already broken the board
once. Re-run Step 4's four checks afterwards.

- [ ] **Step 7: Resolve the 32 `same_local_global_label` collisions**

All 32 are bus and control signals carrying both a local and a global label of the same
name — 15 address lines `A0`–`A14`, 8 data lines `D0`–`D7`, the four strobes `~{RD}`,
`~{WR}`, `~{IOR}`, `~{MEMW}`, and `OSC`, `RESET`, `TTL_CLK`, `SPKR_ENA`, `PIT2_ENA`.

In an 8080-family design these are genuinely one net each, so the fix is to **delete the
redundant local label** and let the global one name the net. That changes no net name, so
the netlist and the gerber `%TO.N` records are untouched.

None of these are the RS-232 signals on U3/U22, so this is not the masking manoeuvre the
design spec warns about. **Do not add or promote any label on U3 or U22.**

```bash
tools/netlist-gate.sh
tools/gerber-gate.sh --strict
tools/rules-report.sh | tee verify/rules-08-symbols.txt
```

Expected: netlist and gerber gates both `PASS` — deleting a redundant duplicate label
renames nothing. If `--strict` fails, inspect the diff: every changed line must be a
`%TO.N` record for a net you deliberately renamed.

Expected ERC afterwards: **67**, all `footprint_link_issues`, which Task 3 clears.

New `pin_not_driven` / `pin_not_connected` / `unconnected_wire_endpoint` violations on
**U3 and U22** may appear as connectivity checks stop being suppressed — that is
GitHub issue #2 becoming visible, which is correct, not a regression.

- [ ] **Step 8: Vendor the `my_components` symbols so a fresh clone works**

Copy the library wholesale. It is 2.1 MB against the 131 MB of datasheets this repo already
carries, so trimming it to the 18 symbols actually used would save about 1.6% of
`Documentation/` — not worth a line of code, let alone a custom s-expression parser.

```bash
source tools/kicad-env.sh
cp ../my_kicad_library/library/my_components.kicad_sym KiCad/Radio86RK.kicad_sym
"$KICAD_CLI" sym upgrade KiCad/Radio86RK.kicad_sym
rm -rf .build/symcheck && mkdir -p .build/symcheck
"$KICAD_CLI" sym export svg --output .build/symcheck KiCad/Radio86RK.kicad_sym >/dev/null \
  && echo "library parses and renders: $(ls .build/symcheck | wc -l | tr -d ' ') units"
```

Verified: 502 symbols upgrade to `version 20251024` and all 671 units render.

Confirm the 18 this project uses are present:

```bash
grep -oh 'lib_id "my_components:[^"]*"' KiCad/*.kicad_sch | sed 's/.*://;s/"//' | sort -u \
  | while read -r s; do grep -q "(symbol \"$s\"" KiCad/Radio86RK.kicad_sym || echo "MISSING: $s"; done
echo "check complete"
```

Expected: `check complete`, no `MISSING` lines. The 18 are `27C64 74198 8080A 8224 8251A
8254 8255A 8257 8275 AS6C62256 Conn_DIN-8 DE9 DS1233 HOLE IZ0512S SN75150P SN75154P
Switch_Tactile_Vertical`.

> **Why not extract only the 18?** An earlier draft of this plan did, via a
> `tools/vendor_symbols.py` that hand-sliced symbol blocks out of the `.kicad_sym` file by
> paren-matching. It produced a library KiCad rejected with *"Unable to load library"* even
> after the format version was made to match, and the cause was never isolated. Copying the
> file KiCad already reads is correct by construction and removes an untested tool from the
> plan. The footprint side is different and does need extraction — there the *board* is the
> geometry authority and no library holds the right data.

- [ ] **Step 9: Write `KiCad/sym-lib-table`**

`my_components` is the only project-local symbol library needed; every other symbol now
comes from KiCad's stock libraries.

```
(sym_lib_table
	(version 7)
	(lib (name "my_components")(type "KiCad")(uri "${KIPRJMOD}/Radio86RK.kicad_sym")(options "")(descr "skiselev/my_kicad_library symbols used by this project, vendored"))
)
```

```bash
tools/rules-report.sh
tools/netlist-gate.sh
```

Expected: ERC unchanged; netlist `PASS`. If ERC *rises*, the vendored library differs from
the sibling clone and Step 8 dropped something.

- [ ] **Step 10: Write `docs/erc-exclusions.md` and exclude the issue-#2 violations**

```markdown
# Retained ERC violations

## U3 / U22 RS-232 wiring defect (GitHub issue #2)

The 8251A (U3) and SN75154 (U22) have their receiver input and output pins wired
backwards. This is a defect in the original v1.4 design, not a migration regression. It was
invisible to ERC until the symbol library links were resolved, because unresolved symbols
suppress KiCad's pin-connectivity checks project-wide.

It is **not fixed here**: correcting it requires moving wire endpoints, which is a topology
change, and this project's top constraint is that the board is preserved exactly. It is
also **not silenced by relabelling** — converting these signals to global labels would give
the pins a driver and hide the defect, which is what an earlier branch did. The 32 label
collisions resolved in Step 7 are address, data and control bus signals only; no label on
U3 or U22 was touched.
```

Add the exclusions in Eeschema (right-click → **Exclude with comment**), or under
`erc.exclusions` in `KiCad/Radio-86RK.kicad_pro`.

- [ ] **Step 11: Commit**

```bash
git add KiCad docs/erc-exclusions.md verify
git commit -m "Finish the symbol work: labels, vendored library, ERC exclusions

Deleted the 32 redundant local bus labels, vendored the 18 my_components
symbols so a fresh clone resolves, and excluded the pre-existing U3/U22
RS-232 defect with a written reason rather than masking it by relabelling.

Netlist connectivity unchanged; board untouched.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 9: Document the retained DRC violations as exclusions

DRC stands at 22: 17 `silk_edge_clearance` and 5 `starved_thermal`. Both are properties of
the 1986 board, preserved deliberately. They should not be "fixed" — fixing them would move
copper or silkscreen — and they should not sit as unexplained warnings either.

**Files:**
- Create: `docs/drc-exclusions.md`
- Modify: `KiCad/Radio-86RK.kicad_pro`

- [ ] **Step 1: Enumerate the 22 with their locations**

```bash
source tools/kicad-env.sh
tools/rules-report.sh > /dev/null
grep -o '"type": "[^"]*"' .build/drc.json | sort | uniq -c
```

Expected: `17 silk_edge_clearance`, `5 starved_thermal`.

- [ ] **Step 2: Write `docs/drc-exclusions.md`**

```markdown
# Retained DRC violations

DRC cannot reach zero on this board, and should not. All 22 remaining violations are
properties of skiselev's v1.4 design, preserved deliberately under the project's
board-is-frozen constraint. Each is excluded in `Radio-86RK.kicad_pro` with this reason.

## 17 x `silk_edge_clearance`

Silkscreen text and outlines that approach or cross the board edge. KiCad 4 did not check
this; KiCad 10 does. Fixing it means moving silkscreen, which changes the fab output for
purely cosmetic benefit.

**Reason recorded:** "preserved from v1.4 original, not a regression"

## 5 x `starved_thermal`

Thermal reliefs with insufficient spoke connection to their zone. Present in the original
routing. Fixing it means altering zone or pad geometry.

**Reason recorded:** "preserved from v1.4 original, not a regression"

## Not in this list

The keyboard adds nothing to this list. Task 7 attaches 3D models to the switch footprints
without replacing them, so no switch geometry changes and no new violation appears.
```

- [ ] **Step 3: Add the exclusions**

In Pcbnew, run DRC, right-click each violation → **Exclude with comment**, pasting
`preserved from v1.4 original, not a regression`. Save the board.

- [ ] **Step 4: Confirm they are now excluded, not merely present**

```bash
tools/rules-report.sh | tee verify/rules-08-exclusions.txt
grep -c 'exclusions' KiCad/Radio-86RK.kicad_pro
```

Expected: DRC still reports 22 items but all are excluded; the project file records them.

- [ ] **Step 5: Run the gate**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS` — exclusions live in the project file, not the board geometry.

- [ ] **Step 6: Commit**

```bash
git add KiCad/Radio-86RK.kicad_pro docs/drc-exclusions.md verify
git commit -m "Record the 22 inherited DRC violations as documented exclusions

17 silk_edge_clearance and 5 starved_thermal are properties of the v1.4
board that KiCad 4 never checked for. Fixing them would move silkscreen or
zone geometry for cosmetic benefit, which the board-is-frozen constraint
forbids. Excluded with a written reason so a future reader sees a decision
rather than an unexplained warning.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 10: Prove the project is standalone and record the result

The whole point of vendoring is that someone who clones this repo can open, check and
fabricate the board with nothing but KiCad 10. Prove it on a clean clone, not on the
working tree where stale caches and the sibling `my_kicad_library` checkout can mask a
missing file.

**Files:**
- Modify: `README.md`
- Create: `docs/modernization-summary.md`

- [ ] **Step 1: Clone into a scratch directory and check for absolute paths**

```bash
cd /tmp && rm -rf rk-clone && git clone -b kicad10-modernization \
    /Users/dveremeev/projects/radio-86rk rk-clone
cd rk-clone
grep -rEn '/Users/|/home/|C:\\\\' KiCad/*-lib-table KiCad/*.kicad_pcb KiCad/*.kicad_sym \
  | grep -v '^\s*$' || echo "no absolute paths - portable"
```

Expected: `no absolute paths - portable`.

- [ ] **Step 2: Run the full verification on the clone**

```bash
cd /tmp/rk-clone
tools/gerber-gate.sh --strict
tools/rules-report.sh
```

Expected: `PASS`, and rule counts matching `verify/rules-09-exclusions.txt` from Task 9. A
difference here means something the working tree provided is not in git.

- [ ] **Step 3: Confirm every 3D model resolves from the clone**

```bash
cd /tmp/rk-clone && source tools/kicad-env.sh
awk -F'\t' '!/^#/ && NF>=2 && $2!="-" {print $2}' tools/models.tsv \
  | sed -e "s|\${KICAD10_3DMODEL_DIR}|$KICAD_3DMODEL_DIR|" \
        -e "s|\${KICAD10_3RD_PARTY}|$KICAD_3RD_PARTY|" \
        -e "s|\${KIPRJMOD}|$PWD/KiCad|" \
  | sort -u | while read -r m; do [ -f "$m" ] || echo "MISSING: $m"; done
echo "model check complete"
```

Expected: `model check complete`, no `MISSING`.

- [ ] **Step 4: Render from the clone**

```bash
cd /tmp/rk-clone && tools/render.sh 10-fresh-clone
```

Compare against `verify/renders/09-keyboard-complete-top.png`. They should be
indistinguishable. A component missing here but present there is a file that never got
committed.

- [ ] **Step 5: Write `docs/modernization-summary.md`**

```markdown
# KiCad 10 modernization — outcome

| Metric | Before | After |
|---|---:|---:|
| File format | KiCad 6 (`20211014`), CRLF | KiCad 10 (`20260206`), LF |
| ERC violations | 243 | 0 + documented issue-#2 exclusions |
| DRC violations | 91 | 22, all excluded with written reasons |
| Unconnected items | 0 | 0 |
| Schematic/board parity | 0 | 0 |
| Components rendering in 3D | 0 / 183 | 183 / 183 |
| Opens from a fresh clone | no | yes |
| Gerber diff vs v1.4 | — | **empty**, no exception |

## What changed on the board

**Nothing.** All 191 footprints, all copper, every drill hole and all silkscreen are
byte-identical to skiselev's v1.4 output. The gerber and drill diff is empty, with no
exception anywhere in the project.

The design spec had proposed one authorized copper change — adopting perigoso's Cherry MX
footprints across the keyboard — on the grounds that doing so "brings a 3D model". That
premise turned out to be false: models attach to any footprint by name, and both libraries
put the switch's centre boss at (0, 0), so perigoso's model renders correctly on the board's
own geometry. Declining the substitution avoided a 2.286 → 2.5 mm pad growth on 67 switches,
a compensating schematic pin swap, two clearance violations at 0.150 mm, and the loss of
SW11 and SW64's stabilizer holes — at a cost of nothing but silkscreen cosmetics.

## How to verify any of this yourself

    tools/gerber-gate.sh --strict     # copper unchanged vs the frozen v1.4 baseline
    tools/rules-report.sh             # ERC and DRC counts by type
    tools/render.sh mycheck           # 3D render to verify/renders/
```

- [ ] **Step 6: Add a short section to `README.md`**

Point at `docs/modernization-summary.md`, `docs/3d-model-sources.md`,
`docs/drc-exclusions.md` and `docs/erc-exclusions.md`, and note that the project now
requires only KiCad 10 plus the perigoso keyswitch library from PCM.

- [ ] **Step 7: Clean up and commit**

```bash
rm -rf /tmp/rk-clone
cd /Users/dveremeev/projects/radio-86rk
git add README.md docs verify
git commit -m "Document the modernization outcome and verify a fresh clone

Cloned into a scratch directory and re-ran the gerber gate, the rule report
and the render there, so the result does not depend on anything in the
working tree - notably not on the sibling my_kicad_library checkout that
the project used to require.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

## Task Dependency Summary

```
1  harness + baseline                   OUTSTANDING
2  format upgrade         (needs 1)     schematics DONE 2a7788a; board OUTSTANDING
3  vendor footprints      (needs 2)     DRC 91 -> 22, ERC -> 34   (rehearsed, exact)
4  3D passives            (needs 3)     3D  0 -> 76
5  3D DIP sockets         (needs 4)     3D 76 -> 100
6  3D connectors/misc     (needs 4)     3D 100 -> 115
7  3D keyboard            (needs 4)     3D 115 -> 183
8  refresh symbols, ERC   (needs 2)     ERC 243 -> 101 DONE 9d8e182 + 16a7755;
                                        labels + vendored lib OUTSTANDING
9  DRC exclusions         (needs 3)     DRC 22 documented
10 standalone proof       (needs all)
```

Tasks 4–7 are independent of each other and may be reordered, as may 8–9. Task 8 was
executed ahead of Task 3 without harm — it is schematic-only, so it has no dependency on
the footprint vendoring.

**Order note:** Task 1 is now partly retrospective. The harness it builds
(`gerber_canon.py`, `netlist-gate.sh`, `rules-report.sh`) was written and validated during
planning, and the v1.4 gerber baseline has been captured; what remains is committing those
into `tools/` and `verify/`. Do that before Task 2's board conversion, which is the first
outstanding step that can move copper.

**No task changes copper.** `tools/gerber-gate.sh --strict` must pass on every one of them,
with no reviewed exception and no prototype measurement anywhere in the plan. That is a
direct consequence of Finding 1: once the switches keep their own footprints, nothing on
the board moves, and the Definition of Done becomes an unconditional empty gerber diff
against skiselev's v1.4.

The riskiest remaining task is 8, because refreshing a symbol whose pins were renumbered
would move nets to different pads. `tools/netlist-gate.sh` exists for exactly that, and it
is the only place in the plan where a silent netlist change is possible.

# Radio-86RK KiCad 10 Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Radio-86RK project to full KiCad 10 compatibility and a complete 3D render of every populated component, without moving a single copper feature.

**Architecture:** The board is the authoritative geometry source. All 191 footprint instances are extracted into a project-local library (`Radio86RK.pretty`), guaranteeing pad-for-pad identity by construction; 3D models are then attached to the 35 *unique* footprint definitions rather than to the 191 instances. Every change is gated by a gerber+drill diff against a baseline captured from `master` before any edit. The one authorized copper change is the keyboard, done last.

**Tech Stack:** KiCad 10.0.4; `kicad-cli` for export/DRC/ERC/render; KiCad's bundled Python 3.9 with the `pcbnew` SWIG bindings for scripted board and library edits; plain POSIX shell for the verification harness; git for per-task commits.

## Global Constraints

Every task's requirements implicitly include this section.

- **KiCad version floor:** 10.0.4. All file formats end at board `version 20260206`.
- **Copper is frozen.** No pad, track, via, zone or drill hole may move. The gerber+drill gate is binary and must pass on every task except Task 9.
- **From scratch only.** No commit, footprint, symbol, model, library table or configuration is taken from `migrate2kicad10`, `sw3-official-reroute-experiment`, or any other branch. Findings from earlier attempts may inform the work only as facts independently re-verified against `master`.
- **No absolute paths in committed files.** Every library and model URI uses `${KIPRJMOD}`, `${KICAD10_3DMODEL_DIR}` or `${KICAD10_3RD_PARTY}`.
- **Public reuse policy, by layer:** 3D models — aggressive. Symbols — where pin-compatible. Footprints — only the Cherry MX exception, and only where pad-for-pad identical apart from the documented name swap.
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

## Findings That Amend the Spec

These were measured while writing this plan and change what the spec assumed. Each is
handled by the task named.

1. **`CHERRY_PCB_225H` and `CHERRY_PCB_625H` carry stabilizer holes that perigoso does not.**
   The board's 2.25u has 4 extra NPTH (±11.938, +8.255 @ ⌀3.9878; ±11.938, −6.985 @ ⌀3.048);
   the 6.25u has 4 (±50.038, −8.255 @ ⌀3.9878; ±50.038, +6.985 @ ⌀3.048). perigoso's
   `SW_Cherry_MX_PCB_2.25u` / `_6.25u` have only the standard 5 pads. Adopting them would
   **delete 8 drill holes**. → Task 9 adopts perigoso for 65 switches only; SW11 and SW64
   stay vendored. 1.00u/1.25u/1.50u have exactly 5 pads and are unaffected.
2. **Gerbers embed net names.** `%TO.N,<netname>*%` appears 1155 times in `F_Cu` alone, so a
   net rename changes gerber bytes without moving copper. → Task 1 builds two gate modes.
3. **The project is in KiCad 6 format with CRLF endings.** The first save rewrites all
   173,936 lines. → Task 2 does that once, in isolation, gated.
4. **3D models attach to 35 footprint definitions, not 191 instances.** → Tasks 4–6 are 35
   assignments, not 191.
5. **U27 is `Transistor_TO92_EBC_254`, not a 3-pin regulator.** The spec's §3 text is wrong;
   its socket table (which excludes U25/U26/U27) is right. → Task 4 gives it a TO-92 model.
6. **F1 (a fuse) uses `Cap_Cer_508`.** Because models attach to footprints, F1 necessarily
   inherits the disc-capacitor model. Accepted per the 3D tolerance policy; recorded in
   `docs/3d-model-sources.md`.
7. **KiCad ships no RCA and no 8-pin DIN model.** → Task 6 sources or records fallbacks.

## File Structure

| Path | Responsibility |
|---|---|
| `tools/kicad-env.sh` | Single source of truth for tool paths. Sourced by every other script. |
| `tools/gerber-gate.sh` | Export gerbers+drill, normalize, diff vs baseline. Two modes. |
| `tools/netlist-gate.sh` | Export the netlist, diff vs baseline. Proves no pin was renumbered. |
| `tools/rules-report.sh` | Run ERC + DRC, print violation counts by type. |
| `tools/render.sh` | Render the board to PNG for the visual record. |
| `tools/vendor_footprints.py` | Extract the 35 unique footprints from the board into `Radio86RK.pretty`. |
| `tools/apply_models.py` | Apply `models.tsv` to both the library and the board instances. |
| `tools/models.tsv` | Data: footprint name → 3D model path → Z offset. Grows across Tasks 4–6 and 9. |
| `tools/switch_net_map.py` | Dump every switch pad as REF/PAD/NET/X/Y. The keyboard correctness proof. |
| `verify/baseline/` | Frozen normalized gerbers+drill from `master`. Committed. |
| `verify/renders/` | Per-task PNG renders. Committed. |
| `KiCad/Radio86RK.pretty/` | Tier 2: the 35 vendored footprints. |
| `KiCad/Radio86RK.kicad_sym` | Tier 2: the `my_components` symbols, plus the pin-swapped switch symbol. |
| `KiCad/Radio86RK.3dshapes/` | Externally sourced models (RCA, DIN-8, DC-DC) if obtained. |
| `KiCad/fp-lib-table`, `KiCad/sym-lib-table` | Project-local library registration. |
| `docs/3d-model-sources.md` | Why each model was chosen; every substitution and fallback. |
| `docs/drc-exclusions.md` | Written reason for each retained DRC violation. |
| `docs/erc-exclusions.md` | Written reason for each retained ERC violation (the RS-232 defect). |
| `docs/keyboard-slice.md` | The one copper change: what moved, and the prototype measurements. |
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

- [ ] **Step 3: Write `tools/gerber-gate.sh`**

The normalizer strips exactly the four line shapes that carry a generation timestamp, all
verified present in real output. `--geometry` additionally strips X2 net/component
attributes, for tasks that legitimately rename nets.

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
  if [ "$MODE" = "geometry" ]; then
    grep -vE "$STAMP" "$f" | grep -vE '^%T[OA]\.|^G04 #@! T[OA]\.' > "$out"
  else
    grep -vE "$STAMP" "$f" > "$out"
  fi
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

- [ ] **Step 4: Write `tools/rules-report.sh`**

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

- [ ] **Step 5: Write `tools/render.sh`**

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

- [ ] **Step 6: Make the scripts executable and ignore build output**

```bash
cd /Users/dveremeev/projects/radio-86rk
chmod +x tools/*.sh
printf '.build/\n.DS_Store\nKiCad/.history/\nKiCad/*.kicad_prl\nKiCad/*.lck\n' >> .gitignore
```

- [ ] **Step 7: Prove the gate works — capture the baseline, then run it unchanged**

This is the failing-test-first moment: a gate that cannot pass on an untouched board is
worthless, and a gate that cannot fail is equally worthless.

```bash
tools/gerber-gate.sh --strict   --capture
tools/gerber-gate.sh --geometry --capture
tools/gerber-gate.sh --strict
tools/gerber-gate.sh --geometry
```

Expected: two `captured` lines, then two `PASS` lines.

- [ ] **Step 8: Prove the gate can fail**

```bash
# Perturb one pad by 1 micron in a scratch copy, confirm the gate catches it.
cp KiCad/Radio-86RK.kicad_pcb /tmp/pcb-backup.kicad_pcb
perl -0pi -e 's/\(at 247\.65 8\.89\)/(at 247.651 8.89)/' KiCad/Radio-86RK.kicad_pcb
tools/gerber-gate.sh --strict || echo "GATE CORRECTLY DETECTED THE CHANGE"
cp /tmp/pcb-backup.kicad_pcb KiCad/Radio-86RK.kicad_pcb
tools/gerber-gate.sh --strict
```

Expected: `FAIL` + a diff + the confirmation line, then `PASS` after restore.

- [ ] **Step 9: Record the starting rule counts**

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

- [ ] **Step 10: Commit**

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

The board is KiCad 6 format (`20211014`) with CRLF endings; the schematics are `20211123`.
Any later edit would be against a legacy format that KiCad rewrites wholesale on first
save, burying real changes in a 173,936-line reformat. Do the reformat once, alone, and
prove it moved nothing.

**Files:**
- Modify: `KiCad/Radio-86RK.kicad_pcb`, all five `KiCad/*.kicad_sch`

**Interfaces:**
- Consumes: `tools/gerber-gate.sh`, `tools/rules-report.sh` from Task 1.
- Produces: board at format `20260206`; no API surface.

- [ ] **Step 1: Record the pre-upgrade format versions**

```bash
head -1 KiCad/Radio-86RK.kicad_pcb
head -1 KiCad/Radio-86RK.kicad_sch
```

Expected: `(kicad_pcb (version 20211014) (generator pcbnew)` and
`(kicad_sch (version 20211123) (generator eeschema)`.

- [ ] **Step 2: Confirm the gate passes before touching anything**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`.

- [ ] **Step 3: Upgrade the schematic and the board**

```bash
source tools/kicad-env.sh
"$KICAD_CLI" sch upgrade "$SCH"
"$KICAD_CLI" pcb upgrade "$PCB"
```

- [ ] **Step 4: Verify the format actually changed**

```bash
head -3 KiCad/Radio-86RK.kicad_pcb
grep -c $'\r' KiCad/Radio-86RK.kicad_pcb || echo "CRLF gone (grep found none)"
```

Expected: `(kicad_pcb` with `(version 20260206)`, and zero CRLF lines.

- [ ] **Step 5: Run the gate — this is the whole point of the task**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`. A reformat that changes one coordinate is a KiCad bug or a wrong
command; if this fails, `git checkout -- KiCad/` and stop.

- [ ] **Step 6: Record rule counts (expect no change)**

```bash
tools/rules-report.sh | tee verify/rules-01-format-upgrade.txt
diff verify/rules-00-baseline.txt verify/rules-01-format-upgrade.txt && echo "rule counts unchanged"
```

- [ ] **Step 7: Commit**

```bash
git add KiCad verify
git commit -m "Upgrade board and schematics from KiCad 6 to KiCad 10 file format

Board 20211014 -> 20260206, schematics 20211123 -> current, CRLF -> LF.
A pure reformat: every line of the board file changes and the gerber gate
passes byte-identical, so no copper moved. Isolated in its own commit so
later diffs stay readable.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 3: Vendor the 35 footprints and make the project self-contained

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

- [ ] **Step 7: Run the gate — the board was not edited, so this must pass trivially**

```bash
tools/gerber-gate.sh --strict
```

Expected: `PASS`.

- [ ] **Step 8: Confirm the rule counts moved as predicted**

```bash
tools/rules-report.sh | tee verify/rules-03-vendored.txt
```

Expected: `DRC 22` — the 67 `lib_footprint_issues` and both `lib_footprint_mismatch` are
gone, leaving exactly the 17 `silk_edge_clearance` + 5 `starved_thermal` inherited from
v1.4. `ERC 176` — the 67 `footprint_link_issues` are gone, leaving 142
`lib_symbol_mismatch` + 32 `same_local_global_label` + 2 `lib_symbol_issues`.

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

TSV columns: footprint_name <TAB> model_path <TAB> z_offset_mm
Multiple rows per footprint are applied in order (used for socket+chip composites).
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
    wanted.setdefault(name, [])
    if path != "-":
        wanted[name].append((path, float(z)))

def set_models(fp, entries):
    fp.Models().clear()
    for path, z in entries:
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        m.m_Offset   = pcbnew.VECTOR3D(0, 0, z)
        m.m_Scale    = pcbnew.VECTOR3D(1, 1, 1)
        m.m_Rotation = pcbnew.VECTOR3D(0, 0, 0)
        m.m_Show     = True
        fp.Models().push_back(m)

io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

# 1. the library
for name, entries in wanted.items():
    fp = pcbnew.FootprintLoad(LIB, name)
    if fp is None:
        sys.exit("ERROR: %s not found in %s" % (name, LIB))
    set_models(fp, entries)
    io.FootprintSave(LIB, fp)

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
```

- [ ] **Step 2: Write `tools/models.tsv` (passives)**

Columns are tab-separated. `${KICAD10_3DMODEL_DIR}` keeps the paths portable.

```
# footprint	model	z_offset_mm
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

3D coverage 100/183 -> 115/183; the remaining 68 are the switches.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```

---

### Task 7: Re-home the drifted symbols to public libraries and drive ERC down

176 ERC violations remain: 142 `lib_symbol_mismatch`, 32 `same_local_global_label`,
2 `lib_symbol_issues`.

**Every one of these resolves through public reuse — nothing needs vendoring.** The
mismatching symbols are *KiCad's own* stock symbols that drifted between KiCad 4 and
KiCad 10 (power flags, 74xx logic, `Device:D`/`LED`), not the lost `my_components` library.
And the single genuinely-missing symbol, `Device:Q_NPN_EBC`, was not deleted — it moved to
`Transistor_BJT.kicad_sym`, where it still exists under the same name.

This is the best possible outcome against the goal of reusing public components: the
schematic ends up pointing at current, maintained, upstream KiCad symbols.

**The risk this task must control** is a pin renumbering. Refreshing a symbol from a library
whose pins have been renumbered would move nets to different pads — the same failure the
Cherry MX analysis identified, arriving from the symbol side. The gerber gate cannot see it
(the board is not edited here), so this task adds a **netlist gate**: export the netlist
before and after, and require it to be identical.

> **Spec amendment — ERC cannot honestly reach 0.**
> The spec's Definition of Done says ERC → 0, and its Out of Scope says the U3/U22 RS-232
> wiring defect (GitHub issue #2) stays unfixed. These conflict: the `lib_symbol_issues`
> currently suppress KiCad's pin-connectivity checks project-wide, so resolving the symbol
> links is exactly what makes that defect visible. The spec warns that `migrate2kicad10`
> reached "ERC 0" by converting local labels to global, giving those pins a driver and
> silencing the check without moving a wire.
> **Revised target: ERC 0 apart from the issue-#2 violations, which get ERC exclusions with
> a written reason**, exactly parallel to the DRC exclusions in Task 8.
>
> Note that the label promotion in Step 8 is *not* that masking manoeuvre: all 32
> collisions are address, data and control bus signals, none of them the RS-232 receiver
> pins the defect concerns.

**Files:**
- Create: `tools/netlist-gate.sh`
- Modify: `KiCad/sym-lib-table`, `KiCad/*.kicad_sch`, `KiCad/Radio-86RK.kicad_pro`
- Create: `docs/erc-exclusions.md`

**Interfaces:**
- Consumes: `tools/kicad-env.sh`, `tools/rules-report.sh`, `tools/gerber-gate.sh`.
- Produces: `tools/netlist-gate.sh [--capture]` — exit 0 if the netlist matches
  `verify/baseline/netlist.net`, 1 otherwise. Used again by Task 9.

- [ ] **Step 1: Write `tools/netlist-gate.sh`**

The netlist is the ground truth linking schematic to copper: if it is unchanged, no symbol
edit can have moved a net to a different pad.

```bash
#!/usr/bin/env bash
# Export the netlist and diff it against verify/baseline/netlist.net.
#   --capture   write the baseline instead of comparing
set -euo pipefail
source "$(dirname "$0")/kicad-env.sh"
mkdir -p "$BUILD" "$REPO_ROOT/verify/baseline"
BASE="$REPO_ROOT/verify/baseline/netlist.net"
CUR="$BUILD/netlist.net"

"$KICAD_CLI" sch export netlist --format kicadsexpr --output "$CUR.raw" "$SCH" >/dev/null
# Drop the generation date and tool version headers; keep every component and net.
grep -vE '^\s*\(date |^\s*\(tool ' "$CUR.raw" > "$CUR"

if [ "${1:-}" = "--capture" ]; then
  cp "$CUR" "$BASE"; echo "netlist-gate: captured baseline ($(wc -l < "$BASE" | tr -d ' ') lines)"; exit 0
fi
[ -f "$BASE" ] || { echo "netlist-gate: no baseline; run --capture" >&2; exit 2; }
if diff -q "$BASE" "$CUR" >/dev/null; then
  echo "netlist-gate: PASS - every pin maps to the same net"
else
  echo "netlist-gate: FAIL"; diff -u "$BASE" "$CUR" | head -60; exit 1
fi
```

- [ ] **Step 2: Capture the netlist baseline and prove the gate works**

```bash
chmod +x tools/netlist-gate.sh
tools/netlist-gate.sh --capture
tools/netlist-gate.sh
```

Expected: a `captured baseline` line, then `PASS`.

- [ ] **Step 3: Confirm the 16 drifted symbols and the one that moved**

```bash
source tools/kicad-env.sh
tools/rules-report.sh > /dev/null
tr ',' '\n' < .build/erc.json | grep -oE "Symbol '[^']+' (doesn't match copy in|not found in symbol) library '[^']+'" | sort -u
```

Expected exactly these — 15 that drifted plus one that moved:

| Library | Symbols |
|---|---|
| `power` | `+12V`, `-12V`, `-5V`, `GND`, `VCC`, `PWR_FLAG` |
| `74xx` | `74LS00`, `74LS08`, `74LS74`, `74LS86` |
| `Device` | `D`, `LED` |
| `Connector` | `Barrel_Jack_Switch`, `Conn_Coaxial` |
| `Graphic` | `Logo_Open_Hardware_Small` |
| `Device` → **moved** | `Q_NPN_EBC` — *not found*; now lives in `Transistor_BJT` |

`Q_NPN_EBC` accounts for both `lib_symbol_issues`, one each for Q1 and Q2.

- [ ] **Step 4: Verify the moved symbol before relying on it**

```bash
SL=/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols
grep -c 'symbol "Q_NPN_EBC"' $SL/Device.kicad_sym || echo "absent from Device (expected)"
grep -c 'symbol "Q_NPN_EBC"' $SL/Transistor_BJT.kicad_sym
```

Expected: absent from `Device`, present in `Transistor_BJT`. The name is unchanged, so the
E-B-C pin order that `Transistor_TO92_EBC_254` depends on is preserved — and Step 7 proves
it rather than assuming it.

- [ ] **Step 5: Write `KiCad/sym-lib-table`**

This replaces the sibling-clone table written on 2026-09-04. `my_components` is the only
project-local symbol library still needed; it is registered against a vendored copy so a
fresh clone works, while every other symbol comes from KiCad's stock libraries.

```
(sym_lib_table
	(version 7)
	(lib (name "my_components")(type "KiCad")(uri "${KIPRJMOD}/Radio86RK.kicad_sym")(options "")(descr "skiselev/my_kicad_library symbols used by this project, vendored"))
)
```

Create `KiCad/Radio86RK.kicad_sym` by copying only the symbols this project actually uses
out of the sibling clone at `../my_kicad_library/library/my_components.kicad_sym`:

```bash
grep -oh 'lib_id "my_components:[^"]*"' KiCad/*.kicad_sch | sort -u
```

Copy each named symbol into `KiCad/Radio86RK.kicad_sym`, then validate:

```bash
source tools/kicad-env.sh
"$KICAD_CLI" sym upgrade KiCad/Radio86RK.kicad_sym
"$KICAD_CLI" sym export svg --output .build/symcheck KiCad/Radio86RK.kicad_sym >/dev/null \
  && echo "symbol library parses and renders"
```

- [ ] **Step 6: Capture the Footprint properties before touching anything**

A known KiCad footgun: symbol relink operations can reset a symbol's `Footprint` property
to the library default, silently destroying real footprint assignments. Capture the mapping
now so Step 9 can prove nothing was lost.

```bash
grep -h -A1 '"Footprint"' KiCad/*.kicad_sch \
  | grep -oE '"(My_Components|Cherry_MX|Symbol):[^"]*"' \
  | sort | uniq -c | sort -rn > verify/footprint-props-before.txt
cat verify/footprint-props-before.txt
```

- [ ] **Step 7: Re-home Q1 and Q2, then refresh the 15 drifted symbols**

First the move — a pure `lib_id` change, two occurrences:

```bash
sed -i '' 's|lib_id "Device:Q_NPN_EBC"|lib_id "Transistor_BJT:Q_NPN_EBC"|g' KiCad/*.kicad_sch
grep -c 'Transistor_BJT:Q_NPN_EBC' KiCad/*.kicad_sch | grep -v ':0'
```

Expected: two occurrences, in whichever sheet holds Q1 and Q2.

Then, in Eeschema, run **Tools → Update Symbols from Library…**, select all, and apply.
This rewrites the embedded `lib_symbols` cache from the current stock libraries.

- [ ] **Step 8: Run the netlist gate — the whole safety argument for this task**

```bash
tools/netlist-gate.sh
```

Expected: `PASS`. **A failure means a symbol's pins were renumbered and nets have moved to
different pads.** Revert immediately (`git checkout -- KiCad/`) and re-home that symbol by
hand, or vendor the cached version for it alone, before continuing.

- [ ] **Step 9: Prove no Footprint property was clobbered**

```bash
grep -h -A1 '"Footprint"' KiCad/*.kicad_sch \
  | grep -oE '"(My_Components|Cherry_MX|Symbol):[^"]*"' \
  | sort | uniq -c | sort -rn > verify/footprint-props-after.txt
diff verify/footprint-props-before.txt verify/footprint-props-after.txt \
  && echo "all footprint assignments intact"
```

Expected: `all footprint assignments intact`. Any difference means a symbol lost its
footprint — restore and investigate before continuing.

- [ ] **Step 10: Resolve the 32 `same_local_global_label` collisions**

All 32 are bus and control signals that carry both a local and a global label of the same
name — 15 address lines `A0`–`A14`, 8 data lines `D0`–`D7`, the four strobes `~{RD}`,
`~{WR}`, `~{IOR}`, `~{MEMW}`, and `OSC`, `RESET`, `TTL_CLK`, `SPKR_ENA`, `PIT2_ENA`.

In an 8080-family design these are genuinely one net each, so the correct fix is to **delete
the redundant local label** and let the global one name the net. That changes no net name,
so both the netlist and the gerber `%TO.N` records are untouched.

None of these are the RS-232 receiver signals on U3/U22, so this is not the masking
manoeuvre the spec warns about. **Do not add or promote any label on U3 or U22.**

- [ ] **Step 11: Run all three gates**

```bash
tools/netlist-gate.sh
tools/gerber-gate.sh --geometry
tools/gerber-gate.sh --strict
```

Expected: all three `PASS`. Because the fix removed duplicate labels rather than renaming
nets, even `--strict` should pass. If `--strict` fails, inspect the diff: every changed
line must be a `%TO.N` net-name record and nothing else, and the net names must be ones
you deliberately changed.

- [ ] **Step 12: Re-run ERC**

```bash
tools/rules-report.sh | tee verify/rules-07-symbols.txt
```

Expected: `lib_symbol_mismatch`, `lib_symbol_issues` and `same_local_global_label` all
gone. New `pin_not_driven` / `pin_not_connected` / `unconnected_wire_endpoint` violations
on **U3 and U22** may now appear — that is issue #2 becoming visible for the first time,
which is the correct outcome, not a regression.

- [ ] **Step 13: Write `docs/erc-exclusions.md` and exclude the issue-#2 violations**

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
collisions resolved in this task are address, data and control bus signals only; no label
on U3 or U22 was touched.

Each violation is excluded with this reason so a future reader sees a deliberate decision.
```

Add the exclusions in Eeschema (right-click the violation → **Exclude with comment**), or
under `erc.exclusions` in `KiCad/Radio-86RK.kicad_pro`.

- [ ] **Step 14: Commit**

```bash
git add KiCad tools/netlist-gate.sh docs/erc-exclusions.md verify
git commit -m "Re-home drifted symbols to public KiCad libraries; ERC 176 -> issue #2 only

Every mismatching symbol turned out to be one of KiCad's own stock symbols
that drifted since KiCad 4 - power flags, 74xx logic, Device:D/LED - not the
lost my_components library. And Device:Q_NPN_EBC was not deleted, it moved to
Transistor_BJT. So all 144 symbol violations resolve through public reuse
with nothing vendored, which is the best available outcome against the goal.

Added tools/netlist-gate.sh: refreshing a symbol whose pins were renumbered
would move nets to different pads, and the gerber gate cannot see that
because the board is not edited here. The netlist is identical before and
after, so no pin moved.

The 32 same_local_global_label collisions are all address/data/control bus
signals; resolved by deleting the redundant local labels, which changes no
net name. No label on U3 or U22 was touched, so the pre-existing RS-232
wiring defect stays visible and is excluded with a written reason.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J23USKeTkpPgzY5ddJr5TY"
```
### Task 8: Document the retained DRC violations as exclusions

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

Anything the keyboard slice (Task 9) adds is documented separately in that task, and only
after the physical prototype confirms clearance.
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

### Task 9: The keyboard — the one authorized copper change

This is the only task permitted to change the fab output, and the only one whose gate is
reviewed rather than required to pass. Do it last, on a clean tree, with every other task
committed.

**What changes and what does not.** 62 × 1.00u, 2 × 1.25u and 1 × 1.50u switches adopt the
public perigoso footprint — **65 in total**. SW11 (2.25u) and SW64 (6.25u) **keep their
vendored footprints**, because the board's `CHERRY_PCB_225H` and `_625H` carry four
stabilizer holes each that perigoso's equivalents do not have; adopting them would delete
8 drill holes. They get the perigoso 3D model without the footprint swap. SW68 is a tactile
switch and only needs a model.

**Why the pin swap is mandatory.** KiCad binds nets to pads by *name*. The board has pad 1
at (2.54, −5.08) and pad 2 at (−3.81, −2.54); perigoso has them the other way round. The
positions are identical — only the names are exchanged — so adopting perigoso without a
compensating swap moves every net to the opposite hole while the copper stays put, shorting
the keyboard matrix. The swap is applied **in the schematic**, as a project-local symbol
with pin numbers exchanged, so the perigoso footprint is used unmodified. A board footprint
that diverges from its library reverts silently on any future "Update Footprints from
Library"; a project-local symbol does not.

The switch is not polarized, so exchanging its two pin numbers is electrically free.

**Files:**
- Modify: `KiCad/fp-lib-table`, `KiCad/Radio86RK.kicad_sym`, `KiCad/Radio-86RK-Keyboard.kicad_sch`
- Modify: `KiCad/Radio-86RK.kicad_pcb`, `tools/models.tsv`, `docs/3d-model-sources.md`
- Create: `tools/switch_net_map.py`, `docs/keyboard-slice.md`

**Interfaces:**
- Consumes: `KiCad/Radio86RK.pretty`, `KiCad/Radio86RK.kicad_sym`, `tools/apply_models.py`.
- Produces: `tools/switch_net_map.py <board>` — prints `REF PAD NET X Y` for every switch
  pad, sorted. This is the correctness proof for the whole task.

- [ ] **Step 1: Write `tools/switch_net_map.py`**

```python
"""Dump every switch pad as REF PAD NET X Y in board coordinates.

Run before and after the relink: the two dumps must be IDENTICAL. Net names may only ever
be paired with the same absolute hole position.
"""
import sys, pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
rows = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if not ref.startswith("SW"):
        continue
    for pad in fp.Pads():
        name = pad.GetName()
        if not name:                      # skip the mechanical NPTH pads
            continue
        pos = pad.GetPosition()
        rows.append("%-6s %-3s %-24s %9.4f %9.4f"
                    % (ref, name, pad.GetNetname(),
                       pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)))
for r in sorted(rows):
    print(r)
```

- [ ] **Step 2: Capture the reference net-to-hole map**

```bash
source tools/kicad-env.sh
"$KICAD_PY" tools/switch_net_map.py "$PCB" > verify/switch-map-before.txt
wc -l verify/switch-map-before.txt
grep '^SW54' verify/switch-map-before.txt
```

Expected: 136 lines (68 switches × 2 electrical pads). SW54 shows pad 1 on
`/Keyboard/ROW6` and pad 2 on `/Keyboard/K_PB5`.

- [ ] **Step 3: Register the perigoso footprint library**

Append to `KiCad/fp-lib-table`, inside the closing paren:

```
	(lib (name "Switch_Keyboard_Cherry_MX")(type "KiCad")(uri "${KICAD10_3RD_PARTY}/footprints/com_github_perigoso_keyswitch-kicad-library/Switch_Keyboard_Cherry_MX.pretty")(options "")(descr "perigoso keyswitch library, installed via PCM"))
```

Verify it resolves:

```bash
source tools/kicad-env.sh
ls "$KICAD_3RD_PARTY/footprints/com_github_perigoso_keyswitch-kicad-library/Switch_Keyboard_Cherry_MX.pretty/" \
  | grep -E 'SW_Cherry_MX_PCB_1\.(00|25|50)u\.kicad_mod'
```

Expected: the three filenames.

- [ ] **Step 4: Confirm the pad-name swap is real before relying on it**

```bash
source tools/kicad-env.sh
P="$KICAD_3RD_PARTY/footprints/com_github_perigoso_keyswitch-kicad-library/Switch_Keyboard_Cherry_MX.pretty"
grep -E '^\s*\(pad [12] ' "$P/SW_Cherry_MX_PCB_1.00u.kicad_mod"
grep -E '\(pad "[12]"' KiCad/Radio86RK.pretty/CHERRY_PCB_100H.kicad_mod
```

Expected: perigoso pad 1 at `(-3.81 -2.54)`, pad 2 at `(2.54 -5.08)`; vendored pad "1" at
`(2.54 -5.08)`, pad "2" at `(-3.81 -2.54)`. Same two positions, names exchanged.

- [ ] **Step 5: Add the pin-swapped symbol to `KiCad/Radio86RK.kicad_sym`**

Copy the `SW_Push_45deg` symbol out of KiCad's stock `Switch.kicad_sym`, rename it to
`SW_Push_45deg_MX`, and exchange **only** the two `(number ...)` values — leave every
`(at ...)`, `(name ...)` and graphic untouched, so no wire endpoint moves.

Stock definition (verified): pin `(number "1")` at `(-2.54 2.54 0)`, pin `(number "2")` at
`(2.54 -2.54 180)`. After the swap, the pin at `(-2.54 2.54 0)` is number `2` and the pin
at `(2.54 -2.54 180)` is number `1`.

```bash
source tools/kicad-env.sh
"$KICAD_CLI" sym export svg --output .build/symcheck KiCad/Radio86RK.kicad_sym >/dev/null \
  && echo "library still parses"
```

- [ ] **Step 6: Relink the 65 switches in the schematic**

In `KiCad/Radio-86RK-Keyboard.kicad_sch`, for every switch **except SW11 and SW64**:

- `(lib_id "Switch:SW_Push_45deg")` → `(lib_id "Radio86RK:SW_Push_45deg_MX")`
- the `Footprint` property value → `"Switch_Keyboard_Cherry_MX:SW_Cherry_MX_PCB_1.00u"`
  (or `_1.25u` for SW65/SW66, `_1.50u` for SW61)

SW11 and SW64 keep `Switch:SW_Push_45deg` and their `Cherry_MX:CHERRY_PCB_225H` /
`_625H` footprints — no swap, because their footprint is not changing.

```bash
grep -c 'Radio86RK:SW_Push_45deg_MX' KiCad/Radio-86RK-Keyboard.kicad_sch
grep -c 'SW_Cherry_MX_PCB_1.00u' KiCad/Radio-86RK-Keyboard.kicad_sch
```

Expected: `65` and `62`.

- [ ] **Step 7: Update the board from the schematic**

Open the project in Pcbnew and run **Tools → Update PCB from Schematic** with
"Update footprints" enabled and "Delete extra footprints" disabled. Save.

- [ ] **Step 8: THE CRITICAL CHECK — every net must still be in its original hole**

```bash
source tools/kicad-env.sh
"$KICAD_PY" tools/switch_net_map.py "$PCB" > verify/switch-map-after.txt
diff verify/switch-map-before.txt verify/switch-map-after.txt \
  && echo "PASS: every net is in the same physical hole"
```

Expected: `PASS`. **Any difference means the pin swap is wrong and the keyboard matrix is
shorted.** Revert the whole task and re-check Step 5 before doing anything else.

- [ ] **Step 9: Confirm the board is still electrically whole**

```bash
tools/rules-report.sh | tee verify/rules-09-keyboard.txt
```

Expected: `unconnected=0` and `parity=0`. New `clearance` or `shorting_items` violations
mean the larger 2.5 mm pads now conflict with adjacent copper — that is the physical
question Step 11 answers, not a reason to stop here.

- [ ] **Step 10: Review the gerber diff feature by feature**

This is the one place the gate is expected to fail. Read the diff rather than accepting it.

```bash
tools/gerber-gate.sh --strict || true
```

Expected changes, and nothing else:
- **Drill:** switch pad holes 1.4986 mm → 1.5 mm (+1.4 µm, 65 switches × 2).
- **Copper:** switch pad annular rings 2.286 mm → 2.5 mm (+0.214 mm diameter).
- **Silkscreen / courtyard / user layers:** perigoso's outlines replace the originals.
  The vendored footprint puts pads on `*.SilkS`; perigoso does not.
- **Unchanged:** every pad *position*, every track, every via, every zone, and all 8
  stabilizer holes on SW11 and SW64.

Verify the stabilizers explicitly, since losing them is the failure mode this task was
restructured to avoid:

```bash
grep -cE '11\.938|50\.038' KiCad/Radio-86RK.kicad_pcb
```

Expected: `8`.

- [ ] **Step 11: Verify clearance on the physical prototype**

The pads grew by 0.214 mm in diameter — 0.107 mm of extra radius. Measure the tightest
switch-pad-to-adjacent-copper gaps on the real board before accepting any DRC exclusion.
**Measurement precedes exclusion, never the reverse.** If the clearance is genuinely
insufficient, stop and reconsider: keeping the vendored footprint for the affected
switches is always available and costs only the 3D model, which can be attached to the
vendored footprint anyway.

- [ ] **Step 12: Add the switch 3D models**

```
# --- Keyboard ---
CHERRY_PCB_225H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/SW_Cherry_MX_PCB.stp	0
CHERRY_PCB_625H	${KICAD10_3RD_PARTY}/3dmodels/com_github_perigoso_keyswitch-kicad-library/3d-library.3dshapes/SW_Cherry_MX_PCB.stp	0
Switch_Tactile_6mm_Right	${KICAD10_3DMODEL_DIR}/Button_Switch_THT.3dshapes/SW_Tactile_SPST_Angled_PTS645Vx31-2LFS.step	0
```

The 65 relinked switches inherit their model from the perigoso footprint itself, which
already references `SW_Cherry_MX_PCB.wrl`. Only the two vendored wide keys and the tactile
switch need explicit rows.

```bash
"$KICAD_PY" tools/apply_models.py tools/models.tsv "$PCB" "$REPO_ROOT/KiCad/Radio86RK.pretty"
```

- [ ] **Step 13: Confirm full 3D coverage**

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
sourced) — i.e. 183/183 coverage of components that should have one.

- [ ] **Step 14: Render the finished board**

```bash
tools/render.sh 09-keyboard-complete
```

Expected: all 68 keys present with keycap-less switch bodies, alongside every IC in its
socket and every connector.

- [ ] **Step 15: Re-baseline and document**

```bash
tools/gerber-gate.sh --strict   --capture
tools/gerber-gate.sh --geometry --capture
```

Write `docs/keyboard-slice.md` recording: the 65/2/1 split and why SW11 and SW64 were
excluded; the pad and drill deltas; the prototype measurements from Step 11; and any DRC
exclusions those measurements justify.

- [ ] **Step 16: Commit**

```bash
git add KiCad tools docs verify
git commit -m "Adopt the public Cherry MX footprint for 65 switches, with the pin swap

The only authorized copper change. 62x1.00u, 2x1.25u and 1x1.50u switches
move to perigoso's SW_Cherry_MX_PCB_*u; pads grow 2.286 -> 2.5mm and drills
1.4986 -> 1.5mm, while every pad position is unchanged.

SW11 (2.25u) and SW64 (6.25u) keep their vendored footprints: the board's
CHERRY_PCB_225H/625H carry four stabilizer holes each that perigoso's
equivalents lack, so adopting them would delete 8 drills.

The pin swap is applied in the schematic via a project-local
SW_Push_45deg_MX symbol with pin numbers exchanged, leaving the perigoso
footprint unmodified. tools/switch_net_map.py proves every net stayed in
its original physical hole.

3D coverage now 183/183.

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

Expected: `PASS`, and rule counts matching `verify/rules-09-keyboard.txt` from Task 9. A
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
| Gerber diff vs v1.4 | — | empty outside the keyboard slice |

## What changed on the board

Exactly one thing: 65 of 68 keyswitches adopted the public perigoso Cherry MX footprint,
growing their pads from 2.286 mm to 2.5 mm and their drills from 1.4986 mm to 1.5 mm. Pad
positions did not move, and a compensating pin swap in the schematic kept every net in its
original physical hole. SW11 and SW64 were deliberately left on the vendored footprints to
preserve their stabilizer holes.

Everything else — all 191 footprints, all copper, all drills — is byte-identical to
skiselev's v1.4 output.

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
1 harness+baseline
2 format upgrade          (needs 1)
3 vendor footprints       (needs 2)   DRC 91 -> 22, ERC 243 -> 176
4 3D passives             (needs 3)   3D  0 -> 76
5 3D DIP sockets          (needs 4)   3D 76 -> 100
6 3D connectors/misc      (needs 4)   3D 100 -> 115
7 re-home symbols, ERC   (needs 3)   ERC 176 -> issue-#2 only
8 DRC exclusions          (needs 3)   DRC 22 documented
9 keyboard                (needs 3,7) 3D 115 -> 183, the one copper change
10 standalone proof       (needs all)
```

Tasks 4–6 and 7–8 are independent of each other and may be reordered. Task 9 goes last
because it is the only task whose gate is reviewed rather than required to pass, and it
should run against an otherwise finished tree.

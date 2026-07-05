# My_Components Footprint Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve every remaining component in the Radio-86RK KiCad project that references the unresolved `My_Components` footprint library nickname, by relinking each to a verified official (or, where none exists, project-local custom) footprint — validated against the real ordered part, not just the closest-sounding name.

**Architecture:** This is a hardware (KiCad) project, not software — there is no compiler or test runner. Each task follows the same repeatable verification loop established and proven on the resistors (commit `5dabaf9`):
1. **Baseline ("red")** — confirm the current DRC `lib_footprint_issues` error for the affected references.
2. **Research** — pull the real part number from the README BOM, fetch its datasheet mechanical dimensions, and search official KiCad libraries for candidates.
3. **Report** — present a comparison table (project footprint vs. candidate vs. real part dimensions) and get explicit user go-ahead before touching any file — this is a hard checkpoint, not optional.
4. **Edit** — relink the schematic `Footprint` field via `mcp__kicad__batch_edit_schematic_components`.
5. **Forward-annotate** — user runs "Update PCB from Schematic" (F8) in the KiCad UI (the `sync_schematic_to_board` MCP tool has a known bug — see CLAUDE.md).
6. **Anchor-point correction (mandatory, do not skip)** — official KiCad THT footprints anchor at pad 1 `(0,0)`; every one of this project's original custom footprints anchors at the body center (pads symmetric about the origin). Swapping footprints without correcting for this silently shifts the component by roughly half the pin pitch — DRC does **not** flag it as an error on its own, but it breaks routed connections (`track_dangling`), zone fills (`starved_thermal`), and clearance (found live on the diode task: `track_dangling` 106→0, `hole_to_hole` 5→0, `isolated_copper` 6→0, `starved_thermal` 41→6 once corrected). For every reference just relinked: pull its pre-swap position/rotation/pad-1-local-offset from git history (`git show <prior-commit>:KiCad/Radio-86RK.kicad_pcb`) or from pad data captured before the edit, compute `new_position = old_position + Rot(old_rotation)*old_pad1_local_offset`, and check whether the new footprint's local pad1→pad2 vector has the same sign as the old one — if it's flipped (as it was for `Diode_762`, whose author placed pad 1 on the opposite side from every official footprint's convention), the rotation also needs a +180° correction. Apply via `mcp__kicad__move_component`, then re-verify pad positions match the pre-swap values exactly before proceeding. **Also check the new footprint's pad-arrangement axis, not just its sign** — found live on the JP1/JP2 task: every footprint up to that point arranged multi-pin pads along local X (`pad2 at (2.54, 0)`), but `PinHeader_1x04_P2.54mm_Vertical` arranges them along local Y (`pad2 at (0, 2.54)`) instead. Reusing the old rotation there turned a vertical header into a horizontal one. Before computing the rotation, read the new footprint's actual pad2 coordinates and confirm which axis it uses; multi-row or non-linear connectors (DIN, D-sub, IDC headers — Tasks 14-16) are likely candidates for this same axis mismatch, not just a sign flip.
7. **Verify ("green")** — reopen the project via `mcp__kicad__open_project` and confirm via `mcp__kicad__get_component_list` that the new footprint appears for exactly the expected references, and confirm the DRC error is gone.
8. **Human sign-off** — present the verification result to the user and wait for explicit approval before doing anything else. Automated verification passing is necessary but not sufficient.
9. **Commit** — only after Step 8's approval.

**Tech Stack:** KiCad 10, `kicad` MCP server (primary interface — see CLAUDE.md "Working with the schematic and PCB"), `kicad-cli` (headless fallback), README.md (BOM/Mouser part source of truth), WebSearch/WebFetch (manufacturer datasheets).

**IC socket vs. IC body — a physical distinction the footprint must represent:** The README BOM has separate line items for "IC Socket" (README.md:223-229, one per DIP pin count, each with its own Mouser P/N) distinct from the IC line items themselves. Physically, the socket is what's soldered to the board; the actual chip plugs into the socket and sits elevated above the PCB by the socket's stack height — it is not a single flat part. A plain swap to KiCad's official `Package_DIP:DIP-N_W*mm` footprint only carries a single IC-body 3D model sitting flush on the board, which is mechanically wrong for this project's stated FreeCAD case-design goal (established in the SW11/SW64 stabilizer work, commit `daacbd7`): the true stack height (PCB → socket → chip) matters for clearance under a case lid. The pad pattern itself is unaffected (a socketed DIP and a directly-soldered DIP share identical pin pitch/spacing), so this is purely a 3D-model-accuracy question, decided **once** in Task 23 and then applied identically across Tasks 24-29.

## Global Constraints

- Never hand-edit `.kicad_sch`/`.kicad_pcb` S-expression files directly — use the `kicad` MCP tools (CLAUDE.md).
- Never pick a "closest official footprint" by name/geometry alone — always resolve the real BOM part (README.md Bill of Materials table) and check its datasheet dimensions first. A project's own hand-drawn footprint is not guaranteed to be accurate (see the resistor case: the project's own silkscreen undersized the real part more than the official candidate did).
- Every footprint swap requires a comparison report presented to the user and explicit confirmation before any schematic edit is made. Do not batch multiple categories' edits into one unconfirmed pass.
- After every schematic edit, the PCB does not update until forward-annotated (F8 in the KiCad UI — the MCP `sync_schematic_to_board` tool is broken).
- One git commit per task, after the fix is verified on the PCB (not just the schematic) AND after the user has explicitly approved that verified state in the conversation. Never run `git commit` on the strength of automated verification (DRC/component-list checks) alone.
- Do not touch `My_Components:Hole_3mm`, connectors, or ICs before the simpler passive categories are done, per the required ordering below.
- Do not start the IC task group until every non-IC category is finished.
- **After every footprint swap, check for and correct the anchor-point shift (Architecture step 6) before verifying/committing.** This was missed on the first three completed tasks (resistors `5dabaf9`, ceramic caps `fdf01d1`, electrolytic caps `88d9543`) and had to be fixed retroactively via a dedicated correction pass — do not repeat that mistake on the remaining tasks.

## Required Task Ordering

1. Capacitors (ceramic, then electrolytic)
2. Diodes
3. Transistors
4. LEDs
5. Mounting holes
6. Connectors — one footprint at a time
7. Other/misc single-instance components (crystal, DC-DC converter, TO-220 regulator, speaker, tactile switch)
8. Integrated circuits (DIP footprints), last, one DIP pin-count at a time

This mirrors the user's explicit ordering request: simple passives first, connectors reviewed individually, "other" components before ICs, ICs last as the special/most complex case.

---

## Reference data (pulled from README.md BOM and the live PCB component survey — do not re-derive, just use)

| Footprint (My_Components:) | Count | Refs | BOM description | Mouser P/N |
|---|---|---|---|---|
| `Cap_Cer_508` | 39 | C1-C32, C39-C44, F1 | 0.1uF...10pF MLCC, 5mm pitch (various values) + Polyfuse 1.1A 5mm pitch | see per-value rows, README.md:160-167; F1: README.md:171 `576-16R110BU` |
| `Cap_Elec_Radial_6.3mm` | 6 | C33-C38 | 47uF 25V Electrolytic/Organic Polymer | README.md:161 `80-A750EK476M1EAAE40` |
| `Diode_762` | 9 | D1-D9 | 1N4148 | README.md:168 `512-1N4148` |
| `Transistor_TO92_EBC_254` | 3 | Q1, Q2, U27 | Q1/Q2: 2N3904 (README.md:181 `512-2N3904TA`); U27: DS1233-5 CPU Supervisory Circuit, also TO-92 (README.md:221 `700-DS1233-5T&R`) |
| `LED_3mm` | 2 | D10, D11 | LED Indicator 3mm Green/Yellow | README.md:169-170 `630-HLMP-1503-C0002`, `630-HLMP-1401` |
| `Hole_3mm` | 7 | HOLE1-HOLE7 | mechanical mounting holes, no BOM part | n/a |
| `Conn_SIL6` | 3 | RN2, RN3, RN4 | Resistor Array 4.7k SIP6 | README.md:191 `652-4606X-1LF-4.7K` |
| `Conn_SIL10` | 1 | RN1 | Resistor Array 10k SIP10 | README.md:190 `652-4610X-1LF-10K` |
| `Conn_Pin_Header_4x1_2.54mm` | 2 | JP1, JP2 | 4 pin header, 2.54mm pitch | README.md:172 `649-68000-204HLF` |
| `Conn_RCA_Right` | 1 | J1 | RCA Phono connector, Yellow | README.md:174 `490-RCJ-014` |
| `Conn_Power_Jack_Circular_Pads` | 1 | J2 | DC Power Jack, 2mm | README.md:175 `806-KLDX-0202-A` |
| `Conn_Friction_Lock_8P_2.54mm` | 1 | J3 | 8 pin friction lock connector | README.md:176 `571-6404568` |
| `Conn_DIN_8pin` | 1 | J4 | DIN 8-pos, Right Angle, PCB mount | README.md:177 `490-SDF-80J` |
| `Conn_Dsub_DE9M` | 1 | J5 | Sub-D DE9M, Right Angle, PCB mount | README.md:178 `523-L717SDE09P1ACH3R` |
| `Conn_Pin_Header_13x2_2.54mm_Shrouded` | 1 | J6 | 13x2 pin header, shrouded | README.md:179 `517-30326-6002` |
| `Conn_Pin_Header_20x1_2.54mm` | 1 | J7 | 20x1 pin socket | README.md:180 `517-929850-01-20-RB` |
| `Crystal_HC-49U_Vert` | 1 | Y1 | 16 MHz, Series, HC-49U | README.md:222 `774-ATS160-E` |
| `DC-DC_SIP8` | 1 | U26 | IZ0512, +/-12V +/-125mA DC-DC converter | README.md:220 `209-IZ0512S` |
| `IC_TO220-3_Vert` | 1 | U25 | LM7905 Negative 5V 1A Linear Regulator, TO-220 | README.md:219 `926-LM7905CT-NOPB` |
| `Speaker_12mm` | 1 | SP1 | 12mm speaker | README.md:192 `665-AT-1224TWTR` |
| `Switch_Tactile_6mm_Right` | 1 | SW68 | 6mm Tactile Switch Right Angle | README.md:196 `653-B3F-3152` |
| `IC_DIP8_300` | 3 | U21, U23, U24 | TL071 op-amp; SN75150P x2 Dual RS-232 Driver — all 8-pin DIP | README.md:216, 218 |
| `IC_DIP14_300` | 6 | U15-U20 | 74LS-series glue logic, all 14-pin DIP | README.md:210-215 |
| `IC_DIP16_300` | 3 | U2, U14, U22 | 8224 Clock Gen, 74LS138, SN75154N — all 16-pin DIP | README.md:199, 209, 217 |
| `IC_DIP20_300` | 1 | U12 | 74LS373 8-bit Latch, 20-pin DIP | README.md:207 |
| `IC_DIP24_600` | 2 | U4, U13 | 8253 PIT, 74198 Shift Register — 24-pin DIP | README.md:201, 208 |
| `IC_DIP28_600` | 4 | U3, U9, U10, U11 | 8251A USART, AS6C62256 SRAM, 2x 2716 EPROM — 28-pin DIP | README.md:200, 205, 206 |
| `IC_DIP40_600` | 5 | U1, U5, U6, U7, U8 | 8080A CPU, 2x 8255A PPI, 8257 DMA, 8275 CRTC — 40-pin DIP | README.md:198, 202-204 |

### IC socket BOM data (separate from the chip BOM rows above — needed for the 3D-model stack-height lookup in Tasks 23-29)

| DIP pin count | Refs using this socket | Socket Mouser P/N(s) | README line |
|---|---|---|---|
| 8-pin | U21, U23, U24 | `649-DILB8P223TLF`, `517-4808-3000-CP` | README.md:229 |
| 14-pin | U15-U20 | `649-DILB14P-223TLF`, `517-4814-3000-CP` | README.md:228 |
| 16-pin | U2, U14, U22 | `649-DILB16P-223TLF`, `517-4816-3000-CP` | README.md:227 |
| 20-pin | U12 | `649-DILB20P-223TLF`, `517-4820-3000-CP` | README.md:226 |
| 24-pin | U4, U13 | `649-DILB24P-223TLF`, `517-4824-6000-CP` | README.md:225 |
| 28-pin | U3, U9, U10, U11 | `649-DILB28P223TLF`, `517-4828-6000-CP` | README.md:224 |
| 40-pin | U1, U5, U6, U7, U8 | `649-DILB40P223TLF`, `517-4840-6000-CP` | README.md:223 |

Sheet locations for each reference (needed for `schematicPath` in every edit — confirmed via `mcp__kicad__list_schematic_components` during the resistor work):
- Root (`Radio-86RK.kicad_sch`): R6 (already done); check others per-task, most passives are on sub-sheets.
- `Radio-86RK-CRT-Mem.kicad_sch`, `Radio-86RK-IO.kicad_sch`, `Radio-86RK-Keyboard.kicad_sch`, `Radio-86RK-Power.kicad_sch`.

Each task's Step 1 includes the exact `mcp__kicad__list_schematic_components` calls (one per sheet, filtered by reference prefix) needed to confirm which sheet(s) hold that task's references — do not assume from the table above; verify live, since a reference's sheet placement is ground truth only in the `.kicad_sch` files.

---

## Task 1: Baseline DRC Snapshot

**Files:**
- Read only: `KiCad/Radio-86RK.kicad_pro`, `KiCad/Radio-86RK.kicad_pcb`
- Create: `KiCad/Radio-86RK_drc_violations.json` (already gitignored/untracked — this is a working artifact, not committed)

**Interfaces:**
- Produces: a known-good "before" DRC violation count and list, referenced by every subsequent task's Step 1 ("confirm regression baseline still matches").

- [ ] **Step 1: Open the project via MCP**

Call `mcp__kicad__open_project` with `filename: "/Users/dveremeev/projects/radio-86rk/KiCad/Radio-86RK.kicad_pro"`.

Expected: `{"success": true, ...}`.

- [ ] **Step 2: Run DRC and save the violation list**

Call `mcp__kicad__run_drc`.

**Actual baseline found (2026-07-06):** 1100 total violations, 108 `lib_footprint_issues` (matches the 28-footprint/108-instance survey in this plan exactly), plus a much larger pre-existing set unrelated to `My_Components`: `clearance` (332), `shorting_items` (202), `hole_clearance` (200), `solder_mask_bridge` (200), `track_dangling` (24), `starved_thermal` (6), `silk_edge_clearance` (18), `courtyards_overlap` (7), `hole_to_hole` (1), `isolated_copper` (1), `holes_co_located` (1). Cross-referenced violation coordinates against all 15 already-relinked resistor positions: only 8-30 of each large category cluster near a resistor, so this is **not** fallout from the R1-R15 footprint swap — it's a pre-existing board condition (likely inherited from the v9→v10 migration's default clearance rules). Per user decision, this entire non-`lib_footprint_issues` set is **out of scope for this plan**, same as the previously-known `starved_thermal`/`silk_edge_clearance` items — do not fix any of it as a side effect of any task below.

- [ ] **Step 3: Record the baseline count**

Baseline `lib_footprint_issues` = **108**. This is the only number every subsequent task's Verify step should track (via the delta it specifies) — ignore all other violation-count changes; they're pre-existing noise outside this plan's scope.

No commit for this task — it's a read-only checkpoint.

---

## Task 2: Capacitors — Ceramic (`Cap_Cer_508`, C1-C32/C39-C44/F1)

**Files:**
- Modify: `KiCad/Radio-86RK-CRT-Mem.kicad_sch`, `KiCad/Radio-86RK-IO.kicad_sch`, `KiCad/Radio-86RK-Keyboard.kicad_sch`, `KiCad/Radio-86RK-Power.kicad_sch`, `KiCad/Radio-86RK.kicad_sch` (confirm actual sheet placement in Step 1 — do not assume)

**Interfaces:**
- Consumes: BOM data from the Reference data table (39 refs, 8 distinct capacitance values + 1 polyfuse, all sharing one 5mm-pitch 2-pad footprint).
- Produces: none consumed by later tasks (independent).

- [ ] **Step 1: Locate every reference on its sheet**

Call `mcp__kicad__list_schematic_components` once per `.kicad_sch` file with `filter: {"referencePrefix": "C"}`, and once with `{"referencePrefix": "F"}`. Record which sheet holds each of C1-C32, C39-C44, F1.

- [ ] **Step 2: Pull current footprint geometry for one instance per distinct value**

Call `mcp__kicad__get_component_properties` and `mcp__kicad__get_component_pads` for one representative of each group: C1 (0.1uF), C39 (0.22uF), C40 (22nF), C41 (10nF), C42 (2.2nF), C43 (1nF), C44 (10pF), F1 (polyfuse). Confirm pad pitch/hole/pad size are identical across all of them (same pattern already established for the resistors — if any instance differs, flag it and do not assume uniformity).

- [ ] **Step 3: Fetch real part mechanical dimensions**

For the MLCC line (`594-K104K15X7RF53H5`, `810-FG24X7R1H224KNT0`, `810-FG28X7R1H223KNT0`, `810-FG28X7R1H103KNT0`, `810-FG28X7R1H222KNT0`, `810-FG28C0G1H102JNT6`, `810-FG28C0G1H100DNT0`) and the polyfuse (`576-16R110BU`), use WebSearch to find each manufacturer's datasheet (Vishay/KEMET/Yageo for the caps, Bel Fuse/Littelfuse for the polyfuse) and record body diameter, lead spacing, and lead diameter. Note: Mouser product pages have previously timed out via WebFetch (see resistor task) — go to the manufacturer datasheet PDF directly via WebSearch instead.

- [ ] **Step 4: Search official KiCad libraries for candidates**

Call `mcp__kicad__search_footprints` with `search_term: "CP_Radial"` (for the polyfuse and any radial candidates) and `search_term: "C_Disc"` (for radial ceramic disc/MLCC 5mm-pitch parts) in library `Capacitor_THT`. Cross-check candidate pad pitch against the real part's lead spacing from Step 3.

- [ ] **Step 5: Build and present the comparison report**

Present a table: project footprint vs. each candidate vs. real part dimensions, one row per distinct value/part, highlighting any mismatch (pitch, hole, pad, silkscreen size, 3D model presence/absence). **Do not proceed to Step 6 without explicit user confirmation of which candidate to use** — there may be one candidate per value (since 0.1uF vs 10pF MLCCs can have different real body sizes despite sharing a PCB footprint historically).

- [ ] **Step 6: Relink via batch edit**

For each sheet found in Step 1, call `mcp__kicad__batch_edit_schematic_components` with the confirmed footprint(s) for every reference on that sheet. If different values map to different official footprints, group the batch calls accordingly (do not force all 39 onto one footprint if the research in Step 5 showed they shouldn't be).

- [ ] **Step 7: Forward-annotate**

Ask the user to run "Update PCB from Schematic" (F8) in the KiCad UI, and wait for confirmation it completed without "footprint not found" errors.

- [ ] **Step 8: Verify**

Call `mcp__kicad__open_project` then `mcp__kicad__get_component_list`, confirm C1-C32/C39-C44/F1 now show the new footprint(s) and no longer show `My_Components:Cap_Cer_508`. Call `mcp__kicad__run_drc` and confirm the `lib_footprint_issues` count dropped by exactly 39 from the Task 1 baseline.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink ceramic capacitors and F1 polyfuse to official footprint(s)

<fill in the specific official footprint name(s) chosen in Step 5 and
why, following the pattern established for R1-R15 in commit 5dabaf9>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Capacitors — Electrolytic (`Cap_Elec_Radial_6.3mm`, C33-C38)

**Files:**
- Modify: sheet(s) confirmed in Step 1 (likely `Radio-86RK-Power.kicad_sch` or `Radio-86RK-CRT-Mem.kicad_sch` — confirm, do not assume)

**Interfaces:**
- Consumes: none from Task 2 (independent capacitor family, different footprint).
- Produces: none.

- [ ] **Step 1: Locate C33-C38**

Call `mcp__kicad__list_schematic_components` with `{"referencePrefix": "C"}` on each sheet; record which sheet(s) hold C33-C38.

- [ ] **Step 2: Pull current geometry**

Call `mcp__kicad__get_component_properties` and `mcp__kicad__get_component_pads` for C33. Record pad pitch, hole diameter, and body diameter implied by silkscreen (per the resistor-task method: extract the raw footprint block from `Radio-86RK.kicad_pcb` for one instance and inspect the `fp_line`/`fp_circle` body outline).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch the Mouser P/N `80-A750EK476M1EAAE40` (47uF 25V Electrolytic or Organic Polymer) — this is a Kemet/AVX part number pattern; find the manufacturer datasheet and record can diameter and lead spacing.

- [ ] **Step 4: Search official KiCad libraries**

Call `mcp__kicad__search_footprints` with `search_term: "CP_Radial"` in library `Capacitor_THT`, filtering to the lead spacing found in Step 3 (radial electrolytic caps come in standard 2.0/2.5/3.5/5.0/7.5mm pitches).

- [ ] **Step 5: Build and present comparison report; get confirmation**

Same format as Task 2 Step 5. Do not proceed without explicit go-ahead.

- [ ] **Step 6: Relink via batch edit**

Call `mcp__kicad__batch_edit_schematic_components` for C33-C38 on their sheet(s) with the confirmed footprint.

- [ ] **Step 7: Forward-annotate**

User runs F8 in KiCad UI; wait for confirmation.

- [ ] **Step 8: Verify**

Reopen project, `get_component_list` confirms C33-C38 show the new footprint. `run_drc` confirms count dropped by 6 more from Task 2's post-count.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink electrolytic capacitors C33-C38 to official footprint

<specific footprint name and real-part justification>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Diodes (`Diode_762`, D1-D9)

**Files:**
- Modify: sheet(s) confirmed in Step 1

- [ ] **Step 1: Locate D1-D9**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "D"}` on each sheet (this will also surface D10/D11 LEDs — exclude those, they're Task 5).

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for D1. The footprint name `Diode_762` mirrors `Res_762` exactly (762 = 7.62mm pitch) — check whether it's pad-for-pad identical to the resistor footprint that was replaced in commit `5dabaf9` (same pitch, same pad/drill size), since 1N4148 in a DO-35 glass package is commonly hand-designed on the same 7.62mm through-hole grid as axial resistors.

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "1N4148 datasheet DO-35" (Mouser P/N `512-1N4148`) — On Semi/Vishay datasheet gives body length/diameter and lead diameter for the DO-35 package.

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "D_DO-35"` in library `Diode_THT`. Check pitch options (P7.62mm, P10.16mm, etc.) against Step 2/3 findings.

- [ ] **Step 5: Build and present comparison report; get confirmation**

Include a polarity check in the report: confirm pad 1 = cathode (banded end) convention matches between old and new footprint, since diodes are polarity-sensitive and a silent pad-1/pad-2 swap would invert every diode on the board without tripping DRC.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for D1-D9.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, `get_component_list` confirms D1-D9 on new footprint. `run_drc` count check. Additionally spot-check net connectivity: `mcp__kicad__get_component_pads` on D1 before and after, confirm the same nets (`net` field) are attached to the same numbered pads (catches a polarity swap the DRC wouldn't).

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink diodes D1-D9 to official DO-35 footprint

<specific footprint name, real-part justification, polarity verified>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Transistors (`Transistor_TO92_EBC_254`, Q1/Q2/U27)

**Files:**
- Modify: sheet(s) confirmed in Step 1

**Interfaces:**
- Consumes: none.
- Produces: none. Note U27 is electrically a supervisory IC (DS1233-5) but mechanically a TO-92 — do not move it into the IC task group; it belongs here because the footprint is what's being fixed, not the symbol.

- [ ] **Step 1: Locate Q1, Q2, U27**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "Q"}` and separately confirm U27's sheet via `{"referencePrefix": "U"}`.

- [ ] **Step 2: Pull current geometry for both real parts separately**

`get_component_properties` + `get_component_pads` for Q1 and for U27 — **do not assume they're pin-compatible just because they share a footprint name.** 2N3904 (Q1/Q2) is EBC pinout per the footprint name; DS1233-5 (U27) is a 3-pin TO-92 CPU supervisor with a different pinout (VCC/GND/RESET, not E/B/C) — the *pitch and body* may be identical DO-based TO-92, but confirm which physical pad number carries which net for each part today, so the replacement footprint's pad numbering doesn't silently swap pins for one part while being correct for the other.

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "2N3904 TO-92 datasheet" (`512-2N3904TA`) and "DS1233-5 TO-92 datasheet" (`700-DS1233-5T&R`) — Maxim/Analog Devices datasheet for the DS1233. Confirm both are standard EIA TO-92, same lead pitch (typically 1.27mm at the die, formed to 2.54mm at the board).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "TO-92"` in library `Package_TO_SOT_THT`. There are typically multiple TO-92 variants (Inline, Wide, Molded_Wide) — match to the exact lead spacing found in Step 3.

- [ ] **Step 5: Build and present comparison report; get confirmation**

Report must show, per reference, current pad→net mapping vs. candidate footprint's pad numbering, explicitly confirming no pin swap for Q1, Q2, and U27 independently.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for Q1, Q2, U27 (same sheet or different — apply per-sheet as found in Step 1).

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, `get_component_list` + `get_component_pads` on all three refs — confirm same net-to-pad-number mapping as recorded in Step 2. `run_drc` count check (drop by 3).

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink transistors Q1/Q2 and U27 to official TO-92 footprint

<specific footprint, confirmation that pin mapping is unchanged for
both the 2N3904s and the DS1233-5 supervisor>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: LEDs (`LED_3mm`, D10/D11)

**Files:**
- Modify: sheet(s) confirmed in Step 1

- [ ] **Step 1: Locate D10, D11**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "D"}`, filter to D10/D11.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for D10.

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "HLMP-1503 datasheet" and "HLMP-1401 datasheet" (Broadcom/Avago 3mm LED indicators, Mouser `630-HLMP-1503-C0002` / `630-HLMP-1401`). Record lead spacing and body diameter (standard T-1 3mm package).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "LED_D3.0mm"` in library `LED_THT`.

- [ ] **Step 5: Build and present comparison report; get confirmation**

Include polarity check (anode/cathode pad mapping) same as the diode task — LED polarity errors are a common and easy-to-miss failure mode of exactly this kind of swap.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for D10, D11.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint + unchanged pad/net mapping (as in Task 4 Step 8). `run_drc` count drops by 2.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink indicator LEDs D10/D11 to official 3mm THT footprint

<specific footprint, polarity verified>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Mounting Holes (`Hole_3mm`, HOLE1-HOLE7)

**Files:**
- Modify: sheet(s) confirmed in Step 1 (mounting holes are sometimes schematic-less, placed only on the PCB — confirm this first, it changes the whole approach for this task)

**Interfaces:**
- Consumes: none.
- Produces: none.

- [ ] **Step 1: Determine whether HOLE1-7 exist in the schematic at all**

Call `mcp__kicad__list_schematic_components` with `{"referencePrefix": "HOLE"}` on every sheet. If they return zero results, these are PCB-only footprints with no schematic symbol — skip straight to Step 3 (PCB-only fix path). If they do appear, proceed with Step 2 (schematic fix path, same pattern as other tasks).

- [ ] **Step 2 (if schematic symbols exist): Pull current geometry**

`get_component_properties` for HOLE1. Confirm it's a simple NPTH (non-plated through hole) with no copper/net — mounting holes should not have an electrical net.

- [ ] **Step 3: Identify the correct official replacement**

Mounting holes have no BOM part (they're structural, sized to the case screw, e.g. M3). Call `mcp__kicad__search_footprints` with `search_term: "MountingHole"` in library `MountingHole`. Confirm the 3mm variant (`MountingHole_3.2mm_M3`, typically) matches the current hole's drill diameter — call `mcp__kicad__get_component_pads` (or read the raw footprint block from `Radio-86RK.kicad_pcb` for HOLE1's `fp_circle`/pad drill) to get the exact existing drill size in mm before picking a candidate.

- [ ] **Step 4: Build and present comparison report; get confirmation**

Simple report: current drill diameter vs. candidate's drill diameter. No BOM part to cross-check against since this is structural, not sourced.

- [ ] **Step 5a (if schematic path): Relink via batch edit + forward-annotate + verify**

Same pattern as prior tasks: `batch_edit_schematic_components`, F8, reopen + `get_component_list`, `run_drc` count check (drop by 7).

- [ ] **Step 5b (if PCB-only path): Edit directly on the PCB**

If Step 1 found no schematic symbols, these must be fixed via PCB-side footprint replacement (`mcp__kicad__replace_component` or equivalent PCB tool — confirm exact tool name via `mcp__kicad__get_category_tools` for the "footprint" category before calling, since this path wasn't exercised in any prior task in this plan). Do this per-instance for HOLE1-HOLE7, then re-run `mcp__kicad__run_drc` directly (no forward-annotation needed since there's no schematic side).

- [ ] **Step 6: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/Radio-86RK.kicad_pcb KiCad/*.kicad_sch
git commit -m "$(cat <<'EOF'
Relink mounting holes HOLE1-7 to official MountingHole footprint

<specific footprint and drill-size confirmation>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Connector — `Conn_SIL10` (RN1, 10k Resistor Array SIP10)

**Files:**
- Modify: sheet confirmed in Step 1

**Interfaces:**
- Consumes: none.
- Produces: none. (RN1 is electrically a resistor network but mechanically a SIP header — footprint-only fix, matching the pattern set for U27 in Task 5.)

- [ ] **Step 1: Locate RN1**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "RN"}` on each sheet.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for RN1 — record all 10 pad positions/pitch (SIP10 = single in-line, 10 pins, one row).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "652-4610X-1LF-10K datasheet" (Bourns 4610X SIP resistor network) — record pin count, pitch, and package width/height.

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "SIP10"` in library `Resistor_THT` (KiCad's official library has SIP resistor network footprints under `Resistor_THT:R_Array_SIP10`, confirmed present in the earlier `Resistor_THT` library listing from the resistor task — 104 footprints were enumerated then, including `R_Array_SIP*` variants).

- [ ] **Step 5: Build and present comparison report; get confirmation**

Confirm pin 1 (common pin, in a bussed SIP network) lines up between old and new footprint — a SIP resistor network's "common" pin is often pin 1 or pin 6 depending on family, and a mismatch here silently changes which resistor is common vs. isolated.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for RN1.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, `get_component_list` + `get_component_pads` confirms new footprint and unchanged net-to-pin mapping. `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink RN1 (10k SIP10 resistor array) to official footprint

<specific footprint, common-pin mapping verified>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Connector — `Conn_SIL6` (RN2/RN3/RN4, 4.7k Resistor Array SIP6)

**Files:**
- Modify: sheet(s) confirmed in Step 1

- [ ] **Step 1: Locate RN2, RN3, RN4**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "RN"}`, filter to RN2-4.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for RN2.

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "652-4606X-1LF-4.7K datasheet" (Bourns 4606X SIP6 resistor network).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "SIP6"` in library `Resistor_THT` (`R_Array_SIP6`).

- [ ] **Step 5: Build and present comparison report; get confirmation**

Same common-pin check as Task 8.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for RN2, RN3, RN4.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint + pin mapping unchanged for all three. `run_drc` count drops by 3.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink RN2-RN4 (4.7k SIP6 resistor arrays) to official footprint

<specific footprint, common-pin mapping verified>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Connector — `Conn_Pin_Header_4x1_2.54mm` (JP1/JP2)

**Files:**
- Modify: sheet(s) confirmed in Step 1

- [ ] **Step 1: Locate JP1, JP2**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "JP"}`.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for JP1.

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "649-68000-204HLF datasheet" (TE Connectivity 68000 series 2.54mm pin header) — confirm 4-pin single row, 2.54mm pitch, straight or right-angle.

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "PinHeader_1x04_P2.54mm"` in library `Connector_PinHeader_2.54mm`.

- [ ] **Step 5: Build and present comparison report; get confirmation**

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for JP1, JP2.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint. `run_drc` count drops by 2.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink JP1/JP2 (4-pin 2.54mm headers) to official footprint

<specific footprint>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Connector — `Conn_RCA_Right` (J1)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate J1**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "J"}`, filter to J1.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for J1 (expect 2 pads: signal + shield/ground, plus possibly 2 mechanical mounting pads for an RCA jack).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "490-RCJ-014 datasheet" (CUI Devices RCJ-014 RCA jack).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "RCA"` (check `Connector_Audio` and `Connector` libraries).

- [ ] **Step 5: Build and present comparison report; get confirmation**

Verify mechanical mounting pad positions too, not just the 2 signal pads — RCA jacks are often through-hole with additional mechanical-only pads that must line up or the connector won't physically seat.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for J1.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint + pad positions compatible with existing board cutout/silkscreen (visually check via `mcp__kicad__get_board_2d_view` around J1's position if available). `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink J1 (RCA phono jack) to official footprint

<specific footprint, mechanical pad fit confirmed>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Connector — `Conn_Power_Jack_Circular_Pads` (J2)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate J2**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "J"}`, filter to J2.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for J2.

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "806-KLDX-0202-A datasheet" (CUI/Kobiconn 2mm DC power jack).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "BarrelJack"` (check `Connector` library).

- [ ] **Step 5: Build and present comparison report; get confirmation**

Confirm center-pin vs. sleeve polarity mapping explicitly (DC jacks are polarity-sensitive at the board level even though the jack mechanically can't be inserted backwards — a pad-number swap here can reverse polarity silently).

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for J2.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint + pad/net mapping unchanged (Task 4-style check). `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink J2 (2mm DC power jack) to official footprint

<specific footprint, polarity mapping verified>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Connector — `Conn_Friction_Lock_8P_2.54mm` (J3)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate J3**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "J"}`, filter to J3.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for J3 (8 pins expected).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "571-6404568 datasheet" (TE Connectivity 640456 series friction-lock header).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "PinHeader_1x08_P2.54mm"` in `Connector_PinHeader_2.54mm` (friction-lock headers are usually footprint-identical to standard 2.54mm headers — the friction-lock feature is mechanical/molded, not a PCB pad difference; confirm this assumption against the datasheet, don't just assert it).

- [ ] **Step 5: Build and present comparison report; get confirmation**

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for J3.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint. `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink J3 (8-pin friction-lock header) to official footprint

<specific footprint>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Connector — `Conn_DIN_8pin` (J4)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate J4**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "J"}`, filter to J4.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for J4 (8 signal pins in DIN circular arrangement + likely 2 mechanical shield/mounting pads).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "490-SDF-80J datasheet" (CUI SDF-80J DIN 8-position right-angle jack).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "DIN"` (check `Connector` and `Connector_Audio` libraries) — DIN connector footprints are less standardized than headers; expect to need the exact pin-circle diameter from the datasheet to find or confirm a match.

- [ ] **Step 5: Build and present comparison report; get confirmation**

This connector is a strong candidate for having no exact official match (right-angle PCB-mount DIN-8 jacks are a narrow niche) — be prepared to recommend the "materialize exact existing geometry as project-local custom footprint" path (the `Cherry_MX_Custom` precedent from commit `daacbd7`) if no official candidate's pin-circle geometry matches within tolerance. Present this as an explicit option in the report, not a fallback decided unilaterally.

- [ ] **Step 6: Relink via batch edit, OR create custom footprint**

If an official match was confirmed: `mcp__kicad__batch_edit_schematic_components` for J4.
If no match: extract J4's existing embedded footprint geometry from `Radio-86RK.kicad_pcb` (same S-expression-preserving method used for `CHERRY_PCB_225H`/`CHERRY_PCB_625H`), create a new `.kicad_mod` file in a project-local `.pretty` folder, add a corresponding `fp-lib-table` entry, then relink J4 to it.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint (official or custom) and unchanged pad/net mapping for all 8 signal pins. `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table
git commit -m "$(cat <<'EOF'
Relink J4 (DIN 8-pin right-angle jack) to <official footprint OR
new project-local custom footprint>

<justification>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Connector — `Conn_Dsub_DE9M` (J5)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate J5**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "J"}`, filter to J5.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for J5 (9 signal pins + 2 mechanical shield-mount pads expected for a right-angle DE9).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "523-L717SDE09P1ACH3R datasheet" (Amphenol L717 series right-angle DE9 male).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "DSUB"` in library `Connector_Dsub` — check for right-angle DE9 male variants specifically (`DSUB-9_Male_Vertical` vs `_Horizontal` matters here since J5 is right-angle/PCB-mount).

- [ ] **Step 5: Build and present comparison report; get confirmation**

Confirm mechanical mounting-pad positions match (DSUB shells have standardized mounting hole spacing, but right-angle vs. vertical variants differ) — a mismatch here means the metal shell won't align with the panel cutout.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for J5.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint and unchanged pad/net mapping for all 9 signal pins. `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink J5 (DE9M right-angle D-sub) to official footprint

<specific footprint, mechanical shell fit confirmed>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: Connector — `Conn_Pin_Header_13x2_2.54mm_Shrouded` (J6)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate J6**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "J"}`, filter to J6.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for J6 (26 pins, 2x13 double row expected).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "517-30326-6002 datasheet" (Amphenol/FCI 30326 series shrouded box header).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "IDC-Header_2x13_P2.54mm"` in library `Connector_IDC`.

- [ ] **Step 5: Build and present comparison report; get confirmation**

Confirm pin-numbering convention matches (IDC headers can be numbered boustrophedon/zig-zag vs. row-by-row differently between footprint authors) — this is the highest-pin-count connector in the plan and the easiest one to introduce a silent net-swap in if pin 1 orientation isn't matched.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for J6.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint and unchanged pad/net mapping for all 26 pins (spot-check at minimum pins 1, 2, 13, 14, 25, 26 — the corners/midpoints most likely to reveal a numbering-convention mismatch). `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink J6 (13x2 shrouded IDC header) to official footprint

<specific footprint, pin-numbering convention verified>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: Connector — `Conn_Pin_Header_20x1_2.54mm` (J7)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate J7**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "J"}`, filter to J7.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for J7 (20 pins, single row expected — note the BOM description says "20x1 pin socket", i.e. female header, not a male pin header; check whether that distinction matters for footprint choice, since sockets and headers often share the same THT pad pattern but not always).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "517-929850-01-20-RB datasheet" (TE Connectivity 929850 series pin socket).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "PinSocket_1x20_P2.54mm"` in library `Connector_PinSocket_2.54mm` (note: distinct library from `Connector_PinHeader_2.54mm` used in Task 10 — this is a socket, not a header).

- [ ] **Step 5: Build and present comparison report; get confirmation**

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for J7.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint. `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink J7 (20x1 pin socket) to official footprint

<specific footprint>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: Crystal (`Crystal_HC-49U_Vert`, Y1)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate Y1**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "Y"}`.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for Y1.

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "774-ATS160-E datasheet" (Abracon ATS160-E 16MHz HC-49U crystal).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "Crystal_HC49"` in library `Crystal`. Note the footprint name says "Vert" (vertical mount) — confirm the candidate's orientation matches; HC-49U crystals are commonly available in both horizontal and vertical mount footprints with different pad spacing.

- [ ] **Step 5: Build and present comparison report; get confirmation**

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for Y1.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint. `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink Y1 (16MHz HC-49U crystal) to official footprint

<specific footprint, vertical-mount orientation confirmed>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: DC-DC Converter (`DC-DC_SIP8`, U26)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate U26**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}`, filter to U26.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for U26 (SIP8 package, 8 pins single row expected).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "209-IZ0512S datasheet" (RECOM/CUI IZ0512S DC-DC converter module) — SIP DC-DC converter modules often have non-standard/wider pin pitch than logic-IC SIP headers, or missing/NC pins; check carefully.

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "SIP-8"` (check `Converter_DCDC` library, which KiCad ships specifically for modules like this).

- [ ] **Step 5: Build and present comparison report; get confirmation**

This is a good candidate for an exact official match since KiCad's `Converter_DCDC` library is designed for exactly this class of part — but confirm pin pitch and any missing/NC pin positions against the datasheet rather than assuming.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for U26.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint. `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink U26 (IZ0512S DC-DC converter) to official footprint

<specific footprint>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 20: TO-220 Regulator (`IC_TO220-3_Vert`, U25)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate U25**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}`, filter to U25.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for U25 (3 pins: IN/GND/OUT for LM7905, vertical TO-220 mount expected — record which pad number carries which pin today).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "926-LM7905CT-NOPB datasheet" (Texas Instruments LM7905 negative regulator, TO-220-3 package) — confirm pinout (note: LM7905 negative regulator pinout order can differ from a positive LM78xx regulator, verify explicitly, don't assume EBC-style ordering).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "TO-220"` in library `Package_TO_SOT_THT`, filtering to the vertical variant matching the current footprint's "Vert" orientation.

- [ ] **Step 5: Build and present comparison report; get confirmation**

Report must show current pad→pin mapping (IN/GND/OUT) vs. candidate footprint's pad numbering — confirm no swap, same as the transistor task.

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for U25.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint and unchanged pad/net mapping (IN/GND/OUT nets on the same pad numbers as recorded in Step 2). `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink U25 (LM7905 TO-220 regulator) to official footprint

<specific footprint, IN/GND/OUT pin mapping verified>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 21: Speaker (`Speaker_12mm`, SP1)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate SP1**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "SP"}`.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for SP1.

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "665-AT-1224TWTR datasheet" (PUI Audio AT-1224TWTR 12mm speaker) — confirm mounting pad pattern (many small speakers mount via 2 solder-tab pads, not a standardized THT footprint family).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "Speaker"` (check `Buzzer_Beeper` library — KiCad's official library naming groups speakers/buzzers there).

- [ ] **Step 5: Build and present comparison report; get confirmation**

This is a plausible second candidate (after J4/DIN) for "no exact official match — materialize as project-local custom footprint" — present that option explicitly if the search in Step 4 doesn't turn up a matching pad pattern.

- [ ] **Step 6: Relink via batch edit, OR create custom footprint**

Same conditional structure as Task 14 Step 6.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint (official or custom). `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table
git commit -m "$(cat <<'EOF'
Relink SP1 (12mm speaker) to <official footprint OR new project-local
custom footprint>

<justification>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 22: Tactile Switch (`Switch_Tactile_6mm_Right`, SW68)

**Files:**
- Modify: sheet confirmed in Step 1

- [ ] **Step 1: Locate SW68**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "SW"}`, filter to SW68 (do not confuse with the 67 Cherry MX keyboard switches, already resolved).

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for SW68 (4 pads expected — right-angle tactile switches are usually 4-pin SPST with 2 pins per side).

- [ ] **Step 3: Fetch real part mechanical dimensions**

WebSearch "653-B3F-3152 datasheet" (Omron B3F-3152 6mm right-angle tactile switch).

- [ ] **Step 4: Search official KiCad libraries**

`mcp__kicad__search_footprints` with `search_term: "SW_PUSH_6mm"` in library `Button_Switch_THT`, filtering to the right-angle/horizontal variant.

- [ ] **Step 5: Build and present comparison report; get confirmation**

- [ ] **Step 6: Relink via batch edit**

`mcp__kicad__batch_edit_schematic_components` for SW68.

- [ ] **Step 7: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 8: Verify**

Reopen, confirm new footprint. `run_drc` count drops by 1.

- [ ] **Step 9: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb
git commit -m "$(cat <<'EOF'
Relink SW68 (6mm right-angle tactile switch) to official footprint

<specific footprint>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 23: ICs — 8-pin DIP (`IC_DIP8_300`, U21/U23/U24)

**Files:**
- Modify: sheet(s) confirmed in Step 1
- Possibly create: `KiCad/IC_Socket_Custom.pretty/` and a new `fp-lib-table` entry, if Step 5 concludes a composite footprint is needed (same precedent as `Cherry_MX_Custom`, commit `daacbd7`)

**Interfaces:**
- Consumes: none from prior tasks.
- Produces: **the IC socket-vs-chip 3D-model decision that Tasks 24-29 reuse without re-litigating.** Everything else (pad pattern search, package-width confirmation, batch relink, forward-annotate, verify, commit) is the same repeatable shape as every prior task; only Steps 4-6 here are new and specific to ICs.

- [ ] **Step 1: Locate U21, U23, U24**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}` on each sheet, filter to U21/U23/U24.

- [ ] **Step 2: Pull current geometry and current 3D model reference**

`get_component_properties` + `get_component_pads` for U21. Confirm 8 pins, row spacing (0.3in/7.62mm implied by the "_300" suffix), and per-pin pitch (standard 0.1in/2.54mm). Also read U21's raw footprint block from `Radio-86RK.kicad_pcb` and check for a `(model ...)` entry — following the pattern found for the resistors/capacitors/diodes (a bare `discret/...` path that resolves nowhere on this machine), record whether the DIP footprints have any 3D model today at all, or none.

- [ ] **Step 3: Confirm package width against the real parts**

These 3 refs are 3 different real ICs (TL071 op-amp, 2x SN75150P RS-232 driver — README.md:216, 218) but all standard 8-pin 300mil DIP. WebSearch "TL071 datasheet DIP-8" and "SN75150P datasheet DIP-8" to confirm both are genuinely 300mil (not 150mil narrow-body, which some op-amps use) — do not assume from the footprint name alone, verify against at least one datasheet per distinct IC.

- [ ] **Step 4: Fetch the socket's real mechanical dimensions**

Per the "IC socket BOM data" reference table: the 8-pin socket is Mouser `649-DILB8P223TLF` / `517-4808-3000-CP`. WebSearch "DILB8P223TLF datasheet" (3M/TE Connectivity turned-pin DIP socket) and record its **stack height** (the dimension from the PCB surface to the top of the socket, i.e. how far the socket raises the chip above the board) — this is the number the 3D model Z-offset in Step 6 depends on. Textool/turned-pin DIP sockets are commonly ~3.3-4.6mm tall; do not assume, read it off the datasheet.

- [ ] **Step 5: Search for pad pattern AND for existing socket/chip 3D models**

Two separate searches:
1. Pad pattern (as in every prior task): `mcp__kicad__search_footprints` with `search_term: "DIP-8_W7.62mm"` in library `Package_DIP`. Call `mcp__kicad__get_footprint_info` on the result to see what 3D model(s) it already ships with (expect exactly one: the bare IC body, no socket — confirm this assumption rather than asserting it).
2. Socket model: `mcp__kicad__search_footprints` with `search_term: "Socket"` across `Package_DIP` and any other library it returns hits in (some 3rd-party PCM packages, e.g. a dedicated DIP-socket footprint/3D-model pack, may already ship a combined or standalone socket 3D model — check what's actually installed via `mcp__kicad__list_footprint_libraries` before assuming none exists).

- [ ] **Step 6: Build the report — decide the 3D-model approach, get confirmation**

Present three options to the user, with the trade-off spelled out plainly (this decision applies to all 24 DIP ICs across Tasks 23-29, so get it right once):
- **(a) Official `Package_DIP` footprint as-is.** Correct pads, correct DRC-resolving library link, but the 3D view will show the chip sitting flush on the PCB with no socket — mechanically wrong height for the FreeCAD case clearance check, but zero extra work.
- **(b) Composite custom footprint.** Same pads as (a) (either reuse the official footprint's pad definitions directly, or copy them into a new file), but with two `(model ...)` entries: the official IC-body model at its normal offset, plus a socket 3D model (if Step 5.2 found one; otherwise a plain rectangular block approximation) at Z=0, and the IC body's own model offset upward in Z by the Step 4 stack-height figure. This is the `Cherry_MX_Custom` pattern applied here: preserve/compose exact geometry rather than accept a simplified official part.
- **(c) Accept option (a) now, revisit 3D accuracy later** if the user decides the DIP stack height doesn't matter enough to justify custom footprints for 7 pin-count variants right now.

Do not proceed past this step without an explicit choice — this determines the shape of every remaining IC task.

- [ ] **Step 7: Relink via batch edit, or build the composite footprint then relink**

If (a) or (c): `mcp__kicad__batch_edit_schematic_components` for U21, U23, U24 directly to the official footprint.
If (b): create `KiCad/IC_Socket_Custom.pretty/DIP-8_W7.62mm_Socketed.kicad_mod` (pads copied from the official footprint, plus the two-model stack from Step 6b), add an `IC_Socket_Custom` entry to `KiCad/fp-lib-table`, then `mcp__kicad__batch_edit_schematic_components` for U21, U23, U24 to point at it.

- [ ] **Step 8: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 9: Verify**

Reopen, confirm new footprint for all 3 refs. `run_drc` count drops by 3. If (b) was chosen, additionally ask the user to check the PCB 3D viewer at U21/U23/U24 and confirm the socket-then-chip stack renders correctly (same visual-confirmation step used for SW11/SW64 in commit `daacbd7` — "look excellent" was the bar there).

- [ ] **Step 10: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table KiCad/IC_Socket_Custom.pretty
git commit -m "$(cat <<'EOF'
Relink U21/U23/U24 (8-pin DIP ICs) to <official Package_DIP footprint
OR new composite IC_Socket_Custom footprint>

<package width confirmed against TL071/SN75150P datasheets; if
composite, note the socket P/N and stack height used for the 3D
Z-offset>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 24: ICs — 14-pin DIP (`IC_DIP14_300`, U15-U20)

**Files:**
- Modify: sheet(s) confirmed in Step 1
- Possibly create/modify: `KiCad/IC_Socket_Custom.pretty/`, `KiCad/fp-lib-table` — only if Task 23 Step 6 chose option (b)

**Interfaces:**
- Consumes: the 3D-model approach decided in Task 23 Step 6 (option a/b/c) — apply it here without re-asking, unless something about this pin count genuinely doesn't fit the prior decision (say so if it doesn't).

- [ ] **Step 1: Locate U15-U20**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}`, filter to U15-U20.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for U15.

- [ ] **Step 3: Confirm package width**

All six are 74LS-series glue logic (7492, 7486, 7474, 7408, 7404, 7400 — README.md:210-215), a family universally 300mil 14-pin DIP; WebSearch one datasheet (e.g. "SN74LS00 datasheet DIP-14") to confirm.

- [ ] **Step 4: Fetch the socket's real mechanical dimensions**

Per the "IC socket BOM data" table: 14-pin socket is Mouser `649-DILB14P-223TLF` / `517-4814-3000-CP`. WebSearch "DILB14P-223TLF datasheet" and record its stack height. (Skip this step entirely if Task 23 chose option (a) or (c) — no socket modeling needed.)

- [ ] **Step 5: Search official KiCad libraries for the pad pattern**

`mcp__kicad__search_footprints` with `search_term: "DIP-14_W7.62mm"` in library `Package_DIP`.

- [ ] **Step 6: Build and present comparison report; confirm applying Task 23's approach**

Report should be short since the 3D-model decision was already made — this is confirming the same choice applies (or flagging why it doesn't) for this pin count, plus the usual footprint/package-width comparison.

- [ ] **Step 7: Relink via batch edit, or build composite footprint then relink**

Same conditional as Task 23 Step 7, using this task's socket data if option (b).

- [ ] **Step 8: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 9: Verify**

Reopen, confirm new footprint for all 6 refs. `run_drc` count drops by 6. If option (b), confirm the 3D stack visually as in Task 23 Step 9.

- [ ] **Step 10: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table KiCad/IC_Socket_Custom.pretty
git commit -m "$(cat <<'EOF'
Relink U15-U20 (14-pin DIP 74LS-series logic) to <official
Package_DIP footprint OR composite IC_Socket_Custom footprint,
matching the Task 23 approach>

<confirmation details>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 25: ICs — 16-pin DIP (`IC_DIP16_300`, U2/U14/U22)

**Files:**
- Modify: sheet(s) confirmed in Step 1
- Possibly create/modify: `KiCad/IC_Socket_Custom.pretty/`, `KiCad/fp-lib-table` — only if Task 23 Step 6 chose option (b)

**Interfaces:**
- Consumes: the 3D-model approach decided in Task 23 Step 6.

- [ ] **Step 1: Locate U2, U14, U22**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}`, filter to U2/U14/U22.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for U2.

- [ ] **Step 3: Confirm package width against the real parts**

Three different real ICs (Intel 8224 clock generator, 74LS138 decoder, SN75154N RS-232 receiver — README.md:199, 209, 217); WebSearch at least the 8224 and SN75154N datasheets (74LS138 shares the well-known 74LS-family 300mil convention already confirmed in Task 24) to confirm 300mil width for all three.

- [ ] **Step 4: Fetch the socket's real mechanical dimensions**

Per the "IC socket BOM data" table: 16-pin socket is Mouser `649-DILB16P-223TLF` / `517-4816-3000-CP`. WebSearch "DILB16P-223TLF datasheet" and record its stack height. (Skip if Task 23 chose (a)/(c).)

- [ ] **Step 5: Search official KiCad libraries for the pad pattern**

`mcp__kicad__search_footprints` with `search_term: "DIP-16_W7.62mm"` in library `Package_DIP`.

- [ ] **Step 6: Build and present comparison report; confirm applying Task 23's approach**

- [ ] **Step 7: Relink via batch edit, or build composite footprint then relink**

Same conditional as Task 23 Step 7.

- [ ] **Step 8: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 9: Verify**

Reopen, confirm new footprint for all 3 refs. `run_drc` count drops by 3. If option (b), confirm the 3D stack visually.

- [ ] **Step 10: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table KiCad/IC_Socket_Custom.pretty
git commit -m "$(cat <<'EOF'
Relink U2/U14/U22 (16-pin DIP ICs) to <official Package_DIP footprint
OR composite IC_Socket_Custom footprint, matching the Task 23 approach>

<package width confirmed against 8224/SN75154N datasheets>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 26: ICs — 20-pin DIP (`IC_DIP20_300`, U12)

**Files:**
- Modify: sheet confirmed in Step 1
- Possibly create/modify: `KiCad/IC_Socket_Custom.pretty/`, `KiCad/fp-lib-table` — only if Task 23 Step 6 chose option (b)

**Interfaces:**
- Consumes: the 3D-model approach decided in Task 23 Step 6.

- [ ] **Step 1: Locate U12**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}`, filter to U12.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for U12.

- [ ] **Step 3: Confirm package width**

U12 is 74LS373 (README.md:207) — WebSearch "SN74LS373N datasheet DIP-20" to confirm 300mil (note: some 20-pin DIPs are 300mil, others 600mil — this is the one pin-count where the width isn't a safe assumption from the 74LS-family pattern alone, confirm explicitly).

- [ ] **Step 4: Fetch the socket's real mechanical dimensions**

Per the "IC socket BOM data" table: 20-pin socket is Mouser `649-DILB20P-223TLF` / `517-4820-3000-CP`. WebSearch "DILB20P-223TLF datasheet" and record its stack height. (Skip if Task 23 chose (a)/(c).)

- [ ] **Step 5: Search official KiCad libraries for the pad pattern**

`mcp__kicad__search_footprints` with `search_term: "DIP-20_W7.62mm"` in library `Package_DIP` (fall back to `search_term: "DIP-20"` without width filter if the 300mil variant doesn't exist, and compare both width options against Step 3's finding).

- [ ] **Step 6: Build and present comparison report; confirm applying Task 23's approach**

- [ ] **Step 7: Relink via batch edit, or build composite footprint then relink**

Same conditional as Task 23 Step 7.

- [ ] **Step 8: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 9: Verify**

Reopen, confirm new footprint. `run_drc` count drops by 1. If option (b), confirm the 3D stack visually.

- [ ] **Step 10: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table KiCad/IC_Socket_Custom.pretty
git commit -m "$(cat <<'EOF'
Relink U12 (74LS373 20-pin DIP) to <official Package_DIP footprint OR
composite IC_Socket_Custom footprint, matching the Task 23 approach>

<width confirmed against datasheet>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 27: ICs — 24-pin DIP (`IC_DIP24_600`, U4/U13)

**Files:**
- Modify: sheet(s) confirmed in Step 1
- Possibly create/modify: `KiCad/IC_Socket_Custom.pretty/`, `KiCad/fp-lib-table` — only if Task 23 Step 6 chose option (b)

**Interfaces:**
- Consumes: the 3D-model approach decided in Task 23 Step 6.

- [ ] **Step 1: Locate U4, U13**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}`, filter to U4/U13.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for U4.

- [ ] **Step 3: Confirm package width**

U4 is Intel 8253 PIT, U13 is 74198 shift register (README.md:201, 208); WebSearch both datasheets to confirm 600mil.

- [ ] **Step 4: Fetch the socket's real mechanical dimensions**

Per the "IC socket BOM data" table: 24-pin socket is Mouser `649-DILB24P-223TLF` / `517-4824-6000-CP`. WebSearch "DILB24P-223TLF datasheet" and record its stack height. (Skip if Task 23 chose (a)/(c).)

- [ ] **Step 5: Search official KiCad libraries for the pad pattern**

`mcp__kicad__search_footprints` with `search_term: "DIP-24_W15.24mm"` in library `Package_DIP`.

- [ ] **Step 6: Build and present comparison report; confirm applying Task 23's approach**

- [ ] **Step 7: Relink via batch edit, or build composite footprint then relink**

Same conditional as Task 23 Step 7.

- [ ] **Step 8: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 9: Verify**

Reopen, confirm new footprint for both refs. `run_drc` count drops by 2. If option (b), confirm the 3D stack visually.

- [ ] **Step 10: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table KiCad/IC_Socket_Custom.pretty
git commit -m "$(cat <<'EOF'
Relink U4/U13 (24-pin DIP ICs) to <official Package_DIP footprint OR
composite IC_Socket_Custom footprint, matching the Task 23 approach>

<package width confirmed against 8253/74198 datasheets>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 28: ICs — 28-pin DIP (`IC_DIP28_600`, U3/U9/U10/U11)

**Files:**
- Modify: sheet(s) confirmed in Step 1
- Possibly create/modify: `KiCad/IC_Socket_Custom.pretty/`, `KiCad/fp-lib-table` — only if Task 23 Step 6 chose option (b)

**Interfaces:**
- Consumes: the 3D-model approach decided in Task 23 Step 6.

- [ ] **Step 1: Locate U3, U9, U10, U11**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}`, filter to U3/U9/U10/U11.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for U3.

- [ ] **Step 3: Confirm package width**

U3 is 8251A USART, U9 is AS6C62256 SRAM, U10/U11 are 2716 EPROM equivalents (README.md:200, 205, 206); WebSearch all three distinct datasheets (8251A, AS6C62256, and note the README's stated substitute AT28C64B for the EPROM slot) to confirm 600mil for all.

- [ ] **Step 4: Fetch the socket's real mechanical dimensions**

Per the "IC socket BOM data" table: 28-pin socket is Mouser `649-DILB28P223TLF` / `517-4828-6000-CP`. WebSearch "DILB28P223TLF datasheet" and record its stack height. (Skip if Task 23 chose (a)/(c).)

- [ ] **Step 5: Search official KiCad libraries for the pad pattern**

`mcp__kicad__search_footprints` with `search_term: "DIP-28_W15.24mm"` in library `Package_DIP`.

- [ ] **Step 6: Build and present comparison report; confirm applying Task 23's approach**

- [ ] **Step 7: Relink via batch edit, or build composite footprint then relink**

Same conditional as Task 23 Step 7.

- [ ] **Step 8: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 9: Verify**

Reopen, confirm new footprint for all 4 refs. `run_drc` count drops by 4. If option (b), confirm the 3D stack visually.

- [ ] **Step 10: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table KiCad/IC_Socket_Custom.pretty
git commit -m "$(cat <<'EOF'
Relink U3/U9/U10/U11 (28-pin DIP ICs) to <official Package_DIP
footprint OR composite IC_Socket_Custom footprint, matching the
Task 23 approach>

<package width confirmed against 8251A/AS6C62256 datasheets>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 29: ICs — 40-pin DIP (`IC_DIP40_600`, U1/U5/U6/U7/U8)

**Files:**
- Modify: sheet(s) confirmed in Step 1
- Possibly create/modify: `KiCad/IC_Socket_Custom.pretty/`, `KiCad/fp-lib-table` — only if Task 23 Step 6 chose option (b)

**Interfaces:**
- Consumes: the 3D-model approach decided in Task 23 Step 6.

- [ ] **Step 1: Locate U1, U5, U6, U7, U8**

`mcp__kicad__list_schematic_components` with `{"referencePrefix": "U"}`, filter to U1/U5/U6/U7/U8.

- [ ] **Step 2: Pull current geometry**

`get_component_properties` + `get_component_pads` for U1.

- [ ] **Step 3: Confirm package width**

U1 is Intel 8080A CPU, U5/U6 are 8255A PPI, U7 is 8257 DMA controller, U8 is 8275 CRTC (README.md:198, 202-204) — all standard 600mil 40-pin DIP for the Intel 8080 family; WebSearch "8080A datasheet DIP-40" to confirm.

- [ ] **Step 4: Fetch the socket's real mechanical dimensions**

Per the "IC socket BOM data" table: 40-pin socket is Mouser `649-DILB40P223TLF` / `517-4840-6000-CP`. WebSearch "DILB40P223TLF datasheet" and record its stack height. (Skip if Task 23 chose (a)/(c).)

- [ ] **Step 5: Search official KiCad libraries for the pad pattern**

`mcp__kicad__search_footprints` with `search_term: "DIP-40_W15.24mm"` in library `Package_DIP`.

- [ ] **Step 6: Build and present comparison report; confirm applying Task 23's approach**

- [ ] **Step 7: Relink via batch edit, or build composite footprint then relink**

Same conditional as Task 23 Step 7.

- [ ] **Step 8: Forward-annotate**

User runs F8; confirm.

- [ ] **Step 9: Verify**

Reopen, confirm new footprint for all 5 refs. `run_drc` count drops by 5 — this should be the last `lib_footprint_issues` entry, bringing the total to 0 (only the unrelated `starved_thermal`/`silk_edge_clearance` items remain, out of scope). If option (b), confirm the 3D stack visually.

- [ ] **Step 10: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add KiCad/*.kicad_sch KiCad/Radio-86RK.kicad_pcb KiCad/fp-lib-table KiCad/IC_Socket_Custom.pretty
git commit -m "$(cat <<'EOF'
Relink U1/U5/U6/U7/U8 (40-pin DIP ICs) to <official Package_DIP
footprint OR composite IC_Socket_Custom footprint, matching the
Task 23 approach>

<package width confirmed against 8080A datasheet>

This is the last unresolved My_Components reference in the project -
all lib_footprint_issues DRC errors from the original component audit
are now resolved.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 30: Final Wrap-Up

**Files:**
- Modify: `CLAUDE.md`
- Delete (project-local `fp-lib-table` entry for `My_Components`, only if it was ever added — confirm first): `KiCad/fp-lib-table`

**Interfaces:**
- Consumes: the completion state of Tasks 2-29.

- [ ] **Step 1: Run a full-project DRC and confirm zero `lib_footprint_issues`**

Call `mcp__kicad__run_drc`. Confirm the only remaining violations are the 6 pre-existing `starved_thermal` errors and 17 `silk_edge_clearance` warnings noted in Task 1 — both explicitly out of scope for this plan.

- [ ] **Step 2: Update CLAUDE.md**

Edit the "Footprint library setup" section: remove the `My_Components` "not yet resolved" bullet (it's now fully resolved — every reference that used it has been relinked), and add one line summarizing that all discrete/connector/IC components now use official KiCad libraries (list them: `Capacitor_THT`, `Diode_THT`, `Package_TO_SOT_THT`, `LED_THT`, `MountingHole`, `Resistor_THT` (for the SIP arrays), `Connector_PinHeader_2.54mm`, `Connector_PinSocket_2.54mm`, `Connector_IDC`, `Connector_Dsub`, `Connector_Audio`/`Connector` (RCA/DC jack), `Crystal`, `Converter_DCDC`, `Button_Switch_THT`, `Package_DIP`), plus any project-local custom footprints created along the way (J4 DIN jack and/or SP1 speaker, if Tasks 14/21 concluded no official match existed; `IC_Socket_Custom.pretty`, if Task 23 chose option (b) for the DIP socket/chip 3D stack — document the socket-height source per pin count so a future case-design pass doesn't have to re-derive it).

- [ ] **Step 3: Present the verified result and wait for explicit human approval, then commit**

Show the user the prior step's verification output (updated component list, DRC count, and any 3D-view check) and wait for an explicit go-ahead in the conversation (e.g. "looks good", "commit") before running anything below. Do not run `git commit` on your own initiative just because the automated verification passed.

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
Document completion of My_Components footprint migration

Every component that referenced the unresolved My_Components library
nickname has now been relinked to an official KiCad library footprint
(or, where none existed, a project-local custom one). Update CLAUDE.md
to remove the stale "not yet resolved" note and list the final set of
libraries in use.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

**Spec coverage:** All 28 remaining unresolved `My_Components` footprints from the survey are covered: Tasks 2-3 (capacitors, 2 footprints), 4 (diodes), 5 (transistors), 6 (LEDs), 7 (holes), 8-17 (connectors, 10 footprints including the two SIP resistor-array footprints per the user's explicit "review connectors one by one"), 18-22 (other/misc, 5 footprints), 23-29 (ICs, 7 DIP sizes). Task 1 establishes the baseline; Task 30 closes out documentation. Ordering matches the user's explicit request (simple passives → connectors individually → other components → ICs last).

**IC socket vs. chip reevaluation:** Per user feedback, Tasks 23-29 were revised from a plain footprint-name swap into a two-part decision: the README BOM lists a separate "IC Socket" line item per DIP size (README.md:223-229, its own Mouser P/N, its own real stack-height dimension) distinct from the chip that plugs into it. A straight swap to `Package_DIP:DIP-N_W*mm` only carries one IC-body 3D model sitting flush on the board — physically wrong for this project's FreeCAD case-clearance goal, since the real assembly is PCB → socket → chip, not PCB → chip. Task 23 (8-pin, first IC task) now researches the socket's real dimensions and decides once, with explicit user sign-off, between (a) accept the flush official footprint, (b) build a composite footprint with two Z-offset 3D models (socket + elevated chip, the same compositing technique already used for the SW11/SW64 stabilizers, commit `daacbd7`), or (c) defer. Tasks 24-29 apply that single decision with their own pin-count-specific socket data rather than re-deciding it seven times.

**Placeholder scan:** Footprint *names* to relink to are intentionally left as research outcomes (Step 3-5 of each task determine them from real datasheets, not assumed) — this is not a placeholder in the forbidden sense, since the plan specifies the exact, concrete procedure (which search terms, which libraries, which datasheets) that produces the answer, and requires a presented comparison report + explicit user confirmation before any edit. Commit message bodies use `<...>` fill-ins for the same reason — the specific footprint name and justification are Task Step 5's (or, for ICs, Step 6's) output, known only after that step runs.

**Type/interface consistency:** Every task uses the same four MCP tool names throughout (`list_schematic_components`, `get_component_properties`, `get_component_pads`, `batch_edit_schematic_components`, plus `search_footprints`/`get_footprint_info` for research and `run_drc`/`get_component_list`/`open_project` for verification) — matching the exact tool names used and proven working in the resistor migration (commit `5dabaf9`). No task invents a new tool name without first calling `get_category_tools` to confirm it exists (see Task 7 Step 5b, the one path — PCB-only mounting holes — not already exercised).

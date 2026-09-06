# KiCad 10 modernization — outcome

| Metric | Before | After |
|---|---:|---:|
| Board file format | KiCad 6 (`20211014`), CRLF | KiCad 10 (`20260206`), LF |
| Schematic format | KiCad 6 (`20211123`) | KiCad 10 (`20260306`) |
| ERC violations | 243 | **32**, 0 errors, documented |
| DRC violations | 91 | **22**, 0 errors, documented |
| Unconnected items | 0 | **0** |
| Schematic/board parity | 0 | **0** |
| Components rendering in 3D | 0 / 183 | **183 / 183** |
| Gerber + drill diff vs v1.4 | — | **empty** |
| Opens from a fresh clone | no | **yes** |

## What changed on the board

**Nothing.** All 191 footprints, all copper, every drill hole and all silkscreen are
identical to skiselev's v1.4 output. The gerber and drill diff is empty, with no exception
anywhere in the project.

That is not an assertion — `tools/gerber-gate.sh` checks it against a baseline frozen from
the board before any edit, and it was run after every one of the nine commits that touched
`KiCad/`.

The design spec had proposed one authorized copper change: adopting perigoso's Cherry MX
footprints across the keyboard, on the grounds that doing so "brings a 3D model". That
premise turned out to be false — 3D models attach to any footprint by name, and both
libraries put the switch's centre guide boss at (0, 0), so perigoso's model renders
correctly on the board's own geometry. Declining the substitution avoided a 2.286 → 2.5 mm
pad growth on 67 switches, a compensating schematic pin swap, two clearance violations at
0.150 mm, and the loss of SW11 and SW64's stabilizer holes — at a cost of nothing but
silkscreen cosmetics.

## What changed everywhere else

- **File formats** upgraded to KiCad 10 (schematics in the GUI, board via `kicad-cli`).
- **All 35 footprints vendored** from the board into `KiCad/Radio86RK.pretty`. `Cherry_MX`
  is lost upstream, so the board is the only authority for it; extracting from the board
  makes library-vs-board identity true by construction.
- **Symbols re-homed to public libraries.** Every mismatching symbol was one of KiCad's own
  stock symbols that drifted since KiCad 4, and `Device:Q_NPN_EBC` had merely moved to
  `Transistor_BJT`. Nothing needed a custom symbol.
- **`my_components` vendored** so no sibling checkout is required.
- **3D models on all 183 components**, including socket+chip composites on all 24 socketed
  DIP ICs and switch+stabilizer composites on the two wide keys. Seven parts KiCad has no
  model for — the RCA, the DIN-8, the barrel jack, the MTA header, the speaker, the tactile
  switch and the DC-DC brick — use manufacturer STEP files recovered from the abandoned
  `migrate2kicad10` branch, vendored into `KiCad/Radio86RK.3dshapes/`.

## What was deliberately not done

| | Why |
|---|---|
| 22 DRC violations | Properties of the v1.4 board. Fixing means moving silkscreen or zone geometry. See `docs/drc-exclusions.md`. |
| 32 ERC violations | Bus signals carrying both label scopes. Clearing them costs 91 label edits for 0 errors — measured, not estimated. See `docs/erc-exclusions.md`. |
| U3/U22 RS-232 defect | Pre-existing v1.4 design defect, GitHub issue #2. Fixing it is a topology change. |

## How to verify any of this yourself

```bash
tools/gerber-gate.sh --strict    # copper unchanged vs the frozen v1.4 baseline
tools/netlist-gate.sh            # no pin moved to a different net
tools/rules-report.sh            # ERC and DRC counts by type
tools/render.sh mycheck          # 3D render into verify/renders/
"$KICAD_PY" tools/model_coverage.py "$PCB"   # 3D coverage, resolving models only
```

All of it was re-run from a fresh `git clone` into a scratch directory and produced
identical results, which is what makes "works standalone" a checked claim rather than a
hope.

## Requirements

KiCad 10.0.4, plus the **perigoso keyswitch library** installed via KiCad's Plugin and
Content Manager — that supplies the Cherry MX switch and stabilizer 3D models. Nothing else
external; all footprints and symbols the project needs are in the repository.

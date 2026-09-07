# Radio-86RK — working notes for agents

What this project *is*: see [README.md](README.md). This file is how to **work in it**.

## Start here — ask before modifying

Establish with the user, before changing anything:

1. **What are we changing?** schematic · layout/copper · footprints or symbols · 3D models
   · firmware · documentation · tooling · nothing (read-only)
2. **Should the manufacturing output change as a result?**
   **No** — the change must be output-neutral · **Yes, deliberately** — routing, pads or
   drill will move and the baseline gets recaptured · **Unknown** — find out and report
   before committing anything
3. *Only if 2 is "yes":* **is this heading for a released revision?** If so the work
   includes regenerating `gerber/`, updating the release notes in `README.md`, tagging `v1.x`.

**If the request already answers these, restate your understanding in one line and
proceed.** Never re-ask what the user just told you.

## The safe change loop

Run `python3 tools/kicad-verify.py all` **before and after** the change, then read the
second result against what you declared in question 2:

| Declared | Result | Means |
|---|---|---|
| no output change | exit 0 | as intended |
| no output change | exit 1 | unintended side effect — investigate before committing |
| output should change | exit 0 | **the edit did nothing** — also a defect |
| output should change | exit 1 | expected — review the diff, recapture, commit the reason |

**Exit 2 means the gate could not run.** It is never a verdict on the board. Full
contract: [tools/README.md](tools/README.md).

## Repo map

- `KiCad/` — the design: board, main schematic + 4 sub-sheets, project file, v1.4 PDFs
- `tools/` — the verification harness, stdlib only
- `verify/baseline/` — harness reference: 22 canonicalised exports + netlist + `meta.json`
- `gerber/` — **published** fab output: 7 `.gbr`, `NPTH.drl`, `PTH.drl`, `gerber.zip`
- `Documentation/` — component datasheets · `Software/` — firmware · `images/` — README photos
- `docs/` — decision records · `Project_Notes.md`, `Radio-86RK_Publications.md` — background

`gerber/` and `verify/baseline/strict/` are **not comparable**: different layer sets,
different extensions, and `gerber/` splits drill into NPTH/PTH where the baseline has one
merged `.drl`. Never diff one against the other.

## Facts

- **Two interpreters.** The harness runs on any Python 3.8+. `pcbnew` work needs KiCad's
  own bundled interpreter — see `kicad-scripting`.
- **Fork.** `origin` is this fork; `upstream` is `skiselev/radio-86rk`. Each workstream
  lands as **one commit**: squash before merging, merge before pushing. Pushed history
  is not rewritten — that ordering is what lets both rules hold.
- **Archive.** `archive/kicad10-3d-2026-09-06` holds KiCad 10 and 3D work not yet on master.

## Skills

`changing-the-schematic` · `changing-the-layout` · `kicad-scripting` ·
`workstream-lifecycle` · `agent-review-policy`

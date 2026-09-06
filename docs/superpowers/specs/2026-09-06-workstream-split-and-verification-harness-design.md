# Workstream split and verification harness — design

**Date:** 2026-09-06
**Status:** approved for planning

## Why this exists

The `kicad10-modernization` branch grew 50 commits carrying four unrelated concerns: a
verification harness, the KiCad 10 conversion and 3D model work, a mechanical export for
case design, and a pile of process documentation. Merging that as one change would put
generic tooling, a board deliverable and an agent's working notes on master together.

This document does two things: it splits the work into four independent workstreams, and it
designs the first of them in full. The other three get their own design cycles when their
turn comes.

## Constraints

These come from the repository owner and bound every decision below.

- **Master is production ready.** Nothing lands unpolished on the promise that it will be
  cleaned up later.
- **One pipeline: this fork's master.** Upstream PRs to skiselev are attempted
  opportunistically. They are welcome but never a blocker, and no design is contorted to
  suit them.
- **The repository will be published** for other people to use, so the documentation bar is
  a stranger's, not the author's.
- **The board is frozen.** Gerber and drill output must stay byte-identical to skiselev's
  v1.4. This is the invariant the harness exists to defend.

---

# Part 1 — The split

## Preservation

The work must survive the split intact, and that has to be a mechanism rather than an
intention. Five rules, all of them checkable.

**1. The archive exists as both a branch and a tag, both on `origin`.**
`kicad10-modernization` was local-only until 2026-09-06 — 51 commits on a single machine,
alongside the unpushed `sw3-official-reroute-experiment` branch and the `dv-finish-3d-models`
tag. It is now pushed. At the moment the split begins, its final commit is also tagged
`archive/kicad10-3d-2026-09-06` and that tag is pushed. Branches move; tags do not. The tag
is created when the split starts, not before, so it captures the true final state.

**2. Master is untouched until a workstream is finished and reviewed.** Each workstream is
branched from master, developed to completion, reviewed, then merged. No partial merges, no
staging work on master.

**3. Workstream branches are not deleted after merging.** They survive until D completes.

**4. The no-loss invariant.** After B merges:

```
git diff archive/kicad10-3d-2026-09-06 master -- KiCad/
```

must be **empty**. That is objective proof the board, schematics, footprints and 3D models
came through the split byte-identical. `tools/` and `docs/` will legitimately differ — A
rewrites the first, the split distils the second — but `KiCad/**` is the irreplaceable part,
and it either survived unchanged or it did not.

**5. The gates run on master after every merge.** Master is never left in a state where the
copper claim is unverified.

## The four workstreams

Each is branched from master after the previous one merges.

| | Branch | Contains | Derived from |
|---|---|---|---|
| **A** | `harness` | `tools/kicad-verify.py`, `tools/kicadverify/`, fixtures, harness README, `verify/baseline/` | `gerber-gate.sh`, `netlist-gate.sh`, `rules-report.sh`, `gerber_canon.py`, `kicad-env.sh` |
| **C** | `agent-flows` | `CLAUDE.md`, project skills, project rules | the archive's lessons, plus A's contract |
| **B** | `kicad10-3d` | `KiCad/**`, model tooling, `render.sh`, `model_coverage.py`, README section, three distilled docs, cited renders | the archive |
| **D** | `freecad-case` | `export-mech.sh`, keycaps, the case model | seeded by `followup-3d-models.md` |

**Order: A → C → B → D.** A first because B's central claim — copper unchanged — is only
checkable with A's tools, and because A is verifiably independent: its five files were run
against an untouched master worktree with nothing from B present, and reproduced the
committed baseline byte-for-byte, including a DRC total of 212 that matches the recorded
v1.4 reference. C second because agent rules should exist before the largest change lands.
D last.

B being third means finished, verified work waits behind two new workstreams. This is a
deliberate trade for a production-ready master. B remains extractable from the archive at
any time, since nothing in it depends on A.

## Where the documentation goes

Nothing in `docs/` moves to master as it stands. Of 3,216 lines, roughly 2,900 are process.

| File | Lines | Destination |
|---|---:|---|
| `superpowers/plans/2026-09-04-…` | 2174 | archive only; raw material for C |
| `superpowers/specs/2026-09-04-…` | 348 | archive only |
| `superpowers/specs/2026-09-06-…` (this document) | 385 | archive only; read from the tag while executing A |
| `3d-model-sources.md` | 394 | **distilled** into B |
| `followup-3d-models.md` | 86 | archive only; becomes D's brief |
| `modernization-summary.md` | 76 | archive only; becomes B's PR description |
| `drc-exclusions.md` | 67 | distilled into B |
| `erc-exclusions.md` | 71 | distilled into B |
| `verify/rules-*.txt` (6 files) | — | archive only |

Distilled means rewritten, not copied. `3d-model-sources.md` is roughly half decision record
and half narrative of how those decisions were reached; only the first half belongs on
master.

## Reassignments

- **The baseline travels with A**, not B. It is A's data, and A can capture it standalone
  from untouched master.
- **`export-mech.sh` moves to D.** It was committed into the current stack but concerns
  neither verification nor KiCad 10.
- **`vendor_footprints.py` is spent.** A one-shot migration script; archive, do not merge.

---

# Part 2 — Workstream A: the verification harness

## Purpose

Prove that a change to a KiCad project did not move copper, did not alter connectivity, and
did not change ERC/DRC counts — on macOS, Linux and Windows, for a human or an agent.

## Requirements

1. Simple, reusable scripts running on macOS, Linux and Windows.
2. Instructions as simple as possible.
3. As autonomous as possible without extra complexity.
4. Very good error, warning and progress messaging, for human **and** agent readers.
5. Ready for a later CI step, which is out of scope here.

## Key finding: no `pcbnew` dependency

Every file that imports `pcbnew` belongs to B. A's only Python file, `gerber_canon.py`,
imports `re` and `sys` — standard library only.

A's entire dependency list is therefore **`kicad-cli` plus any Python 3**.

This matters because locating KiCad's Python is the hardest part of cross-platform support:
it is bundled inside the application on macOS and Windows, but on Linux `pcbnew` is a
distribution package inside the system interpreter. A sidesteps the problem completely. It
also means `KICAD_PY`, which A's scripts currently carry, is dead weight.

## The kicad-cli contract

The entire surface A depends on:

| Subcommand | Used by |
|---|---|
| `pcb export gerbers`, `pcb export drill` | gerber gate |
| `sch export netlist` | netlist gate |
| `pcb drc` | rules report |
| `sch erc` | rules report |

Flags: `--output`, `--format`, `--severity-all`.

## Architecture

One launcher plus one package, standard library only.

```
tools/kicad-verify.py          launcher: python3 tools/kicad-verify.py <command>
tools/kicadverify/
    __main__.py                argparse, subcommands, exit codes
    discover.py                locate kicad-cli and the project, per OS
    report.py                  progress, verdicts, --json, noise filtering
    canon.py                   the gerber canonicaliser
    gerber.py                  export, canonicalise, compare
    netlist.py                 export, compare nets
    rules.py                   ERC and DRC counts
    selftest.py                fixture checks
tools/fixtures/                tiny gerbers for selftest
```

**Why a package rather than one file.** The rewrite lands near 500–700 lines. The
canonicaliser defines what "same copper" means and deserves to be readable on its own rather
than buried inside a CLI.

**Why a launcher rather than `python -m`.** `python3 tools/kicad-verify.py gerber` is the
identical instruction on all three platforms (`py` in place of `python3` on Windows). No
shebang, no `PATH`, no `PYTHONPATH`, no install step.

## Commands

| Command | Purpose |
|---|---|
| `doctor` | Is kicad-cli found, which version, which project, is there a baseline |
| `baseline [--force]` | Capture the frozen reference |
| `gerber [--geometry]` | Copper and drill gate |
| `netlist` | Connectivity gate |
| `rules` | ERC and DRC counts by type |
| `all` | Everything, one verdict |
| `selftest` | Canonicaliser fixture checks |

`doctor` is new. Most real-world failures are environmental — KiCad missing, wrong version,
no project found, no baseline captured — and both humans and agents should be able to ask
one question and get a straight answer rather than inferring it from a gate that failed for
the wrong reason. It exits 0 when everything needed is present and 2 when anything is
missing, so it can be used as a precondition check rather than only read as prose.

`all` runs `gerber`, `netlist` and `rules`, in that order, and prints one verdict line per
gate followed by a combined verdict. It does not stop at the first failure — a run should
report everything that is wrong, not just the first thing. It does **not** run `selftest`,
which tests the tool rather than the project. Its exit code is 1 if any gate failed and 2 if
the environment prevented a gate from running, with 2 taking precedence: not having run is a
more important fact than having failed.

## Discovery

**kicad-cli**, in order, stopping at the first that runs:

1. `$KICAD_CLI` if set
2. `kicad-cli` on `PATH`
3. Per-OS known locations:
   - macOS: `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
   - Windows: `C:\Program Files\KiCad\<version>\bin\kicad-cli.exe`, highest version found
   - Linux: `/usr/bin`, `/usr/local/bin`, plus flatpak and snap wrappers

On failure the error names every path tried and says to set `KICAD_CLI`.

**Project:** `--project` if given, otherwise glob the repository root for `*.kicad_pcb`.
Exactly one match is used; several produce an error listing them. The schematic is the
sibling `.kicad_sch` with the same stem. Repository root comes from
`git rev-parse --show-toplevel`, falling back to the working directory so git is not
required.

**Configuration** is environment variables and flags only. No configuration file, and no
install or packaging step.

**Repository-agnostic.** No project name appears anywhere in the code. The baseline defaults
to `verify/baseline/` and accepts `--baseline-dir`. Dropping the launcher and package into
another KiCad repository is sufficient to use it there.

## Version handling

Compare **major versions only**.

| Condition | Behaviour |
|---|---|
| major < 10 | Fail, exit 2: *"requires KiCad 10 or newer, found 9.0.1"* |
| major differs from the baseline's major | Warn — the yellow flag |
| same major, any patch | Silent |

Patch-level differences are not flagged. Warning on 10.0.4 against 10.0.5 would be noise,
and a flag that fires on every patch release is one people learn to ignore. Emitter changes
arrive with major releases.

The warning is deliberately not a distinct exit code. It is a yellow flag that obliges the
reader — human or agent — to consult the KiCad changelog and confirm the difference is an
emitter change rather than a real one.

## Baseline

Contents: the 22 canonicalised gerber and drill files, `netlist.nets`, and `meta.json`
recording the KiCad version, capture date, source commit and project file.

`meta.json` exists so version drift is detectable at all, and so a later capture can be made
from the same commit rather than from a master that has moved on.

`baseline --force` is required to overwrite an existing baseline, and reports what it is
replacing.

**The `geometry` variant:** keep `--geometry` in code, do not commit its baseline. It has
never been used — every task so far kept nets identical — and it is half of the 15 MB.
`meta.json` records the source commit, so it can be captured from exactly the same commit
when a task genuinely needs it.

**The `strict` baseline stays committed.** A baseline regenerated on demand can be
regenerated *after* a mistake, which silently erases the evidence it exists to preserve. A
committed one cannot be quietly re-derived; changing it appears as a diff.

## Messaging contract

| Stream | Audience | Content |
|---|---|---|
| stderr | human | Progress: `[gerber] exporting…`, `[gerber] 22 files canonicalised`; on failure, the differing files and hunks |
| stdout | both | One stable verdict line per gate |
| `--json` | agent | Full structure in place of the verdict line |

Verdict lines:

```
PASS  gerber   22 files identical
FAIL  gerber   3 files differ: F_Cu.gtl, B_Cu.gbl, Edge_Cuts.gm1
FAIL  gerber   3 files differ  [VERSION-DRIFT baseline=10.0.4 running=11.0.1
                                differences may be emitter changes — check the KiCad changelog]
```

In `--json`, drift appears as fields: `"version_drift": true`, `"baseline_kicad"`,
`"running_kicad"`. The flag must reach an agent through structured output, not only through
prose.

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Pass |
| 1 | A gate failed |
| 2 | Environment or usage problem |

Separating 1 from 2 is the most important property for agent use. "The board changed" and
"I could not run the check" are different facts; today's shell scripts conflate them, and an
agent that cannot distinguish them will report a false regression.

**Failures are actionable.** *"kicad-cli not found. Set KICAD_CLI=/path/to/kicad-cli or
install KiCad 10"* rather than a stack trace.

**Noise filtering** lives in one place, is a documented list rather than a mystery, and
`--verbose` shows everything it would otherwise drop. Two known sources: Homebrew fontconfig
warnings, and a macOS `NSCocoaErrorDomain 260` message emitted when kicad-cli stats an
output file before creating it.

## selftest

Fixture gerbers under `tools/fixtures/`, asserting the three properties that were checked by
hand during the original work but never encoded:

1. A file re-emitted with reordered commands and renumbered aperture D-codes canonicalises
   **identically** — no false alarms.
2. A file with one pad moved by 1 µm canonicalises **differently** — no missed regressions.
3. `G36`/`G37` region fills survive verbatim — the case a naive line-sort would silently
   corrupt.

No test framework and no dependency. `kicad-verify selftest` runs in about a second.

## Proving the rewrite

The port is not finished until the Python produces byte-identical output to the shell
scripts it replaces.

Run both implementations against untouched master and require the captured baselines to be
byte-identical and the verdicts to agree. This experiment has already been run on the shell
side twice: `strict`, `geometry` and `netlist.nets` all reproduce from master's original
KiCad 6 board, and `rules` reports DRC 212 there — 190 `lib_footprint_issues`, 17
`silk_edge_clearance`, 5 `starved_thermal` — matching the recorded v1.4 reference.

## Documentation

A harness README covering: what each command does, the three exit codes, how to run it on
each platform, how to point it at a different project, and what the version warning means.

Written for a stranger, since the repository will be published.

## Explicitly out of scope

Recorded in the plan as future steps, not built here.

- **CI / GitHub Actions** running the gates on push. Requires a runner with KiCad 10
  installed, which pins a version and is its own piece of work.
- **Packaging** or extraction into a standalone reusable component.
- **Any test framework** beyond `selftest`.

---

# Part 3 — Later workstreams, scope only

These are recorded so the decomposition is complete. Each gets its own design cycle.

## C — agent flows

`CLAUDE.md`, project-specific skills and rules, authored from the archive. Expected content:
the frozen-copper rule and when to run A's gates; KiCad-specific traps found the hard way
(use KiCad's Python for `pcbnew` work, never the system one; zsh does not word-split
unquoted variables; the 3D model offset inverts Y but not rotation; the gates are silent on
3D placement, so look at the render); and the recurring failure mode of this project — an
unexamined premise, reasonable by analogy and wrong on inspection.

Some of C's rules will describe constraints on work that has not landed yet. Rules about A's
gates apply immediately; rules about the board's model conventions land before the models do.

## B — KiCad 10 and full 3D

The board, five schematics, project file, two library tables, `Radio86RK.kicad_sym`, 35
vendored footprints, 7 manufacturer STEP models; `models.tsv` with `apply_models.py`,
`align_models.py`, `align_models_legacy.py`; `model_coverage.py` and `render.sh`; the README
section; three distilled documents; the cited renders. Board and schematic content is
already complete and verified in the archive.

## D — FreeCAD case

`export-mech.sh` moved from the archive, keycaps, and the case model itself. Brief is
`followup-3d-models.md`: DSA profile via the MIT-licensed `anhthang/dsa-keycap` STEP set,
which covers all five sizes this board needs; caps placed from `placement.csv` rather than
baked into the board.

---
name: kicad-scripting
description: Use when writing or running scripts against this KiCad project — anything importing pcbnew, driving kicad-cli, or extending the verification harness. Covers which Python interpreter is required and why, what the gates can and cannot see, and the shell traps in this repo.
---

# Scripting against this KiCad project

## Two interpreters, and they are not interchangeable

| Doing this | Use |
|---|---|
| Running or extending `tools/kicadverify/` | any Python 3.8+, including the system one |
| Anything that `import pcbnew` | **KiCad's own bundled interpreter** |

`pcbnew` is a compiled extension module built against the Python that ships inside KiCad.
A system interpreter cannot import it — not with `pip`, not with a virtualenv, not at all.

The harness deliberately avoids the whole problem. From `tools/kicadverify/discover.py:3`:

> The harness needs no pcbnew, which is what makes this tractable: KiCad's Python is
> bundled inside the application on macOS and Windows but is a distribution package on
> Linux, and there is no portable way to find it. kicad-cli is an executable, and an
> executable can be found by looking.

### There is no discovery mechanism on master, on purpose

`discover.py` resolves `kicad-cli` only. `KICAD_PY` is referenced nowhere in the
repository. This is not an oversight — as the comment above says, no portable way to find
KiCad's Python exists, so the harness was built to need none.

**Consequence: if you write the next `pcbnew` script, you must bring your own way to
locate the interpreter.** The archive pinned it for macOS in `tools/kicad-env.sh`:

```
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
```

That path is macOS-specific and version-specific. On Linux, KiCad's Python is a
distribution package and the layout differs by distro. Do not assume the macOS path works
anywhere else, and do not present a hardcoded path as portable.

Four scripts in the archive need it — `align_models.py`, `align_models_legacy.py`,
`apply_models.py`, `model_coverage.py` — and they arrive on master with workstream B.

## What the gates see

`python3 tools/kicad-verify.py all` compares 22 exported files plus the netlist:

copper (`F_Cu`, `B_Cu`) · mask · silkscreen · paste · adhesive · courtyard · fab ·
margin · four user layers · edge cuts · the merged drill file · every pin-to-net mapping ·
ERC and DRC counts.

## What the gates are blind to

- **3D models entirely** — presence, orientation, placement, whether a part is sunk into
  the board or floating above it. No gate will ever report this.
- **Mechanical fit** — connector positions relative to a case, keepout clearance in Z.
- **Whether silkscreen is *legible*** — the gate catches whether silk *changed*; it cannot
  judge a label overlapping a pad or set too small to read.
- **Bill-of-materials correctness** — the gate reads geometry, not part numbers.

This list matters more than the previous one. A passing gate says nothing about 3D, and
that silence is easy to mistake for approval.

**For anything 3D, look at a render.** `kicad-cli` can produce one without opening the GUI:

```
kicad-cli pcb render --help
```

## Shell traps in this repo

The interactive shell on this machine is zsh, which differs from bash in ways that have
already cost commands during this project's own development:

- **`:` in an unbraced parameter expansion is a history modifier.**
  `"$T:tools/file"` silently becomes `<basename of $T>ools/file`, because zsh reads `:t`
  as "tail". Write `"${T}:tools/file"`.
- **Unquoted globs that match nothing are a hard error**, not a pass-through.
  `grep --include=*.py` fails with `no matches found` before grep ever runs. Quote it:
  `grep --include='*.py'`.

Both are zsh-on-macOS specifics. On a bash host neither applies.

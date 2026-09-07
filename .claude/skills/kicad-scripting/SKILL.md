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
repository. That was true when the harness was written: it needs no `pcbnew`, so it could
decline the problem entirely.

**Master now solves it.** `discover.py` carries `py_candidates()` and `find_py()`, built
the way `kicad-cli` discovery already was: an ordered candidate list plus a probe. There
is no single portable *rule*, but a list is portable enough. The probe is the only test
that means anything, because a version string proves nothing about whether the module is
there:

```
<candidate> -c "import pcbnew"      ->  exit 0
```

Use it through the harness rather than re-implementing it:

```
python3 tools/kicad-verify.py run tools/align_models.py
```

`run` finds the interpreter and executes the script under it, passing stdout, stderr and
the exit code straight through. `KICAD_PY` overrides discovery and is authoritative when
set: if it fails, that is reported rather than silently falling through to some other
interpreter that would hide the problem.

On macOS the candidates are globbed from `Python.framework/Versions`, newest first,
rather than pinned — the archive hardcoded `3.9`, which breaks the release KiCad ships a
newer one. **The Linux branch is unverified**: no Linux machine has run it. There
`pcbnew` is a distribution package importable from the system interpreter, which is why
it generalises at all, but a flatpak or snap install keeps it inside the sandbox where no
path reaches it. `KICAD_PY` is the answer in that case, and the failure message says so.

Four scripts need it: `align_models.py`, `align_models_legacy.py`, `apply_models.py` and
`vendor_footprints.py`.

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

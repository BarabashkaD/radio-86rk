---
name: verifying-3d-models
description: Use when changing, adding or checking 3D models on this board, or when a render looks wrong. Covers what the gates cannot see, how to spend render tokens well, and why missing parts are usually the PCM package rather than the design.
---

# Verifying 3D models

## What the gates cannot see

`python3 tools/kicad-verify.py all` proves copper, drill and connectivity. It says
**nothing whatever about 3D models**. A model can be the wrong part, at the wrong scale,
rotated 90°, or sunk into the board, and every gate still passes.

`python3 tools/kicad-verify.py models` closes half the gap: it proves a model file
*resolves*. It never proves the model is right.

```
3D coverage 183 / 183 footprints   (exempt 8)
```

183 is footprints, not model references. There are 209 references, because 26 footprints
carry two models each — the DIP sockets (`U1`–`U24`) are socket-plus-IC, and `SW11` and
`SW64` are switch-plus-stabilizer. The 8 exempt are `HOLE1`–`HOLE7` and `LOGO1`, which
legitimately have no model. Quote the footprint number; it is the one comparable with the
project's record.

## The only detector is a picture

Every 3D defect this project has found was invisible to automation and obvious in a
render: a 90° IC rotation, half-pitch offsets, five wrong or missing parts, and U26
rendered 15.6 mm tall because a correct scale ratio was applied to the wrong axes.

```
python3 tools/render.py <tag>                      iso-left, into verify/renders/
python3 tools/render.py --view rear <tag>          top · bottom · iso-left · iso-right · rear · back
python3 tools/render.py --shipped                  the five images/ files, full quality
```

`verify/renders/` is gitignored. **Renders are build output and are never committed.**
The five in `images/` are deliberate, and are regenerated on purpose rather than as a side
effect.

Two rear views, for two different jobs. `--view back` is a true orthographic elevation:
dimensionally honest, so it is the panel-cutout reference a case design needs, but it
renders as a thin strip in an empty frame because kicad-cli fits the camera to the
board's diagonal — a wider aspect ratio does not fill it. `--view rear` is the picture:
almost the same angle, with enough perspective to show each connector body's depth. That
one ships.

## What looking costs, when an agent is the one looking

Reading a render means putting an image into context, and that is billed in tokens.
Images are downscaled to roughly 1568 px on the long edge before tokenising, so a
full-board view costs on the order of **1,500 tokens regardless of the file's size on
disk** — a ten-view sweep is on the order of 15,000. (Approximate: the downscale
threshold and rate are platform behaviour, not measured in this repository.)

The expensive mistake is not one render. It is the render–inspect–adjust loop run at full
resolution.

- **Screen at low resolution first.** `--width 800 --height 533 --quality basic` costs
  roughly a tenth of a full view, and gross errors survive downscaling: a rotation, a
  missing part, a part sunk into the board. This is how the clipped-frame defect below
  was found.
- **Target a refdes** rather than re-reading the whole board when you already know what
  you are checking.
- **Prefer a human look.** It costs nothing and is better at "that looks wrong". Ask.

## Missing parts are usually the package, not the board

**Check this before suspecting the design.** 69 of the 209 model references — the Cherry
MX body shared by all 67 keys, plus two stabilizers — come from the Keyswitch Kicad
Library, a Plugin and Content Manager package that this repository declares as a
prerequisite and does not vendor. Without it the keyboard renders empty and everything
else is fine.

`models` names the path variable it could not resolve, and distinguishes that from a file
that is genuinely absent. "Cannot resolve `${KICAD10_3RD_PARTY}`" and "the model is
missing" are different facts and it reports them differently. Only macOS defaults are
verified; elsewhere set the variable in the environment.

## Framing is a real failure mode

At `kicad-cli`'s default zoom the isometric view **clips this board** — the spacebar row
runs off the frame. The shell script that preceded `render.py` used that default, so its
documented view was cropped for as long as it existed. `render.py` applies `--zoom 0.75`
to the isometric views for that reason.

Check the frame on any new view before trusting what it shows, and check it at low
resolution, where it costs almost nothing.

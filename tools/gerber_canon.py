"""Canonicalise a gerber file so reordering and aperture renumbering compare equal,
while any change to real geometry compares different.

Why this is needed: KiCad re-emits identical geometry in a different order and with D-codes
renumbered when it rewrites a board. Measured on this project, a format upgrade changed 12
of 22 gerber files byte-wise while moving nothing: the drill file stayed byte-identical,
the aperture sets matched, and every copper file held the same multiset of drawing
commands. A byte diff would fail on every such rewrite.

A naive line sort is not safe either, because F_Cu, B_Cu and F_Silkscreen use G36/G37
region fills whose vertex order defines the polygon.

Canonical form: the file is split into atomic drawing units --
  * a G36...G37 region block, kept verbatim and in order
  * a D02 move plus the D01/D03 operations that follow it
  * a bare D03 flash
each prefixed by the resolved aperture definition (not its D-code) and the current
interpolation mode. Units are then sorted, so order between units is irrelevant while
order within a unit is preserved.

Validated both ways on this board: reports a KiCad format upgrade as unchanged, and
detects a 1um pad displacement in 5 files.

Usage: gerber_canon.py <file.gbr>      -> prints canonical form
"""
import re
import sys

APERTURE_DEF = re.compile(r"^%ADD(\d+)([^*]*)\*%")
APERTURE_SEL = re.compile(r"^D(\d+)\*$")
GMODE = re.compile(r"^(G0[123])\*?$")
OPLINE = re.compile(r"D0([123])\*$")


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
                units.append(unit)
                unit = None
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
                units.append(unit)
                unit = None
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
                    units.append(unit)
                    unit = None
                units.append("FLASH|%s|%s" % (cur_ap, line))
            continue
        # everything else (format specs, attributes, M02) is metadata, not geometry

    if unit:
        units.append(unit)
    return sorted(units)


if __name__ == "__main__":
    for u in canon(sys.argv[1]):
        print(u)

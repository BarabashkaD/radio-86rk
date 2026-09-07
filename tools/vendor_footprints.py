"""Extract every unique footprint from the board into a project-local .pretty library.

Geometry identity is guaranteed by construction: these ARE the board's footprints, with
only instance data (placement, rotation, reference, net assignments) neutralised. That
matters because Cherry_MX is lost upstream and no library on disk holds the correct data --
the board is the only authority for it.

The loaded board is mutated in place rather than duplicating each footprint: it is a
throwaway copy and is never saved. (Duplicate() returns a BOARD_ITEM that would need a
cast.)

Usage: vendor_footprints.py <board.kicad_pcb> <out.pretty>
"""
import os
import sys

import pcbnew

BOARD = sys.argv[1]
LIB = sys.argv[2]

os.makedirs(LIB, exist_ok=True)
board = pcbnew.LoadBoard(BOARD)
io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

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

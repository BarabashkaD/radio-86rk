"""Apply models.tsv to the vendored library AND to the board's footprint instances.

TSV columns: footprint <TAB> model <TAB> off_x <TAB> off_y <TAB> off_z <TAB> rot_z

Columns after the model are optional and default to 0. Multiple rows per footprint are
applied in order, which is how socket+chip and switch+stabilizer composites are built.

The offset and rotation matter: a KiCad 3D model is authored in the frame of the KiCad
footprint it ships with, and our footprints use different conventions - pad 1 at the origin
vs centred, DIP long axis along Y vs X. tools/align_models.py computes the transform that
maps one onto the other.

A model_path of "-" means "deliberately no model"; the row documents the decision and the
footprint is still counted as handled.

Footprints that live in an external library (perigoso's, say) are not in LIB. Those are
applied to the board instances only, and reported. A name found in neither the library nor
the board is a typo, not a decision, and is fatal.

Re-runnable and idempotent: each footprint's model list is cleared before adding.

Usage: apply_models.py <models.tsv> <board.kicad_pcb> <lib.pretty>
"""
import collections
import sys

import pcbnew

TSV = sys.argv[1]
BOARD = sys.argv[2]
LIB = sys.argv[3]

wanted = collections.OrderedDict()
for raw in open(TSV):
    line = raw.split("#", 1)[0].strip()
    if not line:
        continue
    cols = [c.strip() for c in line.split("\t") if c.strip() != ""]
    name, path = cols[0], cols[1]
    vals = [float(c) for c in cols[2:6]] + [0.0] * 4
    ox, oy, oz, rot = vals[0], vals[1], vals[2], vals[3]
    wanted.setdefault(name, [])
    if path != "-":
        wanted[name].append((path, ox, oy, oz, rot))


def set_models(fp, entries):
    fp.Models().clear()
    for path, ox, oy, oz, rot in entries:
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        m.m_Offset = pcbnew.VECTOR3D(ox, oy, oz)
        m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
        m.m_Rotation = pcbnew.VECTOR3D(0, 0, rot)
        m.m_Show = True
        fp.Models().push_back(m)


io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

# 1. the vendored library
external = []
for name, entries in wanted.items():
    fp = pcbnew.FootprintLoad(LIB, name)
    if fp is None:
        external.append(name)
        continue
    set_models(fp, entries)
    io.FootprintSave(LIB, fp)
if external:
    print("board-only (not in %s): %s" % (LIB, ", ".join(external)))

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
    print("  %3d x %-38s (%d model(s))" % (touched[name], name, len(wanted[name])))
print("applied to %d footprints / %d instances" % (len(wanted), total))

ghosts = [n for n in wanted if touched[n] == 0 and n in external]
if ghosts:
    sys.exit("ERROR: named in models.tsv but found nowhere: %s" % ", ".join(ghosts))

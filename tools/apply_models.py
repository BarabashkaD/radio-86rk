"""Apply models.tsv to the vendored library AND to the board's footprint instances.

TSV columns: footprint <TAB> model <TAB> off_x <TAB> off_y <TAB> off_z <TAB> rot_z
             [<TAB> rot_x <TAB> rot_y <TAB> scale_x <TAB> scale_y <TAB> scale_z]

Columns after the model are optional: rotations default to 0 and scales to 1. The trailing
five exist for manufacturer models, which — unlike KiCad's own library, where everything is
authored Z-up in the footprint frame — arrive in whatever frame the vendor's CAD used. A
connector exported lying on its side needs rot_x = -90; a model of a sibling part needs a
scale. KiCad's own models never need either, which is why the first eleven years of this
file did not have the columns.

Multiple rows per footprint are applied in order, which is how socket+chip and
switch+stabilizer composites are built.

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
    nums = [float(c) for c in cols[2:11]]
    off = (nums + [0.0] * 3)[0:3]                     # off_x, off_y, off_z
    rz = (nums + [0.0] * 4)[3]                        # rot_z
    rx, ry = (nums + [0.0] * 6)[4:6]                  # rot_x, rot_y
    scale = nums[6:9] if len(nums) >= 9 else [1.0, 1.0, 1.0]
    wanted.setdefault(name, [])
    if path != "-":
        wanted[name].append((path, off, (rx, ry, rz), scale))


def set_models(fp, entries):
    fp.Models().clear()
    for path, off, rot, scale in entries:
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        m.m_Offset = pcbnew.VECTOR3D(*off)
        m.m_Scale = pcbnew.VECTOR3D(*scale)
        m.m_Rotation = pcbnew.VECTOR3D(*rot)
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

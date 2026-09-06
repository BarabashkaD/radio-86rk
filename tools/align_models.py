"""Compute the offset and rotation that align a KiCad stock 3D model to our footprint.

Why this is needed: a 3D model is authored in the coordinate frame of the KiCad footprint
it ships with. Our footprints came from a 1986 board via a different library and use
different conventions, so a model dropped in at offset (0,0,0) lands wrong:

  * KiCad's THT passives put **pad 1 at the origin**; ours are **centred** on the origin,
    so the model sits half a pitch off — one lead in a hole, one in mid-air.
  * KiCad's DIP footprints run their long axis along **Y**; ours run along **X**, so every
    IC appears rotated 90 degrees.
  * Some of ours number the pads in the opposite direction (Diode_762, LED_3mm), so the
    body is reversed — a diode's cathode band ends up at the wrong end.

None of this touches copper. It is purely how the model is placed for rendering.

The transform is derived from geometry rather than guessed: take the pad-1 -> pad-N vector
in each footprint, rotate by the angle between them, then translate so the model's pad 1
lands on ours.

Usage: align_models.py            -> prints a models.tsv fragment
       align_models.py --check    -> just report the computed transforms
"""
import math
import sys

import pcbnew

OURS = "KiCad/Radio86RK.pretty"
KI = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

# our footprint -> (KiCad .pretty, KiCad footprint the model belongs to)
SOURCE = {
    "Res_762":                 ("Resistor_THT",      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"),
    "Cap_Cer_508":             ("Capacitor_THT",     "C_Disc_D5.0mm_W2.5mm_P5.00mm"),
    "Cap_Elec_Radial_6.3mm":   ("Capacitor_THT",     "CP_Radial_D6.3mm_P2.50mm"),
    "Diode_762":               ("Diode_THT",         "D_DO-35_SOD27_P7.62mm_Horizontal"),
    "LED_3mm":                 ("LED_THT",           "LED_D3.0mm"),
    "Crystal_HC-49U_Vert":     ("Crystal",           "Crystal_HC49-U_Vertical"),
    "Transistor_TO92_EBC_254": ("Package_TO_SOT_THT", "TO-92_Inline"),
    "IC_TO220-3_Vert":         ("Package_TO_SOT_THT", "TO-220-3_Vertical"),
    "IC_DIP8_300":             ("Package_DIP",       "DIP-8_W7.62mm"),
    "IC_DIP14_300":            ("Package_DIP",       "DIP-14_W7.62mm"),
    "IC_DIP16_300":            ("Package_DIP",       "DIP-16_W7.62mm"),
    "IC_DIP20_300":            ("Package_DIP",       "DIP-20_W7.62mm"),
    "IC_DIP24_600":            ("Package_DIP",       "DIP-24_W15.24mm"),
    "IC_DIP28_600":            ("Package_DIP",       "DIP-28_W15.24mm"),
    "IC_DIP40_600":            ("Package_DIP",       "DIP-40_W15.24mm"),
    "Conn_SIL6":               ("Resistor_THT",      "R_Array_SIP6"),
    "Conn_SIL10":              ("Resistor_THT",      "R_Array_SIP10"),
    "Conn_Pin_Header_4x1_2.54mm":  ("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical"),
    "Conn_Pin_Header_20x1_2.54mm": ("Connector_PinHeader_2.54mm", "PinHeader_1x20_P2.54mm_Vertical"),
    "Conn_Pin_Header_13x2_2.54mm_Shrouded": ("Connector_IDC", "IDC-Header_2x13_P2.54mm_Vertical"),
    "Conn_Friction_Lock_8P_2.54mm": ("Connector_Molex", "Molex_KK-254_AE-6410-08A_1x08_P2.54mm_Vertical"),
    # Housed variant: our footprint does carry the connector's two mounting holes -- 3.05 mm
    # plated, named "0", at +/-12.494 on the centreline between the pin rows -- so the
    # hardware in this model has somewhere to land. Of the five housed variants, three put
    # their holes on that centreline (the 4.94 and 14.56/8.20 variants put them at row-2
    # height instead, a real mechanical mismatch); those three then differ only in how far
    # the shell face stands off the pins, and ours sits 8.178 mm from the board edge, so
    # 7.70 is the near fit and the shell overhangs the edge by 0.478 mm.
    "Conn_Dsub_DE9M":          ("Connector_Dsub",    "DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm"),
    "Speaker_12mm":            ("Buzzer_Beeper",     "Buzzer_12x9.5RM7.6"),
    "Conn_Power_Jack_Circular_Pads": ("Connector_BarrelJack", "BarrelJack_CUI_PJ-063AH_Horizontal"),
    "Switch_Tactile_6mm_Right": ("Button_Switch_THT", "SW_Tactile_SPST_Angled_PTS645Vx31-2LFS"),
    "DC-DC_SIP8":              ("Converter_DCDC",    "Converter_DCDC_Bothhand_CFUSxxxx_THT"),
    "Conn_RCA_Right":          ("Connector_Coaxial", "BNC_Amphenol_B6252HB-NPP3G-50_Horizontal"),
}


def anchors(lib, name):
    """(pad1_xy, padN_xy) in mm, N being the highest-numbered pad."""
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        return None
    pads = {}
    for p in fp.Pads():
        n = p.GetName()
        if n:
            pads[n] = (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
    if "1" not in pads or len(pads) < 2:
        return None

    def key(k):
        try:
            return (0, int(k))
        except ValueError:
            return (1, k)

    return pads["1"], pads[max(pads, key=key)]


def transform(ours, kilib, kiname):
    a = anchors(OURS, ours)
    b = anchors("%s/%s.pretty" % (KI, kilib), kiname)
    if not a or not b:
        return None
    (ax1, ay1), (ax2, ay2) = a
    (bx1, by1), (bx2, by2) = b
    ang_ours = math.atan2(ay2 - ay1, ax2 - ax1)
    ang_ki = math.atan2(by2 - by1, bx2 - bx1)
    rot = math.degrees(ang_ours - ang_ki)
    rot = round(rot / 90.0) * 90.0            # snap: these are all right angles
    rot = (rot + 360.0) % 360.0
    # the model's pad 1 sits at KiCad's pad-1 position; place it on ours
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    rx, ry = bx1 * c - by1 * s, bx1 * s + by1 * c
    ox, oy = ax1 - rx, ay1 - ry

    # KiCad's 3D model offset has Y inverted relative to PCB coordinates (the 3D view has
    # Y up, the board has Y down); the Z rotation is NOT inverted. Determined empirically
    # with a calibration board -- see verify/renders/calib2.png, which renders eight
    # candidate conventions side by side against KiCad's own DIP-40 as a known-good
    # reference. Only (ox, -oy, rot) puts the chip body between its pad rows.
    #
    # This is why the passives looked correct while every IC was visibly wrong: the
    # passives all have oy = 0, so negating it changes nothing.
    return round(ox, 4), round(-oy, 4), rot


if __name__ == "__main__":
    for ours in sorted(SOURCE):
        kilib, kiname = SOURCE[ours]
        t = transform(ours, kilib, kiname)
        if t is None:
            print("# %-38s COULD NOT RESOLVE (%s:%s)" % (ours, kilib, kiname), file=sys.stderr)
            continue
        ox, oy, rot = t
        note = "" if (ox or oy or rot) else "   # already aligned"
        print("%-38s off=(%8.4f, %8.4f)  rot=%5.1f%s" % (ours, ox, oy, rot, note))

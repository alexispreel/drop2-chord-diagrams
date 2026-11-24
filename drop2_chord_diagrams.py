#!/usr/bin/env python3
"""
Drop 2 guitar chord diagram generator.

Builds every drop 2 voicing (4 inversions x 3 adjacent string sets) for each
seventh-chord quality and writes a printable, one-page-per-quality PDF.

Usage:
    pip install reportlab
    python drop2_chord_diagrams.py                 # -> drop2_chord_diagrams.pdf
    python drop2_chord_diagrams.py out.pdf         # custom filename
    python drop2_chord_diagrams.py --a4            # A4 instead of US Letter

To add a chord quality, add one entry to QUALITIES (semitones + labels).
"""
import sys

from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

# --------------------------------------------------------------------------
# Theory data
# --------------------------------------------------------------------------
OPEN_STRINGS = [40, 45, 50, 55, 59, 64]            # MIDI: E2 A2 D3 G3 B3 E4 (low -> high)
STRING_NAMES = ["6", "5", "4", "3", "2", "1"]       # string numbers, low -> high

# name: (semitones above root, degree labels) for chord tones 1-3-5-7
QUALITIES = {
    "Major 7":            ([0, 4, 7, 11], ["R", "3",  "5",  "7"]),
    "Dominant 7":         ([0, 4, 7, 10], ["R", "3",  "5",  "b7"]),
    "Minor 7":            ([0, 3, 7, 10], ["R", "b3", "5",  "b7"]),
    "Minor 7b5 (half-dim)": ([0, 3, 6, 10], ["R", "b3", "b5", "b7"]),
    "Diminished 7":       ([0, 3, 6, 9],  ["R", "b3", "b5", "bb7"]),
}

# Qualities included when none are specified (CLI) and pre-checked in the web UI.
DEFAULT_QUALITIES = ["Major 7", "Dominant 7", "Minor 7", "Minor 7b5 (half-dim)"]

STRING_SETS = [0, 1, 2]       # index of the lowest string of each 4-string group
INVERSIONS = ["Root position", "1st inversion", "2nd inversion", "3rd inversion"]

MAX_SPAN = 4                  # max fret stretch (frets between lowest & highest)

# Rows are 0-based: 0 = root in bass, 1 = 3rd, 2 = 5th, 3 = 7th.
# Make a quality's voicing the exact same shape as a reference quality, shifted only
# by the interval difference (Minor 7 vs Minor 7b5: just the 5th moves one fret).
ALIGN_TO = {("Minor 7", 3): "Minor 7b5 (half-dim)"}
# Force the first fret row shown in the diagram, so paired diagrams line up.
WINDOW_START = {("Minor 7", 3): 1, ("Minor 7b5 (half-dim)", 3): 1}


def drop2_order(inversion):
    """Chord-tone indices (0=R,1=3rd,2=5th,3=7th), bottom -> top, for a drop 2 voicing.

    `inversion` is the bass note of the voicing: 0 = root, 1 = 3rd, 2 = 5th, 3 = 7th.
    Built from a close-position chord with the 2nd voice from the top dropped
    down an octave (it becomes the bass note).
    """
    # Rows are named by the BASS note of the drop 2 voicing (0 = root in the bass,
    # 1 = 3rd, 2 = 5th, 3 = 7th). Dropping the 2nd voice from the top puts the
    # close-position chord's 3rd-from-bottom tone in the bass, hence the +2 offset.
    # (Before this fix the rows were numbered by the close-position inversion,
    # so the "root position" row actually had the 5th in the bass.)
    close = [(inversion + 2 + i) % 4 for i in range(4)]
    return [close[2], close[0], close[1], close[3]]


def place_voicing(semis, order, first_string):
    """Find the lowest-position fingering on 4 adjacent strings.

    Each note is the nearest matching pitch above the previous one, which is
    exactly how a drop 2 voicing stacks. Returns list of (string_idx, fret).
    """
    for fret0 in range(1, 13):
        # pitch of bass note on the lowest string; derive the root's pitch class
        p = OPEN_STRINGS[first_string] + fret0
        root_pc = (p - semis[order[0]]) % 12
        frets = [fret0]
        ok = True
        for k in range(1, 4):
            target_pc = (root_pc + semis[order[k]]) % 12
            s = first_string + k
            # next pitch above p with the target pitch class
            step = (target_pc - p) % 12
            step = step or 12
            p += step
            fret = p - OPEN_STRINGS[s]
            if fret < 1 or fret > 15:
                ok = False
                break
            frets.append(fret)
        if ok and max(frets) - min(frets) <= MAX_SPAN:
            return [(first_string + k, frets[k]) for k in range(4)]
    raise RuntimeError("no fingering found")


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------
DEGREE_COLORS = {
    "R":   HexColor("#1f6fd1"),   # blue
    "3":   HexColor("#d6336c"),   # magenta/red
    "b3":  HexColor("#d6336c"),
    "5":   HexColor("#2f9e44"),   # green
    "b5":  HexColor("#2f9e44"),
    "7":   HexColor("#e67700"),   # orange
    "b7":  HexColor("#e67700"),
    "bb7": HexColor("#e67700"),
}

STR_GAP = 17        # horizontal spacing between strings (pt)
FRET_GAP = 19       # vertical spacing between frets (pt)
N_FRETS = MAX_SPAN + 1
DOT_R = 7.2


def draw_diagram(c, x, y_top, notes, labels, start=None):
    """Draw one chord box. (x, y_top) = top-left of the string/fret grid.

    notes: list of (string_idx, fret); labels: degree label per note.
    """
    width = STR_GAP * 5
    height = FRET_GAP * N_FRETS
    f_min = min(f for _, f in notes)
    start = f_min if start is None else start   # first fret row shown

    # muted strings (x) above the grid
    used = {s for s, _ in notes}
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 7)
    for s in range(6):
        if s not in used:
            c.drawCentredString(x + s * STR_GAP, y_top + 4, "x")

    # fret lines
    c.setStrokeColor(HexColor("#555555"))
    for i in range(N_FRETS + 1):
        c.setLineWidth(0.8)
        yy = y_top - i * FRET_GAP
        c.line(x, yy, x + width, yy)
    # strings (thicker toward the bass)
    for s in range(6):
        c.setLineWidth(1.1 - s * 0.12)
        c.line(x + s * STR_GAP, y_top, x + s * STR_GAP, y_top - height)

    # # starting-fret label
    # if True:
    #     c.setFillColor(black)
    #     c.setFont("Helvetica-Bold", 8)
    #     c.drawRightString(x - 6, y_top - FRET_GAP / 2 - 3, f"{start}")
    #     c.setFont("Helvetica", 6)
    #     c.drawRightString(x - 6, y_top - FRET_GAP / 2 - 10, "fret")

    # dots
    for (s, f), lab in zip(notes, labels):
        cx = x + s * STR_GAP
        cy = y_top - (f - start) * FRET_GAP - FRET_GAP / 2
        c.setFillColor(DEGREE_COLORS[lab])
        c.setStrokeColor(DEGREE_COLORS[lab])
        c.circle(cx, cy, DOT_R, stroke=1, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 6.6 if len(lab) < 3 else 5.6)
        c.drawCentredString(cx, cy - 2.3, lab)


def draw_legend(c, x, y):
    c.setFont("Helvetica", 7.5)
    items = [("R", "Root"), ("3", "3rd / b3"), ("5", "5th / b5"), ("7", "7th / b7 / bb7")]
    for key, text in items:
        color = DEGREE_COLORS[key]
        c.setFillColor(color)
        c.circle(x + 5, y + 2.5, 5, stroke=0, fill=1)
        c.setFillColor(black)
        c.drawString(x + 14, y, text)
        x += 14 + c.stringWidth(text, "Helvetica", 7.5) + 18


# def build_pdf(path, pagesize=letter):
def build_pdf(path, qualities=None):
    """Write the PDF to `path` (a filename or a file-like object such as BytesIO).

    qualities: iterable of keys of QUALITIES to include (default: DEFAULT_QUALITIES).
    Pages always follow the order of QUALITIES, whatever order is passed in.
    """
    wanted = set(DEFAULT_QUALITIES if qualities is None else qualities)
    unknown = wanted - set(QUALITIES)
    if unknown:
        raise ValueError(f"unknown chord quality: {sorted(unknown)}")
    selected = [q for q in QUALITIES if q in wanted]
    if not selected:
        raise ValueError("select at least one chord quality")

    W, H = A4
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle("Drop 2 guitar chord voicings")
    c.setAuthor("drop2_chord_diagrams.py")

    margin = 36
    label_w = 78    # with row-label column; the 3 diagram columns use the remaining width
    # label_w = 0   # no row-label column; the 3 diagram columns use the full width
    col_w = (W - 2 * margin - label_w) / 3
    header_h = 66
    footer_h = 40
    row_h = (H - 2 * margin - header_h - footer_h) / 4
    grid_w = STR_GAP * 5

    for qname in selected:
        semis, labs = QUALITIES[qname]
        # ---- title ----
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, H - margin - 14, f"Drop 2 voicings \u2013 {qname}")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(HexColor("#555555"))
        c.drawString(margin, H - margin - 28,
                     "Chord tones R\u2013" + "\u2013".join(labs[1:]) +
                     "  |  movable shapes, standard tuning  |  bass note at left")

        # ---- column headers ----
        top = H - margin - header_h
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        for j, s0 in enumerate(STRING_SETS):
            cx = margin + label_w + j * col_w + col_w / 2
            c.drawCentredString(cx, top + 8, f"Strings {STRING_NAMES[s0]}-{STRING_NAMES[s0+1]}-"
                                              f"{STRING_NAMES[s0+2]}-{STRING_NAMES[s0+3]}")
        c.setStrokeColor(HexColor("#bbbbbb"))
        c.setLineWidth(0.6)
        c.line(margin, top, W - margin, top)

        # ---- rows ----
        for i, inv_name in enumerate(INVERSIONS):
            row_top = top - i * row_h
            order = drop2_order(i)
            degs = [labs[k] for k in order]

            c.setFillColor(black)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(margin, row_top - 24, inv_name)
            c.setFont("Helvetica", 8)
            c.setFillColor(HexColor("#555555"))
            c.drawString(margin, row_top - 36, " ".join(degs))
            # c.setFont("Helvetica", 6.5)
            # c.drawString(margin, row_top - 46, "(low \u2192 high)")

            for j, s0 in enumerate(STRING_SETS):
                notes = place_voicing(semis, order, s0)
                ref = ALIGN_TO.get((qname, i))
                if ref:
                    ref_semis, _ = QUALITIES[ref]
                    ref_notes = place_voicing(ref_semis, order, s0)
                    notes = [(st, f + semis[k] - ref_semis[k])
                             for (st, f), k in zip(ref_notes, order)]
                gx = margin + label_w + j * col_w + (col_w - grid_w) / 2
                draw_diagram(c, gx, row_top - 22, notes, degs,
                             start=WINDOW_START.get((qname, i)))

            c.setStrokeColor(HexColor("#dddddd"))
            c.line(margin, row_top - row_h, W - margin, row_top - row_h)

        # ---- footer ----
        draw_legend(c, margin, margin + 6)
        c.setFont("Helvetica", 7)
        c.setFillColor(HexColor("#777777"))
        c.drawRightString(W - margin, margin + 6,
                          "Left number = fret of the top row of each diagram; x = muted string")
        c.showPage()

    c.save()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    size = A4 if "--a4" in sys.argv else letter
    out = args[0] if args else "drop2_chord_diagrams.pdf"
    build_pdf(out)
    print(f"wrote {out}")

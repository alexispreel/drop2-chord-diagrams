#!/usr/bin/env python3

"""
Drop 2 guitar chord diagram generator.

Builds every drop 2 voicing (4 inversions x 3 adjacent string sets) for each
seventh-chord quality and writes a printable, one-page-per-quality PDF.

Usage:
    pip install reportlab
    python drop2_chord_diagrams.py                 # -> drop2_chord_diagrams.pdf
    python drop2_chord_diagrams.py out.pdf         # custom filename

To add a chord quality, add one entry to QUALITIES (semitones + labels).
"""
import sys

from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

# Semitones above open low E string (standard tuning: E A D G B E)
OPEN_STRINGS = [0, 5, 10, 15, 19, 24]
STRING_NAMES = ["6", "5", "4", "3", "2", "1"]

# Quality names, for chord tones 1-3-5-7
QUALITIES = {
    "Major 7":              ([0, 4, 7, 11], ["R", "3",  "5",  "7"]),
    "Dominant 7":           ([0, 4, 7, 10], ["R", "3",  "5",  "b7"]),
    "Minor 7":              ([0, 3, 7, 10], ["R", "b3", "5",  "b7"]),
    "Minor 7b5 (half-dim)": ([0, 3, 6, 10], ["R", "b3", "b5", "b7"]),
    "Diminished 7":         ([0, 3, 6, 9],  ["R", "b3", "b5", "bb7"]),
}

# Qualities included when none are specified
DEFAULT_QUALITIES = ["Major 7", "Dominant 7", "Minor 7", "Minor 7b5 (half-dim)"]

# Index of lowest string of each 4-string group
STRING_SETS = [0, 1, 2]

# Inversion names, for the 4 drop 2 voicings of each quality
INVERSIONS = ["Root position", "1st inversion", "2nd inversion", "3rd inversion"]

# Max fret stretch, to keep positions playable on guitar
MAX_SPAN = 4

# Rows are 0-based: 0 = root in bass, 1 = 3rd, 2 = 5th, 3 = 7th.
# Make a quality voicing the exact same shape as a reference quality, shifted only
# by the interval difference (Minor 7 vs Minor 7b5: just the 5th moves one fret).
ALIGN_TO = {("Minor 7", 3): "Minor 7b5 (half-dim)"}

# Force the first fret row shown in the diagram, so paired diagrams line up.
WINDOW_START = {("Minor 7", 3): 1, ("Minor 7b5 (half-dim)", 3): 1}


"""
Chord-tone indices (0=R,1=3rd,2=5th,3=7th), bottom -> top, for drop 2 voicing.

`inversion`: bass note of voicing, i.e. 0 = root, 1 = 3rd, 2 = 5th, 3 = 7th.
Built by dropping 2nd voice from top to down an octave, then reordering to bottom -> top.
"""
def drop2_order(inversion: int) -> list[int]:
    close = [(inversion + 2 + i) % 4 for i in range(4)]
    return [close[2], close[0], close[1], close[3]]


"""
To find the lowest-position fingering on 4 adjacent strings.

Each note is nearest matching pitch above previous one, which is
exactly how a drop 2 voicing stacks.
"""
def place_voicing(semi_tones: list[int], order: list[int], first_string: int) -> list[tuple[int, int]]:
    for fret0 in range(1, 13):
        # Pitch of bass note on lowest string
        pitch = OPEN_STRINGS[first_string] + fret0

        # Pitch class of bass note, relative to chord's root
        root_pitch_class = (pitch - semi_tones[order[0]]) % 12

        # Initialize fret finger positions with bass first
        frets = [fret0]

        ok = True
        for k in range(1, 4):
            # Target pitch class of next note, relative to chord's root
            target_pitch_class = (root_pitch_class + semi_tones[order[k]]) % 12
            strg = first_string + k

            # Next pitch above previous note, with same pitch class as target
            step = (target_pitch_class - pitch) % 12
            step = step or 12
            pitch += step

            # Fret number on current string
            fret = pitch - OPEN_STRINGS[strg]
            if fret < 1 or fret > 15:
                ok = False
                break

            # Add position to list of frets
            frets.append(fret)

        if ok and max(frets) - min(frets) <= MAX_SPAN:
            return [(first_string + k, frets[k]) for k in range(4)]
        
    raise RuntimeError("no fingering found for semi_tones={} order={} first_string={}".format(semi_tones, order, first_string))


# Chord voice colors: 1 color for each voice degree (root, 3rd, 5th, 7th).
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

# Horizontal spacing between strings (pt)
STR_GAP = 17

# Vertical spacing between frets (pt)
FRET_GAP = 19

# Number of frets shown on diagram
FRET_COUNT = MAX_SPAN + 1

# Radius of chord-tone dots (pt)
DOT_R = 7.2


"""
To draw one chord box. (x, y_top) = top-left of string/fret grid.

notes: list of (string_idx, fret); labels: degree label per note.
"""
def draw_diagram(c, x, y_top, notes, labels, start=None):
    width = STR_GAP * 5
    height = FRET_GAP * FRET_COUNT
    f_min = min(f for _, f in notes)

    # First fret row shown in diagram, so paired diagrams line up
    start = f_min if start is None else start

    # Muted strings: 'x' label above grid
    used = {strg for strg, _ in notes}
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 7)
    for strg in range(6):
        if strg not in used:
            c.drawCentredString(x + strg * STR_GAP, y_top + 4, "x")

    # Fret lines
    c.setStrokeColor(HexColor("#555555"))
    for i in range(FRET_COUNT + 1):
        c.setLineWidth(0.8)
        yy = y_top - i * FRET_GAP
        c.line(x, yy, x + width, yy)
    
    # Strings (thinner toward high, thicker toward low)
    for strg in range(6):
        c.setLineWidth(1.1 - strg * 0.12)
        c.line(x + strg * STR_GAP, y_top, x + strg * STR_GAP, y_top - height)

    # # Starting-fret label
    # if True:
    #     c.setFillColor(black)
    #     c.setFont("Helvetica-Bold", 8)
    #     c.drawRightString(x - 6, y_top - FRET_GAP / 2 - 3, f"{start}")
    #     c.setFont("Helvetica", 6)
    #     c.drawRightString(x - 6, y_top - FRET_GAP / 2 - 10, "fret")

    # Finger colored dots
    for (strg, f), lab in zip(notes, labels):
        cx = x + strg * STR_GAP
        cy = y_top - (f - start) * FRET_GAP - FRET_GAP / 2
        c.setFillColor(DEGREE_COLORS[lab])
        c.setStrokeColor(DEGREE_COLORS[lab])
        c.circle(cx, cy, DOT_R, stroke=1, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 6.6 if len(lab) < 3 else 5.6)
        c.drawCentredString(cx, cy - 2.3, lab)


"""
To draw legend as page footer.
"""
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


"""
To write the PDF to `path`.

qualities: iterable of keys of QUALITIES to be included (default: DEFAULT_QUALITIES).
"""
def build_pdf(path, qualities=None):
    # Check quality input against constants, and sort as constants
    wanted = set(DEFAULT_QUALITIES if qualities is None else qualities)
    unknown = wanted - set(QUALITIES)
    if unknown:
        raise ValueError(f"unknown chord quality: {sorted(unknown)}")
    selected = [q for q in QUALITIES if q in wanted]
    if not selected:
        raise ValueError("select at least one chord quality")

    # Create PDF canvas
    W, H = A4
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle("Drop 2 guitar chord voicings")
    c.setAuthor("drop2_chord_diagrams.py")

    # Layout constants
    margin = 36
    label_w = 78
    col_w = (W - 2 * margin - label_w) / 3
    header_h = 66
    footer_h = 40
    row_h = (H - 2 * margin - header_h - footer_h) / 4
    grid_w = STR_GAP * 5

    # Browse through chord qualities, one page per quality
    for qname in selected:
        semi_tones, labs = QUALITIES[qname]

        # Page header
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, H - margin - 14, f"Drop 2 voicings \u2013 {qname}")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(HexColor("#555555"))
        c.drawString(margin, H - margin - 28,
                     "Chord tones R\u2013" + "\u2013".join(labs[1:]) +
                     "  |  movable shapes, standard tuning  |  bass note at left")

        # Column headers: one per string set
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

        # Rows: one per inversion (root, 3rd, 5th, 7th as bass)
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
                notes = place_voicing(semi_tones, order, s0)
                ref = ALIGN_TO.get((qname, i))
                if ref:
                    ref_semis, _ = QUALITIES[ref]
                    ref_notes = place_voicing(ref_semis, order, s0)
                    notes = [(st, f + semi_tones[k] - ref_semis[k])
                             for (st, f), k in zip(ref_notes, order)]
                gx = margin + label_w + j * col_w + (col_w - grid_w) / 2
                draw_diagram(c, gx, row_top - 22, notes, degs,
                             start=WINDOW_START.get((qname, i)))

            c.setStrokeColor(HexColor("#dddddd"))
            c.line(margin, row_top - row_h, W - margin, row_top - row_h)

        # Page footer: legend
        draw_legend(c, margin, margin + 6)
        c.setFont("Helvetica", 7)
        c.setFillColor(HexColor("#777777"))
        c.drawRightString(W - margin, margin + 6,
                          "Left number = fret of the top row of each diagram; x = muted string")
        c.showPage()

    c.save()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else "drop2_chord_diagrams.pdf"
    build_pdf(out)
    print(f"wrote {out}")

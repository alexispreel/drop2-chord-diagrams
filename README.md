# Drop 2 chord diagrams

Generates printable fretboard diagrams for every drop 2 voicing (4 bass-note
inversions x 3 adjacent string sets) of the common seventh-chord qualities,
one PDF page per quality.

## Web page

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>, switch qualities on/off (Major 7, Dominant 7, Minor 7
and Minor 7b5 are on by default; Diminished 7 is off), choose the output file name
(default `drop2_chord_diagrams.pdf`) and click **Generate PDF**.

## Command line

```bash
python drop2_chord_diagrams.py [out.pdf]    # default qualities
```

From Python / Jupyter:

```python
from drop2_chord_diagrams import build_pdf
build_pdf("out.pdf", ["Major 7", "Diminished 7"])   # omit the list for the defaults
```

## Layout notes

- Rows are ordered by bass note: root, 3rd, 5th, 7th.
- Diagrams are movable shapes in standard tuning, placed at the lowest position.
- `ALIGN_TO` / `WINDOW_START` (top of `drop2_chord_diagrams.py`) make the Minor 7 and
  Minor 7b5 7th-in-bass diagrams line up so only the 5th moves one fret.
- To add a quality, add one entry to `QUALITIES`.

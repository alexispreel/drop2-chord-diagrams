"""Minimal web front end for the drop 2 chord diagram generator.

Run:  python app.py   then open http://127.0.0.1:5000
"""
import io
import os
import re

from flask import Flask, abort, render_template, request, send_file

from drop2_chord_diagrams import DEFAULT_QUALITIES, QUALITIES, build_pdf

DEFAULT_FILENAME = "drop2_chord_diagrams.pdf"

app = Flask(__name__)


def safe_filename(raw):
    """Keep it a plain file name: no paths, no odd characters, always .pdf."""
    name = os.path.basename((raw or "").strip().replace("\\", "/"))
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")
    if not name:
        return DEFAULT_FILENAME
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


@app.get("/")
def index():
    return render_template(
        "index.html",
        qualities=[(q, q in DEFAULT_QUALITIES) for q in QUALITIES],
        default_filename=DEFAULT_FILENAME,
    )


@app.post("/generate")
def generate():
    chosen = [q for q in request.form.getlist("quality") if q in QUALITIES]
    if not chosen:
        abort(400, "Select at least one chord quality.")
    buf = io.BytesIO()
    build_pdf(buf, chosen)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=safe_filename(request.form.get("filename")),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

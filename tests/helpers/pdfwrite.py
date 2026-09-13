from __future__ import annotations

from pathlib import Path


def write_text_pdf(path: Path, text: str) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)
    for line in text.splitlines():
        safe = line.encode("latin-1", "replace").decode("latin-1")
        pdf.cell(0, 5, text=safe, new_x="LMARGIN", new_y="NEXT")
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))

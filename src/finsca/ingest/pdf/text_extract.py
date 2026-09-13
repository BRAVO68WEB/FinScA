from __future__ import annotations

from pathlib import Path


def extract_text(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages).strip()

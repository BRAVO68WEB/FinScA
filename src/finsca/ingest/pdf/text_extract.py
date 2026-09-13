from __future__ import annotations

from pathlib import Path

from finsca.ingest.errors import ParseError


class ExtractError(ParseError):
    pass


def extract_text(path: Path) -> str:
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except ParseError:
        raise
    except Exception as exc:
        raise ExtractError(f"could not read PDF: {exc}") from exc
    return "\n".join(pages).strip()

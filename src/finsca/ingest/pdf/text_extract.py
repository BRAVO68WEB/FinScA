from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from finsca.ingest.errors import ParseError


class ExtractError(ParseError):
    pass


def extract_text(path: Path, passwords: Sequence[str] | None = None) -> str:
    import pdfplumber

    last: Exception | None = None
    for password in (None, *(passwords or ())):
        try:
            with pdfplumber.open(path, password=password or "") as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages).strip()
        except ParseError:
            raise
        except Exception as exc:
            last = exc
            if not _is_password_error(exc):
                raise ExtractError(f"could not read PDF: {exc}") from exc
    raise ExtractError(
        "PDF is password protected. Add a password: finsca passwords add SECRET --match hdfc"
    ) from last


def _is_password_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    text = str(exc).lower()
    return "password" in name.lower() or "password" in text

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
                raise ExtractError(_read_error(exc)) from exc
    raise ExtractError(
        "password not accepted (file is complete). "
        "If a freshly downloaded copy opens in Preview, drop that file in data/inbox/pdf. "
        "Otherwise: finsca passwords add SECRET --match bank"
    ) from last


def _read_error(exc: BaseException) -> str:
    detail = str(exc).strip() or type(exc).__name__
    return f"could not read PDF: {detail}"


def _is_password_error(exc: BaseException) -> bool:
    seen: set[int] = set()
    stack: list[BaseException] = [exc]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        name = type(current).__name__.lower()
        text = str(current).lower()
        tokens = ("password", "encrypt", "decrypt")
        if any(token in name for token in tokens) or any(token in text for token in tokens):
            return True
        stack.extend(arg for arg in current.args if isinstance(arg, BaseException))
        if current.__cause__ is not None:
            stack.append(current.__cause__)
        if current.__context__ is not None:
            stack.append(current.__context__)
    return False

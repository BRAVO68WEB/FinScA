from __future__ import annotations

from pathlib import Path

from finsca.core.enums import SourceKind

_BANK_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hdfc", ("HDFC BANK", "HDFC Bank")),
    ("icici", ("ICICI BANK", "ICICI Bank")),
    ("sbi", ("STATE BANK OF INDIA", "SBI ")),
    ("axis", ("AXIS BANK", "Axis Bank")),
)

_INBOX: tuple[tuple[str, SourceKind, frozenset[str]], ...] = (
    ("pdf", SourceKind.PDF, frozenset({".pdf"})),
    ("email", SourceKind.EMAIL, frozenset({".eml", ".mbox", ".zip"})),
    ("sms", SourceKind.SMS, frozenset({".xml", ".csv", ".json"})),
)


def list_inbox_pdfs(inbox_dir: Path) -> list[Path]:
    return [path for path, kind in list_inbox_files(inbox_dir) if kind is SourceKind.PDF]


def list_inbox_files(inbox_dir: Path) -> list[tuple[Path, SourceKind]]:
    found: list[tuple[Path, SourceKind]] = []
    for folder_name, kind, suffixes in _INBOX:
        folder = inbox_dir / folder_name
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            if path.suffix.lower() in suffixes:
                found.append((path, kind))
    return found


def detect_bank(text: str) -> str | None:
    upper = text.upper()
    for bank_id, markers in _BANK_MARKERS:
        if any(marker.upper() in upper for marker in markers):
            return bank_id
    return None

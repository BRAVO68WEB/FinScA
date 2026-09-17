from __future__ import annotations

from pathlib import Path

from finsca.core.enums import SourceKind

_HEADER_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("axis", ("STATEMENT OF AXIS ACCOUNT", "AXIS BANK LTD", "IFSC CODE: UTIB", "MY ZONE CARD", "AXIS EDGE", "AXIS INTERNET BANKING")),
    ("icici", ("ICICI BANK LIMITED", "WWW.ICICI.BANK", "YOUR BASE BRANCH")),
    ("idfc", ("IDFC FIRST BANK LIMITED", "SAVINGS ACCOUNT DETAILS FOR A/C", "CONSOLIDATED STATEMENT")),
    ("hdfc", ("TATA NEU PLUS HDFC", "HDFC BANK CREDIT CARD", "HDFC BANK LTD")),
    ("sbi", ("SBI CARD", "GSTIN OF SBI CARD", "STATE BANK OF INDIA")),
    ("yes", ("YES BANK POP", "YES BANK CARD NUMBER")),
    ("bob", ("BOBCARD", "UNI BOBCARD")),
)
_BANK_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hdfc", ("HDFC BANK CREDIT CARD", "HDFC Bank Credit Card", "HDFC BANK LTD", "HDFC BANK")),
    ("idfc", ("IDFC FIRST BANK LIMITED", "IDFCFIRST")),
    ("sbi", ("SBI CARD", "STATE BANK OF INDIA")),
    ("axis", ("AXIS BANK LTD", "My Zone Card", "Axis Account")),
    ("icici", ("ICICI BANK LIMITED", "ICICI Bank Ltd")),
    ("yes", ("YES BANK POP", "YES BANK Card")),
    ("bob", ("BOBCARD", "Uni BOBCARD")),
)
_NAME_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hdfc", ("hdfcbank", "hdfc.bank")),
    ("icici", ("icici.bank", "icicibank")),
    ("axis", ("axis.bank", "axisbank")),
    ("idfc", ("idfcfirst", "idfc.bank")),
    ("sbi", ("sbicard", "sbi.bank", "cbssbi", "onlinesbi")),
    ("yes", ("yes.bank", "yesbank")),
    ("bob", ("bobcard",)),
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


def detect_bank(text: str, filename: str = "") -> str | None:
    named = _detect_from_name(filename)
    head = "\n".join(text.splitlines()[:30]).upper()
    for bank_id, markers in _HEADER_MARKERS:
        if any(marker in head for marker in markers):
            return bank_id
    if named:
        return named
    upper = text.upper()
    for bank_id, markers in _BANK_MARKERS:
        if any(marker.upper() in upper for marker in markers):
            return bank_id
    return None


def _detect_from_name(filename: str) -> str | None:
    name = filename.lower()
    if not name:
        return None
    for bank_id, markers in _NAME_MARKERS:
        if any(marker in name for marker in markers):
            return bank_id
    return None

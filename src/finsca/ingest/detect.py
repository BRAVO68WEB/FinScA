from __future__ import annotations

from pathlib import Path

from finsca.core.ids import file_sha256

_BANK_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hdfc", ("HDFC BANK", "HDFC Bank")),
    ("icici", ("ICICI BANK", "ICICI Bank")),
    ("sbi", ("STATE BANK OF INDIA", "SBI ")),
    ("axis", ("AXIS BANK", "Axis Bank")),
)


def list_inbox_pdfs(inbox_dir: Path) -> list[Path]:
    folder = inbox_dir / "pdf"
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf" and path.name != ".gitkeep"
    )


def detect_bank(text: str) -> str | None:
    upper = text.upper()
    for bank_id, markers in _BANK_MARKERS:
        if any(marker.upper() in upper for marker in markers):
            return bank_id
    return None


def file_digest(path: Path) -> str:
    return file_sha256(path)

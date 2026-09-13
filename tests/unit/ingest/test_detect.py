from __future__ import annotations

from pathlib import Path

from finsca.ingest.detect import detect_bank, list_inbox_pdfs


def test_detect_hdfc_from_header() -> None:
    assert detect_bank("HDFC BANK\nAccount No : 1234") == "hdfc"


def test_detect_unknown_bank() -> None:
    assert detect_bank("Some random brokerage statement") is None


def test_list_inbox_pdfs_ignores_gitkeep(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    pdf = inbox / "pdf"
    pdf.mkdir(parents=True)
    (pdf / ".gitkeep").write_text("")
    (pdf / "stmt.pdf").write_bytes(b"%PDF")
    (pdf / "notes.txt").write_text("nope")
    found = list_inbox_pdfs(inbox)
    assert [p.name for p in found] == ["stmt.pdf"]

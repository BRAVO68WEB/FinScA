from __future__ import annotations

from pathlib import Path

from finsca.core.enums import SourceKind
from finsca.ingest.detect import detect_bank, list_archive_files, list_inbox_pdfs


def test_detect_hdfc_from_header() -> None:
    assert detect_bank("HDFC BANK\nAccount No : 1234") == "hdfc"


def test_detect_prefers_filename_over_payee_text() -> None:
    text = "Opening Balance 1.00\n03-08-2026 UPI/P2M/1/NETFLIX C/HDFC BANK 649.00\n"
    assert detect_bank(text, "1a06_statements_axis.bank.in_AXIS BANK Statement.pdf") == "axis"


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


def test_list_archive_files_skips_manifest_and_sidecars(tmp_path: Path) -> None:
    run = tmp_path / "2026-08-01_run_abc123"
    (run / "pdf").mkdir(parents=True)
    statement = run / "pdf" / "a.pdf"
    statement.write_bytes(b"%PDF")
    (run / "manifest.json").write_text("{}", encoding="utf-8")
    (run / "pdf" / "a.pdf.error.json").write_text("{}", encoding="utf-8")
    assert list_archive_files(run) == [(statement, SourceKind.PDF)]

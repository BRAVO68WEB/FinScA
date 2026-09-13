from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from finsca.cli.app import app
from tests.helpers.pdfwrite import write_text_pdf

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "statements"


def test_ingest_pdf_persists_and_archives(data_dir: Path) -> None:
    text = (FIXTURES / "hdfc.txt").read_text()
    pdf_path = data_dir / "inbox" / "pdf" / "hdfc-aug.pdf"
    write_text_pdf(pdf_path, text)
    result = runner.invoke(app, ["ingest"])
    assert result.exit_code == 0, result.output
    assert "parsed" in result.output
    assert not pdf_path.exists()
    archives = list((data_dir / "archive").glob("*/hdfc-aug.pdf"))
    assert len(archives) == 1
    assert (archives[0].parent / "manifest.json").exists()
    listed = runner.invoke(app, ["accounts", "list"])
    assert listed.exit_code == 0, listed.output
    assert "4521" in listed.output
    months = runner.invoke(app, ["accounts", "months", "--account", "4521"])
    assert "22250.00" in months.output
    assert "statement" in months.output


def test_ingest_empty_inbox(data_dir: Path) -> None:
    result = runner.invoke(app, ["ingest"])
    assert result.exit_code == 0, result.output
    assert "inbox empty" in result.output


def test_ingest_keeps_ledger_if_archive_fails(data_dir: Path, monkeypatch) -> None:
    text = (FIXTURES / "hdfc.txt").read_text()
    pdf_path = data_dir / "inbox" / "pdf" / "hdfc-aug.pdf"
    write_text_pdf(pdf_path, text)

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("finsca.agents.pipeline.archive_successes", boom)
    result = runner.invoke(app, ["ingest"])
    assert result.exit_code != 0
    assert pdf_path.exists()
    listed = runner.invoke(app, ["accounts", "list"])
    assert "4521" in listed.output


def test_ingest_rejects_pdf_without_last4(data_dir: Path) -> None:
    write_text_pdf(
        data_dir / "inbox" / "pdf" / "nolast4.pdf",
        "Statement Period: 01/08/2026 to 31/08/2026\n"
        "Opening Balance: 100.00\n"
        "01/08/2026 UPI-SWIGGY 10.00 Dr\n"
        "Closing Balance: 90.00\n",
    )
    result = runner.invoke(app, ["ingest"])
    assert result.exit_code == 0, result.output
    assert "last4" in result.output
    assert (data_dir / "inbox" / "pdf" / "nolast4.pdf").exists()
    listed = runner.invoke(app, ["accounts", "list"])
    assert "no accounts yet" in listed.output

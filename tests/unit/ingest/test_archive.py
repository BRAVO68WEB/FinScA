from __future__ import annotations

from pathlib import Path

from finsca.archive.mover import archive_successes, write_error_sidecar
from finsca.ingest.types import IngestFileResult


def test_archive_moves_successes_and_writes_manifest(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox" / "pdf"
    inbox.mkdir(parents=True)
    src = inbox / "stmt.pdf"
    src.write_bytes(b"%PDF")
    archive = tmp_path / "archive"
    item = IngestFileResult(path=src, sha256="abc", parser="hdfc", tx_count=2)
    dest = archive_successes([item], archive, "runid1234567890")
    assert not src.exists()
    assert (dest / "stmt.pdf").exists()
    assert (dest / "manifest.json").exists()
    assert "runid123456" in dest.name


def test_error_sidecar_stays_beside_file(tmp_path: Path) -> None:
    src = tmp_path / "bad.pdf"
    src.write_bytes(b"%PDF")
    sidecar = write_error_sidecar(src, "no transactions parsed")
    assert src.exists()
    assert sidecar.exists()
    assert "no transactions parsed" in sidecar.read_text()

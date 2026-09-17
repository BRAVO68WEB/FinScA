from __future__ import annotations

import base64
import json
from pathlib import Path
from types import SimpleNamespace

from finsca.config.settings import Settings
from finsca.ingest.email.gmail_api import (
    SeenIndex,
    _pull_action,
    load_seen,
    pull,
    save_seen,
    seen_path,
)


def test_seen_roundtrip_and_inbox_prefixes(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_dirs()
    (settings.inbox_dir / "email" / "1a0568f195b9_alerts.eml").write_text("From: x\n\nbody\n")
    index = SeenIndex(pdfs={"already": []})
    save_seen(settings, index)
    seen = load_seen(settings)
    assert seen.pdfs["already"] == []
    assert seen.pdfs["1a0568f195b9"] is None


def test_legacy_ids_file_backfills_existing_eml(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_dirs()
    mid = "19dae860caa3d1d2"
    (settings.inbox_dir / "email" / f"{mid[:12]}_alerts.eml").write_text("From: x\n\nbody\n")
    seen_path(settings).write_text(json.dumps({"ids": [mid, mid[:12]]}), encoding="utf-8")
    seen = load_seen(settings)
    assert seen.pdfs[mid] is None
    assert _pull_action(mid, seen, settings) == "pdfs"


def test_eml_without_pdfs_needs_attachment_backfill(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_dirs()
    mid = "1a0568f195b9b84e"
    (settings.inbox_dir / "email" / f"{mid[:12]}_alerts.eml").write_text("From: x\n\nbody\n")
    seen = load_seen(settings)
    assert _pull_action(mid, seen, settings) == "pdfs"


def test_recorded_empty_attachments_skips(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_dirs()
    mid = "bbbbbbbbbbbbcccc"
    seen = SeenIndex(pdfs={mid: [], mid[:12]: []})
    assert _pull_action(mid, seen, settings) == "skip"


def test_recorded_pdfs_present_skips(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_dirs()
    mid = "cccccccccccccccc"
    name = "cccccccccccccccc_CC_Statement.pdf"
    (settings.inbox_dir / "pdf" / name).write_bytes(b"%PDF")
    seen = SeenIndex(pdfs={mid: [name]})
    assert _pull_action(mid, seen, settings) == "skip"


def test_recorded_pdfs_missing_from_disk_backfills(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_dirs()
    mid = "dddddddddddddddd"
    seen = SeenIndex(pdfs={mid: ["dddddddddddd_CC_Statement.pdf"]})
    assert _pull_action(mid, seen, settings) == "pdfs"


def test_pull_backfills_pdfs_without_rewriting_eml(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_dirs()
    mid = "1a0568f195b9b84e"
    eml = settings.inbox_dir / "email" / f"{mid[:12]}_alerts.eml"
    original = "From: already-downloaded\n\nbody only, no attachment\n"
    eml.write_text(original, encoding="utf-8")
    seen_path(settings).write_text(json.dumps({"ids": [mid, mid[:12]]}), encoding="utf-8")

    pdf_bytes = b"%PDF-1.4 statement"
    message = {
        "id": mid,
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [{"name": "From", "value": "alerts@hdfcbank.net"}],
            "parts": [
                {
                    "filename": "CC_Statement.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "ATT1", "size": len(pdf_bytes)},
                }
            ],
        },
    }

    class Messages:
        def get(self, **_kwargs):
            return SimpleNamespace(execute=lambda: message)

        def attachments(self):
            encoded = base64.urlsafe_b64encode(pdf_bytes).decode().rstrip("=")
            return SimpleNamespace(get=lambda **_k: SimpleNamespace(execute=lambda: {"data": encoded}))

    service = SimpleNamespace(users=lambda: SimpleNamespace(messages=lambda: Messages()))
    monkeypatch.setattr("finsca.ingest.email.gmail_api._service", lambda _s: service)
    monkeypatch.setattr("finsca.ingest.email.gmail_api._list_ids", lambda *_a, **_k: [mid])
    monkeypatch.setattr("finsca.ingest.email.gmail_api.time.sleep", lambda *_a, **_k: None)

    result = pull(settings, months=6)
    assert result.emails == 0
    assert result.pdfs == 1
    assert result.skipped == 0
    assert eml.read_text(encoding="utf-8") == original
    dest = settings.inbox_dir / "pdf" / f"{mid[:12]}_alerts_hdfcbank.net_CC_Statement.pdf"
    assert dest.read_bytes() == pdf_bytes
    reloaded = load_seen(settings)
    assert dest.name in (reloaded.pdfs[mid] or [])

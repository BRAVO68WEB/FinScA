from __future__ import annotations

from pathlib import Path

from finsca.config.settings import Settings
from finsca.ingest.email.gmail_api import load_seen, save_seen


def test_seen_roundtrip_and_inbox_prefixes(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_dirs()
    (settings.inbox_dir / "email" / "1a0568f195b9_alerts.eml").write_text("From: x\n\nbody\n")
    save_seen(settings, {"already"})
    seen = load_seen(settings)
    assert "already" in seen
    assert "1a0568f195b9" in seen

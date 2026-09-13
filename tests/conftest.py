from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    for part in ("inbox/pdf", "inbox/email", "inbox/sms", "archive", "reports"):
        (root / part).mkdir(parents=True)
    monkeypatch.setenv("FINSCA_DATA_DIR", str(root))
    return root

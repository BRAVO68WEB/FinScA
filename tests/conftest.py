from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from finsca.db.engine import init_db, make_engine
from finsca.db.session import session_scope


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    for part in ("inbox/pdf", "inbox/email", "inbox/sms", "archive", "reports"):
        (root / part).mkdir(parents=True)
    monkeypatch.setenv("FINSCA_DATA_DIR", str(root))
    return root


@pytest.fixture
def db_session(data_dir: Path) -> Iterator[Session]:
    engine = make_engine(data_dir / "finsca.db")
    init_db(engine)
    with session_scope(engine) as session:
        yield session
